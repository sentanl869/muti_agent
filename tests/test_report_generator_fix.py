"""
测试报告生成器修复
专门测试 NoneType 错误的修复
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.report_generator import ReportGenerator
from agents.structure_checker import StructureCheckResult, StructureNode, MissingChapter
from agents.content_checker import ContentCheckResult, ChapterCheckResult, Violation


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


class TestReportGeneratorFix:
    """测试报告生成器修复"""
    
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
    
    def test_original_error_scenario(self):
        """测试原始错误场景：content_result 为 None"""
        # 创建一个有效的结构检查结果
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
        
        structure_result = StructureCheckResult(
            passed=False,
            missing_chapters=missing_chapters,
            extra_chapters=[],
            structure_issues=[],
            template_structure=template_structure,
            target_structure=target_structure,
            similarity_score=0.5
        )
        
        # content_result 为 None（这是导致原始错误的情况）
        content_result = None
        
        # 模拟配置
        with patch('agents.report_generator.config') as mock_config:
            mock_config.check.get_enabled_checks.return_value = ['structure']  # 只启用结构检查
            mock_config.check.enable_image_check = False
            
            # 这应该不会抛出 'NoneType' object has no attribute 'total_violations' 错误
            try:
                report_data = self.report_generator._prepare_report_data(
                    structure_result, content_result,
                    self.template_doc_info, self.target_doc_info
                )
                
                # 验证结果
                assert report_data['overall_passed'] == False  # 结构检查失败
                assert report_data['total_issues'] == 1  # 只有结构问题
                assert report_data['total_violations'] == 0  # 内容检查未执行
                assert report_data['missing_chapters_count'] == 1
                assert report_data['content_passed'] == True  # 内容检查未执行，默认通过
                
                print("✅ 原始错误已修复：content_result=None 不再导致异常")
                
            except AttributeError as e:
                if "'NoneType' object has no attribute 'total_violations'" in str(e):
                    pytest.fail("修复失败：仍然出现 'NoneType' object has no attribute 'total_violations' 错误")
                else:
                    raise
    
    def test_structure_result_none_scenario(self):
        """测试 structure_result 为 None 的场景"""
        # 创建一个有效的内容检查结果
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
        
        content_result = ContentCheckResult(
            passed=False,
            chapters=chapter_results,
            total_violations=1,
            rules_summary={"测试规则": 1},
            severity_summary={"critical": 0, "warning": 1, "info": 0}
        )
        
        # structure_result 为 None
        structure_result = None
        
        # 模拟配置
        with patch('agents.report_generator.config') as mock_config:
            mock_config.check.get_enabled_checks.return_value = ['content']  # 只启用内容检查
            mock_config.check.enable_image_check = False
            
            # 这应该不会抛出异常
            report_data = self.report_generator._prepare_report_data(
                structure_result, content_result,
                self.template_doc_info, self.target_doc_info
            )
            
            # 验证结果
            assert report_data['overall_passed'] == False  # 内容检查失败
            assert report_data['total_issues'] == 1  # 只有内容问题
            assert report_data['total_violations'] == 1
            assert report_data['missing_chapters_count'] == 0  # 结构检查未执行
            assert report_data['structure_passed'] == True  # 结构检查未执行，默认通过
            
            print("✅ structure_result=None 场景正常处理")
    
    def test_both_results_none_scenario(self):
        """测试两个结果都为 None 的场景"""
        structure_result = None
        content_result = None
        
        # 模拟配置
        with patch('agents.report_generator.config') as mock_config:
            mock_config.check.get_enabled_checks.return_value = []  # 禁用所有检查
            mock_config.check.enable_image_check = False
            
            # 这应该不会抛出异常
            report_data = self.report_generator._prepare_report_data(
                structure_result, content_result,
                self.template_doc_info, self.target_doc_info
            )
            
            # 验证结果
            assert report_data['overall_passed'] == True  # 没有检查，默认通过
            assert report_data['total_issues'] == 0
            assert report_data['total_violations'] == 0
            assert report_data['missing_chapters_count'] == 0
            assert report_data['structure_passed'] == True
            assert report_data['content_passed'] == True
            
            print("✅ 两个结果都为 None 的场景正常处理")
    
    def test_structure_tree_conversion_with_none(self):
        """测试结构树转换处理 None 输入"""
        # 测试 None 输入
        result = self.report_generator._convert_structure_trees(None, None, [], [])
        assert result == ([], [])
        print("✅ 结构树转换正确处理 None 输入")
        
        # 测试部分 None 输入
        structure = StructureNode("根节点", 0, [])
        result = self.report_generator._convert_structure_trees(structure, None, [], [])
        assert result == ([], [])
        
        result = self.report_generator._convert_structure_trees(None, structure, [], [])
        assert result == ([], [])
        print("✅ 结构树转换正确处理部分 None 输入")
    
    def test_detailed_statistics_with_none_content(self):
        """测试详细统计计算处理 None 内容结果"""
        # 创建一个有效的结构检查结果
        template_structure = StructureNode("根节点", 0, [
            StructureNode("第一章", 1, [])
        ])
        
        structure_result = StructureCheckResult(
            passed=True,
            missing_chapters=[],
            extra_chapters=[],
            structure_issues=[],
            template_structure=template_structure,
            target_structure=template_structure,
            similarity_score=1.0
        )
        
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
        
        print("✅ 详细统计计算正确处理 None 内容结果")


def test_demonstrate_fix():
    """演示修复效果的测试"""
    print("\n" + "="*60)
    print("🔧 动态配置修复验证")
    print("="*60)
    
    # 运行所有测试方法
    test_instance = TestReportGeneratorFix()
    test_instance.setup_method()
    
    print("\n1. 测试原始错误场景（content_result=None）...")
    test_instance.test_original_error_scenario()
    
    print("\n2. 测试 structure_result=None 场景...")
    test_instance.test_structure_result_none_scenario()
    
    print("\n3. 测试两个结果都为 None 的场景...")
    test_instance.test_both_results_none_scenario()
    
    print("\n4. 测试结构树转换...")
    test_instance.test_structure_tree_conversion_with_none()
    
    print("\n5. 测试详细统计计算...")
    test_instance.test_detailed_statistics_with_none_content()
    
    print("\n" + "="*60)
    print("✅ 所有修复验证通过！")
    print("🎉 'NoneType' object has no attribute 'total_violations' 错误已完全修复")
    print("="*60)


if __name__ == '__main__':
    test_demonstrate_fix()
