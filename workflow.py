"""
基于 LangGraph 的文档检查工作流程
"""

import logging
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents import (
    DocumentFetcher, StructureChecker, ContentChecker, ReportGenerator
)
from utils import ContentIntegrator
from config.config import config

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """工作流状态"""
    # 输入参数
    template_url: str
    template_page_id: str
    target_url: str
    target_page_id: str
    
    # 文档数据
    template_document: Dict[str, Any]
    target_document: Dict[str, Any]
    integrated_chapters: List[Any]
    
    # 检查结果
    structure_result: Any
    content_result: Any
    
    # 输出
    report_path: str
    
    # 状态信息
    current_step: str
    error_message: str
    completed: bool


class DocumentCheckWorkflow:
    """文档检查工作流程"""
    
    def __init__(self):
        self.document_fetcher = DocumentFetcher()
        self.structure_checker = StructureChecker()
        self.content_checker = ContentChecker()
        self.content_integrator = ContentIntegrator()
        self.report_generator = ReportGenerator()
        
        # 创建工作流图
        self.workflow = self._create_workflow()
        
        # 编译工作流
        self.app = self.workflow.compile(checkpointer=MemorySaver())
    
    def _create_workflow(self) -> StateGraph:
        """创建 LangGraph 工作流"""
        
        # 创建状态图
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("fetch_template", self._fetch_template_document)
        workflow.add_node("fetch_target", self._fetch_target_document)
        workflow.add_node("integrate_content", self._integrate_content)
        workflow.add_node("check_structure", self._check_structure)
        workflow.add_node("check_content", self._check_content)
        workflow.add_node("generate_report", self._generate_report)
        workflow.add_node("handle_error", self._handle_error)
        
        # 设置入口点
        workflow.set_entry_point("fetch_template")
        
        # 添加边
        workflow.add_edge("fetch_template", "fetch_target")
        workflow.add_edge("fetch_target", "integrate_content")
        workflow.add_edge("integrate_content", "check_structure")
        workflow.add_edge("check_structure", "check_content")
        workflow.add_edge("check_content", "generate_report")
        workflow.add_edge("generate_report", END)
        workflow.add_edge("handle_error", END)
        
        # 添加条件边（错误处理）
        workflow.add_conditional_edges(
            "fetch_template",
            self._should_continue,
            {
                "continue": "fetch_target",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "fetch_target",
            self._should_continue,
            {
                "continue": "integrate_content",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "integrate_content",
            self._should_continue,
            {
                "continue": "check_structure",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "check_structure",
            self._should_continue,
            {
                "continue": "check_content",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "check_content",
            self._should_continue,
            {
                "continue": "generate_report",
                "error": "handle_error"
            }
        )
        
        return workflow
    
    def _should_continue(self, state: WorkflowState) -> str:
        """判断是否应该继续执行"""
        if state.get("error_message"):
            return "error"
        return "continue"
    
    def _fetch_template_document(self, state: WorkflowState) -> WorkflowState:
        """获取模板文档"""
        try:
            logger.info("开始获取模板文档")
            state["current_step"] = "获取模板文档"
            
            template_doc = self.document_fetcher.fetch_template_document(
                state["template_url"],
                state.get("template_page_id")
            )
            
            # 验证文档
            if not self.document_fetcher.validate_document(template_doc):
                raise ValueError("模板文档验证失败")
            
            state["template_document"] = template_doc
            logger.info("模板文档获取完成")
            
        except Exception as e:
            logger.error(f"获取模板文档失败: {e}")
            state["error_message"] = f"获取模板文档失败: {str(e)}"
        
        return state
    
    def _fetch_target_document(self, state: WorkflowState) -> WorkflowState:
        """获取目标文档"""
        try:
            logger.info("开始获取目标文档")
            state["current_step"] = "获取目标文档"
            
            target_doc = self.document_fetcher.fetch_target_document(
                state["target_url"],
                state.get("target_page_id")
            )
            
            # 验证文档
            if not self.document_fetcher.validate_document(target_doc):
                raise ValueError("目标文档验证失败")
            
            state["target_document"] = target_doc
            logger.info("目标文档获取完成")
            
        except Exception as e:
            logger.error(f"获取目标文档失败: {e}")
            state["error_message"] = f"获取目标文档失败: {str(e)}"
        
        return state
    
    def _integrate_content(self, state: WorkflowState) -> WorkflowState:
        """整合文档内容"""
        try:
            logger.info("开始整合文档内容")
            state["current_step"] = "整合文档内容"
            
            target_chapters = state["target_document"]["chapters"]
            
            # 检查内容长度，如果超过限制则进行分块
            total_length = sum(len(chapter.content) for chapter in target_chapters)
            max_length = config.llm.max_context_length
            
            if total_length > max_length:
                logger.warning(f"文档内容过长 ({total_length} > {max_length})，进行分块处理")
                integrated_chapters = self.content_integrator.integrate_chapters_chunked(
                    target_chapters, max_length
                )
            else:
                integrated_chapters = self.content_integrator.integrate_chapters(
                    target_chapters
                )
            
            state["integrated_chapters"] = integrated_chapters
            logger.info(f"内容整合完成: {len(integrated_chapters)} 个整合章节")
            
        except Exception as e:
            logger.error(f"整合文档内容失败: {e}")
            state["error_message"] = f"整合文档内容失败: {str(e)}"
        
        return state
    
    def _check_structure(self, state: WorkflowState) -> WorkflowState:
        """检查章节结构完整性"""
        try:
            logger.info("开始检查章节结构")
            state["current_step"] = "检查章节结构"
            
            template_chapters = state["template_document"]["chapters"]
            target_chapters = state["target_document"]["chapters"]
            
            structure_result = self.structure_checker.check_structure_completeness(
                template_chapters, target_chapters
            )
            
            state["structure_result"] = structure_result
            logger.info("章节结构检查完成")
            
        except Exception as e:
            logger.error(f"检查章节结构失败: {e}")
            state["error_message"] = f"检查章节结构失败: {str(e)}"
        
        return state
    
    def _check_content(self, state: WorkflowState) -> WorkflowState:
        """检查内容规范"""
        try:
            logger.info("开始检查内容规范")
            state["current_step"] = "检查内容规范"
            
            integrated_chapters = state["integrated_chapters"]
            
            content_result = self.content_checker.check_content_compliance(
                integrated_chapters
            )
            
            state["content_result"] = content_result
            logger.info("内容规范检查完成")
            
        except Exception as e:
            logger.error(f"检查内容规范失败: {e}")
            state["error_message"] = f"检查内容规范失败: {str(e)}"
        
        return state
    
    def _generate_report(self, state: WorkflowState) -> WorkflowState:
        """生成检查报告"""
        try:
            logger.info("开始生成检查报告")
            state["current_step"] = "生成检查报告"
            
            report_path = self.report_generator.generate_report(
                state["structure_result"],
                state["content_result"],
                state["template_document"],
                state["target_document"]
            )
            
            state["report_path"] = report_path
            state["completed"] = True
            logger.info("检查报告生成完成")
            
        except Exception as e:
            logger.error(f"生成检查报告失败: {e}")
            state["error_message"] = f"生成检查报告失败: {str(e)}"
        
        return state
    
    def _handle_error(self, state: WorkflowState) -> WorkflowState:
        """处理错误"""
        logger.error(f"工作流执行失败: {state.get('error_message', '未知错误')}")
        state["completed"] = True
        return state
    
    def run(self, template_url: str, target_url: str, 
            template_page_id: str = None, target_page_id: str = None) -> Dict[str, Any]:
        """
        运行文档检查工作流
        
        Args:
            template_url: 模板文档 URL
            target_url: 目标文档 URL
            template_page_id: 模板页面 ID（可选）
            target_page_id: 目标页面 ID（可选）
            
        Returns:
            工作流执行结果
        """
        try:
            logger.info("开始执行文档检查工作流")
            
            # 初始化状态
            initial_state = WorkflowState(
                template_url=template_url,
                template_page_id=template_page_id,
                target_url=target_url,
                target_page_id=target_page_id,
                template_document={},
                target_document={},
                integrated_chapters=[],
                structure_result=None,
                content_result=None,
                report_path="",
                current_step="初始化",
                error_message="",
                completed=False
            )
            
            # 执行工作流
            config_dict = {"configurable": {"thread_id": "document_check"}}
            final_state = self.app.invoke(initial_state, config_dict)
            
            # 返回结果
            result = {
                "success": not bool(final_state.get("error_message")),
                "error_message": final_state.get("error_message", ""),
                "report_path": final_state.get("report_path", ""),
                "structure_result": final_state.get("structure_result"),
                "content_result": final_state.get("content_result"),
                "template_document": final_state.get("template_document", {}),
                "target_document": final_state.get("target_document", {}),
                "current_step": final_state.get("current_step", ""),
                "completed": final_state.get("completed", False)
            }
            
            if result["success"]:
                logger.info(f"文档检查工作流执行成功，报告已生成: {result['report_path']}")
            else:
                logger.error(f"文档检查工作流执行失败: {result['error_message']}")
            
            return result
            
        except Exception as e:
            logger.error(f"工作流执行异常: {e}")
            return {
                "success": False,
                "error_message": f"工作流执行异常: {str(e)}",
                "report_path": "",
                "structure_result": None,
                "content_result": None,
                "template_document": {},
                "target_document": {},
                "current_step": "异常终止",
                "completed": True
            }
    
    def get_workflow_status(self, thread_id: str = "document_check") -> Dict[str, Any]:
        """获取工作流状态"""
        try:
            config_dict = {"configurable": {"thread_id": thread_id}}
            state = self.app.get_state(config_dict)
            
            if state and state.values:
                return {
                    "current_step": state.values.get("current_step", "未知"),
                    "completed": state.values.get("completed", False),
                    "error_message": state.values.get("error_message", ""),
                    "has_error": bool(state.values.get("error_message"))
                }
            else:
                return {
                    "current_step": "未开始",
                    "completed": False,
                    "error_message": "",
                    "has_error": False
                }
                
        except Exception as e:
            logger.error(f"获取工作流状态失败: {e}")
            return {
                "current_step": "状态获取失败",
                "completed": False,
                "error_message": str(e),
                "has_error": True
            }
    
    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self.document_fetcher, 'close'):
                self.document_fetcher.close()
            logger.info("工作流资源清理完成")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
