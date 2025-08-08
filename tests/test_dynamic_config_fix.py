"""
测试动态配置修复
验证在不同配置组合下报告生成器的行为
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.report_generator import ReportGenerator
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


class TestDynamicConfigFix:
    """测试动态配置修复"""
    
    def setup_method(self):
        """测试前设置"""
        self.report_generator = ReportGenerator()
        
        # 创建模拟的文档信息
        self.template_doc_info = {
            'url': 'https://example.com/template',
            'meta_info': {'title': '模板文档'},
            'chapters': [
                MockChapterInfo('第一章', 1),
                MockChapterInfo('第二章', 1),
            ]
        }
        
        self.target_doc_info = {
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
    
    @patch('agents.report_generator.config')
    def test_both_checks_enabled(self, mock_config):
        """测试两个检查都启用的情况"""
        # 配置两个检查都启用
        mock_config.check.get_enabled_checks.return_value = ['structure', 'content']
        mock_config.check.enable_image_check = False
        mock_config.report.template_file = 'templates/report.html'
        mock_config.report.output_dir = 'reports'
        
        structure_result = self.create_mock_structure_result()
        content_result = self.create_mock_content_result()
        
        # 模拟模板文件
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "<html>{{document_name}}</html>"
            mock_open.return_value.__enter__.return_value.write = Mock()
            
            with patch('os.path.join', return_value='test_report.html'):
                report_data = self.report_generator._prepare_report_data(
                    structure_result, content_result,
                    self.template_doc_info, self.target_doc_info
                )
        
        # 验证结果
        assert report_data['overall_passed'] == False
        assert report_data['total_issues'] == 2  # 1个结构问题 + 1个内容问题
        assert report_data['structure_passed'] == False
        assert report_data['content_passed'] == False
        assert report_data['total_violations'] == 1
        assert report_data['missing_chapters_count'] == 1
    
    @patch('agents.report_generator.config')
    def test_only_structure_check_enabled(self, mock_config):
        """测试只启用结构检查的情况"""
        # 配置只启用结构检查
        mock_config.check.get_enabled_checks.return_value = ['structure']
        mock_config.check.enable_image_check = False
        
        structure_result = self.create_mock_structure_result()
        content_result = None  # 内容检查未执行，结果为 None
        
        report_data = self.report_generator._prepare_report_data(
            structure_result, content_result,
            self.template_doc_info, self.target_doc_info
        )
        
        # 验证结果
        assert report_data['overall_passed'] == False  # 结构检查失败
        assert report_data['total_issues'] == 1  # 只有结构问题
        assert report_data['structure_passed'] == False
        assert report_data['content_passed'] == True  # 内容检查未执行，默认通过
        assert report_data['total_violations'] == 0  # 内容检查未执行
        assert report_data['missing_chapters_count'] == 1
        
        # 验证内容检查相关数据为默认值
        assert report_data['violation_chapters'] == []
        assert report_data['violation_results'] == []
        assert report_data['rules_summary'] == {}
        assert report_data['severity_summary'] == {"critical": 0, "warning": 0, "info": 0}
    
    @patch('agents.report_generator.config')
    def test_only_content_check_enabled(self, mock_config):
        """测试只启用内容检查的情况"""
        # 配置只启用内容检查
        mock_config.check.get_enabled_checks.return_value = ['content']
        mock_config.check.enable_image_check = False
        
        structure_result = None  # 结构检查未执行，结果为 None
        content_result = self.create_mock_content_result()
        
        report_data = self.report_generator._prepare_report_data(
            structure_result, content_result,
            self.template_doc_info, self.target_doc_info
        )
        
        # 验证结果
        assert report_data['overall_passed'] == False  # 内容检查失败
        assert report_data['total_issues'] == 1  # 只有内容问题
        assert report_data['structure_passed'] == True  # 结构检查未执行，默认通过
        assert report_data['content_passed'] == False
        assert report_data['total_violations'] == 1
        assert report_data['missing_chapters_count'] == 0  # 结构检查未执行
        
        # 验证结构检查相关数据为默认值
        assert report_data['missing_chapters'] == []
        assert report_data['extra_chapters'] == []
        assert report_data['structure_issues'] == []
        assert report_data['structure_similarity'] == 100
    
    @patch('agents.report_generator.config')
    def test_no_checks_enabled(self, mock_config):
        """测试禁用所有检查的情况"""
        # 配置禁用所有检查
        mock_config.check.get_enabled_checks.return_value = []
        mock_config.check.enable_image_check = False
        
        structure_result = None
        content_result = None
        
        report_data = self.report_generator._prepare_report_data(
            structure_result, content_result,
            self.template_doc_info, self.target_doc_info
        )
        
        # 验证结果
        assert report_data['overall_passed'] == True  # 没有检查，默认通过
        assert report_data['total_issues'] == 0
        assert report_data['structure_passed'] == True
        assert report_data['content_passed'] == True
        assert report_data['total_violations'] == 0
        assert report_data['missing_chapters_count'] == 0
        
        # 验证所有检查相关数据为默认值
        assert report_data['missing_chapters'] == []
        assert report_data['extra_chapters'] == []
        assert report_data['structure_issues'] == []
        assert report_data['violation_chapters'] == []
        assert report_data['violation_results'] == []
    
    def test_convert_structure_trees_with_none_input(self):
        """测试结构树转换方法处理 None 输入"""
        # 测试 None 输入
        result = self.report_generator._convert_structure_trees(None, None, [], [])
        assert result == ([], [])
        
        # 测试部分 None 输入
        structure = StructureNode("根节点", 0, [])
        result = self.report_generator._convert_structure_trees(structure, None, [], [])
        assert result == ([], [])
        
        result = self.report_generator._convert_structure_trees(None, structure, [], [])
        assert result == ([], [])
    
    def test_calculate_detailed_statistics_with_none_content_result(self):
        """测试详细统计计算方法处理 None 内容结果"""
        structure_result = self.create_mock_structure_result()
        content_result = None
        
        statistics = self.report_generator._calculate_detailed_statistics(
            structure_result, content_result,
            self.template_doc_info, self.target_doc_info
        )
        
        # 验证统计数据
        assert statistics['chapters_with_violations'] == 0
        assert statistics['chapters_without_violations'] == 0
        assert 'level_distribution' in statistics
        assert 'total_images' in statistics
        assert 'total_content_length' in statistics
        assert 'avg_chapter_length' in statistics


class TestConfigValidation:
    """测试配置验证"""
    
    def test_validate_check_config(self):
        """测试检查配置验证"""
        # 测试正常配置
        assert config.validate_check_config() == True
        
        # 测试获取启用的检查
        enabled_checks = config.check.get_enabled_checks()
        assert isinstance(enabled_checks, list)
        
        # 测试检查是否有任何检查启用
        has_any_enabled = config.check.has_any_check_enabled()
        assert isinstance(has_any_enabled, bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
