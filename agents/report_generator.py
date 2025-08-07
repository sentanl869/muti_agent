"""
报告生成 Agent
负责生成 HTML 格式的检查报告
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, List
from jinja2 import Template

from agents.structure_checker import StructureCheckResult
from agents.content_checker import ContentCheckResult
from config.config import config

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成 Agent"""
    
    def __init__(self):
        self.template_path = config.report.template_file
        self.output_dir = config.report.output_dir
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_report(self, 
                       structure_result: StructureCheckResult,
                       content_result: ContentCheckResult,
                       template_doc_info: Dict[str, Any],
                       target_doc_info: Dict[str, Any]) -> str:
        """
        生成完整的检查报告
        
        Args:
            structure_result: 结构检查结果
            content_result: 内容检查结果
            template_doc_info: 模板文档信息
            target_doc_info: 目标文档信息
            
        Returns:
            生成的报告文件路径
        """
        try:
            logger.info("开始生成检查报告")
            
            # 准备报告数据
            report_data = self._prepare_report_data(
                structure_result, content_result, 
                template_doc_info, target_doc_info
            )
            
            # 读取模板
            template_content = self._load_template()
            
            # 渲染报告
            html_content = self._render_template(template_content, report_data)
            
            # 保存报告
            report_path = self._save_report(html_content)
            
            logger.info(f"检查报告生成完成: {report_path}")
            
            return report_path
            
        except Exception as e:
            logger.error(f"生成检查报告失败: {e}")
            raise
    
    def _prepare_report_data(self, 
                           structure_result: StructureCheckResult,
                           content_result: ContentCheckResult,
                           template_doc_info: Dict[str, Any],
                           target_doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """准备报告数据"""
        
        # 计算总体统计
        total_issues = len(structure_result.missing_chapters) + content_result.total_violations
        overall_passed = structure_result.passed and content_result.passed
        
        # 计算通过率
        total_checks = len(structure_result.template_structure.children) + sum(
            chapter.total_rules_checked for chapter in content_result.chapters
        )
        passed_checks = total_checks - total_issues
        pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 100
        
        
        # 转换结构树数据
        document_structure_tree, template_structure_tree = self._convert_structure_trees(
            structure_result.target_structure, 
            structure_result.template_structure,
            structure_result.missing_chapters,
            structure_result.extra_chapters
        )
        
        # 获取启用的检查功能
        enabled_checks = config.check.get_enabled_checks()
        
        report_data = {
            # 基本信息
            'document_name': target_doc_info.get('meta_info', {}).get('title', '未知文档'),
            'check_time': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
            'template_url': template_doc_info.get('url', ''),
            'target_url': target_doc_info.get('url', ''),
            
            # 检查功能开关状态
            'show_structure_check': 'structure' in enabled_checks,
            'show_content_check': 'content' in enabled_checks,
            'show_image_check': config.check.enable_image_check,
            'enabled_checks': enabled_checks,
            'total_enabled_checks': len(enabled_checks),
            
            # 总体统计
            'overall_passed': overall_passed,
            'total_issues': total_issues,
            'pass_rate': round(pass_rate, 1),
            
            # 章节统计
            'total_chapters': len(target_doc_info.get('chapters', [])),
            'template_chapters': len(template_doc_info.get('chapters', [])),
            
            # 结构检查结果（只有启用时才提供数据）
            'structure_passed': structure_result.passed if 'structure' in enabled_checks else True,
            'missing_chapters_count': len(structure_result.missing_chapters) if 'structure' in enabled_checks else 0,
            'extra_chapters_count': len(structure_result.extra_chapters) if 'structure' in enabled_checks else 0,
            'structure_similarity': round(structure_result.similarity_score * 100, 1) if 'structure' in enabled_checks else 100,
            'missing_chapters': structure_result.missing_chapters if 'structure' in enabled_checks else [],
            'extra_chapters': structure_result.extra_chapters if 'structure' in enabled_checks else [],
            'structure_issues': structure_result.structure_issues if 'structure' in enabled_checks else [],
            
            # 结构树数据
            'document_structure_tree': document_structure_tree if 'structure' in enabled_checks else [],
            'template_structure_tree': template_structure_tree if 'structure' in enabled_checks else [],
            
            # 内容检查结果（只有启用时才提供数据）
            'content_passed': content_result.passed if 'content' in enabled_checks else True,
            'total_violations': content_result.total_violations if 'content' in enabled_checks else 0,
            'violation_chapters': [ch for ch in content_result.chapters if not ch.passed] if 'content' in enabled_checks else [],
            'violation_results': content_result.chapters if 'content' in enabled_checks else [],
            'rules_summary': content_result.rules_summary if 'content' in enabled_checks else {},
            'severity_summary': content_result.severity_summary if 'content' in enabled_checks else {"critical": 0, "warning": 0, "info": 0},
            
            # 详细统计
            'statistics': self._calculate_detailed_statistics(
                structure_result, content_result, template_doc_info, target_doc_info
            )
        }
        
        return report_data
    
    
    def _calculate_detailed_statistics(self, 
                                     structure_result: StructureCheckResult,
                                     content_result: ContentCheckResult,
                                     template_doc_info: Dict[str, Any],
                                     target_doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """计算详细统计信息"""
        
        # 章节层级分布
        target_chapters = target_doc_info.get('chapters', [])
        level_distribution = {}
        for chapter in target_chapters:
            level = chapter.level
            level_distribution[f'H{level}'] = level_distribution.get(f'H{level}', 0) + 1
        
        # 图像统计
        total_images = sum(len(chapter.images) for chapter in target_chapters)
        
        # 内容长度统计
        total_content_length = sum(len(chapter.content) for chapter in target_chapters)
        avg_chapter_length = total_content_length // len(target_chapters) if target_chapters else 0
        
        statistics = {
            'level_distribution': level_distribution,
            'total_images': total_images,
            'total_content_length': total_content_length,
            'avg_chapter_length': avg_chapter_length,
            'chapters_with_violations': len([ch for ch in content_result.chapters if not ch.passed]),
            'chapters_without_violations': len([ch for ch in content_result.chapters if ch.passed])
        }
        
        return statistics
    
    def _convert_structure_trees(self, target_structure, template_structure, missing_chapters, extra_chapters):
        """
        转换结构树为HTML模板所需的格式
        
        Args:
            target_structure: 目标文档结构树
            template_structure: 模板文档结构树
            missing_chapters: 缺失章节列表
            extra_chapters: 额外章节列表
            
        Returns:
            tuple: (目标文档结构树数据, 模板文档结构树数据)
        """
        try:
            # 创建缺失章节标题集合，用于快速查找
            missing_titles = {ch.title for ch in missing_chapters}
            extra_titles = {ch.title for ch in extra_chapters}
            
            # 转换目标文档结构树
            document_tree = self._flatten_structure_tree(target_structure, missing_titles, extra_titles, is_target=True)
            
            # 转换模板文档结构树
            template_tree = self._flatten_structure_tree(template_structure, missing_titles, extra_titles, is_target=False)
            
            return document_tree, template_tree
            
        except Exception as e:
            logger.error(f"转换结构树失败: {e}")
            # 返回空列表，避免模板渲染失败
            return [], []
    
    def _flatten_structure_tree(self, structure_node, missing_titles, extra_titles, is_target=True):
        """
        将结构树扁平化为节点列表
        
        Args:
            structure_node: 结构树根节点
            missing_titles: 缺失章节标题集合
            extra_titles: 额外章节标题集合
            is_target: 是否为目标文档
            
        Returns:
            list: 扁平化的节点列表
        """
        nodes = []
        
        def traverse_node(node, depth=0):
            # 跳过根节点
            if node.title == "根节点":
                for child in node.children:
                    traverse_node(child, depth)
                return
            
            # 确定节点状态
            status = self._determine_node_status(node.title, missing_titles, extra_titles, is_target)
            
            # 创建节点数据
            node_data = {
                'title': node.title,
                'level': node.level,
                'status': status,
                'depth': depth
            }
            
            nodes.append(node_data)
            
            # 递归处理子节点
            for child in node.children:
                traverse_node(child, depth + 1)
        
        traverse_node(structure_node)
        return nodes
    
    def _determine_node_status(self, title, missing_titles, extra_titles, is_target):
        """
        确定节点在对比中的状态
        
        Args:
            title: 节点标题
            missing_titles: 缺失章节标题集合
            extra_titles: 额外章节标题集合
            is_target: 是否为目标文档
            
        Returns:
            str: 节点状态 ('matched', 'missing', 'extra')
        """
        if is_target:
            # 对于目标文档
            if title in extra_titles:
                return 'extra'  # 目标文档中的额外章节
            else:
                return 'matched'  # 匹配的章节
        else:
            # 对于模板文档
            if title in missing_titles:
                return 'missing'  # 模板中存在但目标文档缺失的章节
            else:
                return 'matched'  # 匹配的章节
    
    def _load_template(self) -> str:
        """加载 HTML 模板"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            raise
    
    def _render_template(self, template_content: str, data: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            template = Template(template_content)
            return template.render(**data)
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            raise
    
    def _save_report(self, html_content: str) -> str:
        """保存报告文件"""
        try:
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"document_check_report_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)
            
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"报告已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise
