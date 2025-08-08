"""
测试工作流配置集成
验证工作流在不同配置组合下的完整行为
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow import DocumentCheckWorkflow
from agents.structure_checker import StructureCheckResult, StructureNode, MissingChapter
from agents.content_checker import ContentCheckResult, ChapterCheckResult, Violation
from config.config import config


@dataclass
class MockChapterInfo:
    """模拟章节信息"""
    title: str
    level: int
    content: str = ""
    images: List = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []


class TestWorkflowConfigIntegration:
    """测试工作流配置集成"""
    
    def setup_method(self):
        """测试前设置"""
        self.workflow = DocumentCheckWorkflow()
        
        # 模拟文档数据
        self.mock_template_doc = {
            'url': 'https://example.com/template',
            'meta_info': {'title': '模板文档'},
            'chapters': [
                MockChapterInfo('第一章', 1),
                MockChapterInfo('第二章', 1),
            ]
        }
        
        self.mock_target_doc = {
            'url': 'https://example.com/target',
            'meta_info': {'title': '目标文档'},
            'chapters': [
                MockChapterInfo('第一章', 1),
                MockChapterInfo('第三章', 1),
            ]
        }
    
    def create_mock_structure_result(self) -> StructureCheckResult:
        """创建模拟的结构检查结果"""
        template_structure = StructureNode("根节点", 0, [
            StructureNode("第一章", 1, []),
            StructureNode("第二章", 1, [])
        ])
        
        target_structure = StructureNode("根节点", 0, [
            StructureNode("第一章", 1, []),
            StructureNode("第三章", 1, [])
        ])
        
        missing_chapters = [
            MissingChapter("第二章", 1, "第二章", "根节点", 1)
        ]
        
        extra_chapters = [
            MockChapterInfo("第三章", 1)
        ]
        
        return StructureCheckResult(
            passed=False,
            missing_chapters=missing_chapters,
            extra_chapters=extra_chapters,
            structure_issues=[],
            template_structure=template_structure,
            target_structure=target_structure,
            similarity_score=0.5
        )
    
    def create_mock_content_result(self) -> ContentCheckResult:
        """创建模拟的内容检查结果"""
        violations = [
            Violation(
                rule="测试规则",
                content="测试内容",
                content_type="text",
                position="第一章",
                suggestion="测试建议"
            )
        ]
        
        chapter_results = [
            ChapterCheckResult(
                chapter_title="第一章",
                violations=violations,
                passed=False,
                total_rules_checked=5,
                violation_count=1
            )
        ]
        
        return ContentCheckResult(
            passed=False,
            chapters=chapter_results,
            total_violations=1,
            rules_summary={"测试规则": 1},
            severity_summary={"critical": 0, "warning": 1, "info": 0}
        )
    
    def test_workflow_with_both_checks_enabled(self):
        """测试启用两个检查的工作流"""
        # 直接测试报告生成器在两个检查都启用时的行为
        with patch('agents.report_generator.config') as mock_config:
            mock_config.check.get_enabled_checks.return_value = ['structure', 'content']
            mock_config.check.enable_image_check = False
            
            structure_result = self.create_mock_structure_result()
            content_result = self.create_mock_content_result()
            
            report_data = self.workflow.report_generator._prepare_report_data(
                structure_result, content_result,
                self.mock_template_doc, self.mock_target_doc
            )
            
            # 验证结果
            assert report_data['overall_passed'] == False
            assert report_data['total_issues'] == 2  # 1个结构问题 + 1个内容问题
            assert report_data['structure_passed'] == False
            assert report_data['content_passed'] == False
            assert report_data['total_violations'] == 1
            assert report_data['missing_chapters_count'] == 1
    
    def test_workflow_with_only_structure_check(self):
        """测试只启用结构检查的工作流"""
        # 直接测试报告生成器在只启用结构检查时的行为
        with patch('agents.report_generator.config') as mock_config:
            mock_config.check.get_enabled_checks.return_value = ['structure']
            mock_config.check.enable_image_check = False
            
            structure_result = self.create_mock_structure_result()
            content_result = None  # 内容检查未执行
            
            report_data = self.workflow.report_generator._prepare_report_data(
                structure_result, content_result,
                self.mock_template_doc, self.mock_target_doc
            )
            
            # 验证结果
            assert report_data['overall_passed'] == False  # 结构检查失败
            assert report_data['total_issues'] == 1  # 只有结构问题
            assert report_data['structure_passed'] == False
            assert report_data['content_passed'] == True  # 内容检查未执行，默认通过
            assert report_data['total_violations'] == 0  # 内容检查未执行
            assert report_data['missing_chapters_count'] == 1
    
    def test_workflow_with_only_content_check(self):
        """测试只启用内容检查的工作流"""
        # 直接测试报告生成器在只启用内容检查时的行为
        with patch('agents.report_generator.config') as mock_config:
            mock_config.check.get_enabled_checks.return_value = ['content']
            mock_config.check.enable_image_check = False
            
            structure_result = None  # 结构检查未执行
            content_result = self.create_mock_content_result()
            
            report_data = self.workflow.report_generator._prepare_report_data(
                structure_result, content_result,
                self.mock_template_doc, self.mock_target_doc
            )
            
            # 验证结果
            assert report_data['overall_passed'] == False  # 内容检查失败
            assert report_data['total_issues'] == 1  # 只有内容问题
            assert report_data['structure_passed'] == True  # 结构检查未执行，默认通过
            assert report_data['content_passed'] == False
            assert report_data['total_violations'] == 1
            assert report_data['missing_chapters_count'] == 0  # 结构检查未执行
    
    def test_workflow_with_no_checks_enabled(self):
        """测试禁用所有检查的工作流"""
        # 直接测试报告生成器在禁用所有检查时的行为
        with patch('agents.report_generator.config') as mock_config:
            mock_config.check.get_enabled_checks.return_value = []
            mock_config.check.enable_image_check = False
            
            structure_result = None  # 结构检查未执行
            content_result = None    # 内容检查未执行
            
            report_data = self.workflow.report_generator._prepare_report_data(
                structure_result, content_result,
                self.mock_template_doc, self.mock_target_doc
            )
            
            # 验证结果
            assert report_data['overall_passed'] == True  # 没有检查，默认通过
            assert report_data['total_issues'] == 0
            assert report_data['structure_passed'] == True
            assert report_data['content_passed'] == True
            assert report_data['total_violations'] == 0
            assert report_data['missing_chapters_count'] == 0
    
    def test_report_generator_handles_none_results(self):
        """测试报告生成器正确处理 None 结果"""
        from agents.report_generator import ReportGenerator
        
        # 创建报告生成器
        report_gen = ReportGenerator()
        
        # 测试处理 None 结果
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "<html>{{document_name}}</html>"
            mock_open.return_value.__enter__.return_value.write = Mock()
            
            with patch('os.path.join', return_value='test_report.html'):
                with patch('agents.report_generator.config') as mock_config:
                    mock_config.check.get_enabled_checks.return_value = []
                    mock_config.check.enable_image_check = False
                    
                    # 这应该不会抛出异常
                    report_data = report_gen._prepare_report_data(
                        None, None, self.mock_template_doc, self.mock_target_doc
                    )
                    
                    # 验证默认值
                    assert report_data['overall_passed'] == True
                    assert report_data['total_issues'] == 0
                    assert report_data['total_violations'] == 0
                    assert report_data['missing_chapters_count'] == 0


class TestErrorHandling:
    """测试错误处理"""
    
    def test_report_generator_error_handling(self):
        """测试报告生成器的错误处理"""
        from agents.report_generator import ReportGenerator
        
        report_gen = ReportGenerator()
        
        # 测试模板加载失败
        with patch('builtins.open', side_effect=FileNotFoundError("Template not found")):
            with pytest.raises(FileNotFoundError):
                report_gen._load_template()
        
        # 测试模板渲染失败 - 直接测试 Template 类的实例化和渲染
        with patch('agents.report_generator.Template') as mock_template_class:
            mock_template_instance = Mock()
            mock_template_class.return_value = mock_template_instance
            mock_template_instance.render.side_effect = Exception("Render error")
            
            with pytest.raises(Exception, match="Render error"):
                report_gen._render_template("test template content", {"test": "data"})
    
    def test_structure_tree_conversion_error_handling(self):
        """测试结构树转换的错误处理"""
        from agents.report_generator import ReportGenerator
        
        report_gen = ReportGenerator()
        
        # 测试异常情况下返回空列表
        with patch.object(report_gen, '_flatten_structure_tree', side_effect=Exception("Test error")):
            result = report_gen._convert_structure_trees(
                Mock(), Mock(), [], []
            )
            assert result == ([], [])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
