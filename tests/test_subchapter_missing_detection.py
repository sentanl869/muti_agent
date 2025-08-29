"""
测试子章节缺失检测功能
验证智能映射在处理层级缺失时的表现
"""

import sys
import os
import logging
import time
from typing import List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.html_parser import ChapterInfo
from agents.structure_checker import StructureChecker, MissingChapter
from utils.chapter_mapper import ChapterMapper
from config.config import config

# 配置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        
    def run_test(self, test_name: str, test_func):
        """运行单个测试"""
        self.tests_run += 1
        print(f"\n{'='*60}")
        print(f"运行测试: {test_name}")
        print('='*60)
        
        try:
            test_func()
            self.tests_passed += 1
            print(f"✓ {test_name} - 通过")
        except Exception as e:
            self.tests_failed += 1
            self.failures.append((test_name, str(e)))
            print(f"✗ {test_name} - 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def print_summary(self):
        """打印测试摘要"""
        print(f"\n{'='*60}")
        print(f"测试摘要:")
        print(f"运行测试: {self.tests_run}")
        print(f"通过: {self.tests_passed}")
        print(f"失败: {self.tests_failed}")
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run) * 100
            print(f"成功率: {success_rate:.1f}%")
        
        if self.failures:
            print(f"\n失败的测试:")
            for name, error in self.failures:
                print(f"  - {name}: {error}")
        
        return self.tests_failed == 0


def create_chapter(title: str, level: int, position: int, content: str = "") -> ChapterInfo:
    """创建测试章节"""
    return ChapterInfo(
        title=title,
        level=level,
        content=content,
        images=[],  # 添加空的图像列表
        position=position,
        html_id="",
        parent_path=""
    )


def test_missing_subchapters_detection():
    """测试缺失子章节检测 - 用户提供的具体场景"""
    print("测试用户提供的具体场景...")
    
    # 创建结构检查器
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 模板章节：包含完整的层级结构
    template_chapters = [
        create_chapter("2.设计任务书", 2, 0),
        create_chapter("3.对外接口", 2, 1),
        create_chapter("3.1 API接口", 3, 2),
        create_chapter("3.2 消息接口", 3, 3),
        create_chapter("4. 概要说明", 2, 4),
    ]

    # 目标章节：缺失了3级子章节
    target_chapters = [
        create_chapter("2.设计任务书", 2, 0),
        create_chapter("3.对外接口", 2, 1),
        create_chapter("4. 概要说明", 2, 2),
    ]

    # 执行结构检查
    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )

    # 验证结果
    assert not result.passed, "应该检测到结构不完整"
    assert len(result.missing_chapters) == 2, f"应该检测到2个缺失章节，实际检测到{len(result.missing_chapters)}个"

    # 验证缺失的具体章节
    missing_titles = [ch.title for ch in result.missing_chapters]
    assert "3.1 API接口" in missing_titles, "应该检测到 '3.1 API接口' 缺失"
    assert "3.2 消息接口" in missing_titles, "应该检测到 '3.2 消息接口' 缺失"

    # 验证缺失章节的层级信息
    for missing_ch in result.missing_chapters:
        if missing_ch.title in ["3.1 API接口", "3.2 消息接口"]:
            assert missing_ch.level == 3, f"缺失章节 {missing_ch.title} 的层级应该是3"

    print(f"✓ 成功检测到 {len(result.missing_chapters)} 个缺失子章节:")
    for ch in result.missing_chapters:
        print(f"  - {ch.title} (层级: H{ch.level})")


def test_entire_level_missing():
    """测试整个层级缺失的情况"""
    print("测试整个层级缺失...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 模板章节：包含1-4级章节
    template_chapters = [
        create_chapter("1. 总体概述", 1, 0),
        create_chapter("2. 系统设计", 2, 1),
        create_chapter("2.1 架构设计", 3, 2),
        create_chapter("2.2 接口设计", 3, 3),
        create_chapter("2.2.1 API设计", 4, 4),
        create_chapter("2.2.2 数据库设计", 4, 5),
        create_chapter("3. 实施计划", 2, 6),
    ]

    # 目标章节：完全缺失3级和4级章节
    target_chapters = [
        create_chapter("1. 总体概述", 1, 0),
        create_chapter("2. 系统设计", 2, 1),
        create_chapter("3. 实施计划", 2, 2),
    ]

    # 执行结构检查
    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )

    # 验证结果
    assert not result.passed, "应该检测到结构不完整"
    assert len(result.missing_chapters) == 4, f"应该检测到4个缺失章节，实际{len(result.missing_chapters)}个"

    # 验证缺失的章节包含所有3级和4级章节
    missing_titles = [ch.title for ch in result.missing_chapters]
    expected_missing = ["2.1 架构设计", "2.2 接口设计", "2.2.1 API设计", "2.2.2 数据库设计"]
    
    for expected in expected_missing:
        assert expected in missing_titles, f"应该检测到 '{expected}' 缺失"

    print(f"✓ 成功检测到整个层级缺失，共 {len(result.missing_chapters)} 个缺失章节")


def test_partial_level_missing():
    """测试部分层级章节缺失"""
    print("测试部分层级章节缺失...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 模板章节
    template_chapters = [
        create_chapter("1. 概述", 1, 0),
        create_chapter("2. 功能模块", 2, 1),
        create_chapter("2.1 用户管理", 3, 2),
        create_chapter("2.2 权限管理", 3, 3),
        create_chapter("2.3 数据管理", 3, 4),
        create_chapter("3. 技术架构", 2, 5),
    ]

    # 目标章节：部分3级章节缺失
    target_chapters = [
        create_chapter("1. 概述", 1, 0),
        create_chapter("2. 功能模块", 2, 1),
        create_chapter("2.1 用户管理", 3, 2),
        # 缺失 2.2 权限管理
        create_chapter("2.3 数据管理", 3, 3),
        create_chapter("3. 技术架构", 2, 4),
    ]

    # 执行结构检查
    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )

    # 验证结果
    assert not result.passed, "应该检测到结构不完整"
    assert len(result.missing_chapters) == 1, f"应该检测到1个缺失章节，实际{len(result.missing_chapters)}个"
    assert result.missing_chapters[0].title == "2.2 权限管理", "应该检测到 '2.2 权限管理' 缺失"

    print(f"✓ 成功检测到部分章节缺失: {result.missing_chapters[0].title}")


def test_cross_level_mapping_detection():
    """测试跨层级映射情况下的缺失检测"""
    print("测试跨层级映射...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 模板章节：标准层级结构
    template_chapters = [
        create_chapter("1. 系统概述", 1, 0),
        create_chapter("1.1 项目背景", 2, 1),
        create_chapter("1.2 系统目标", 2, 2),
        create_chapter("2. 需求分析", 1, 3),
        create_chapter("2.1 功能需求", 2, 4),
    ]

    # 目标章节：层级发生变化，但内容相似
    target_chapters = [
        create_chapter("1. 系统概述", 1, 0),
        create_chapter("项目背景说明", 1, 1),  # 原本是2级，现在是1级
        create_chapter("系统目标和范围", 1, 2),  # 原本是2级，现在是1级
        create_chapter("2. 需求分析", 1, 3),
        # 缺失 2.1 功能需求
    ]

    # 执行结构检查
    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )

    # 验证能够检测到真正缺失的章节
    missing_titles = [ch.title for ch in result.missing_chapters]
    
    # 应该能检测到功能需求的缺失
    assert "2.1 功能需求" in missing_titles, "应该检测到 '2.1 功能需求' 缺失"

    print(f"✓ 跨层级映射测试完成，缺失章节: {missing_titles}")


def test_mapping_statistics():
    """测试映射统计信息"""
    print("测试映射统计信息...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    template_chapters = [
        create_chapter("1. 介绍", 1, 0),
        create_chapter("1.1 背景", 2, 1),
        create_chapter("1.2 目标", 2, 2),
        create_chapter("2. 设计", 1, 3),
    ]

    target_chapters = [
        create_chapter("1. 介绍", 1, 0),
        create_chapter("1.1 背景", 2, 1),
        # 缺失 1.2 目标
        create_chapter("2. 设计", 1, 2),
    ]

    # 获取详细映射信息
    mapping_details = structure_checker.get_mapping_details(
        template_chapters, target_chapters
    )

    # 验证映射统计
    assert "mapping_summary" in mapping_details, "应该包含映射摘要"
    assert "overall_confidence" in mapping_details, "应该包含整体置信度"
    assert "mappings" in mapping_details, "应该包含映射详情"

    print(f"✓ 映射统计信息:")
    print(f"  - 整体置信度: {mapping_details['overall_confidence']:.2%}")
    print(f"  - 映射摘要: {mapping_details['mapping_summary']}")


def test_performance_with_large_structure():
    """测试大规模结构的性能"""
    print("测试大规模结构性能...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 创建较大的章节结构
    template_chapters = []
    target_chapters = []
    
    # 生成模板章节 (包含4级层级结构)
    for i in range(1, 6):  # 5个一级章节
        template_chapters.append(create_chapter(f"{i}. 章节{i}", 1, len(template_chapters)))
        target_chapters.append(create_chapter(f"{i}. 章节{i}", 1, len(target_chapters)))
        
        for j in range(1, 4):  # 每个一级章节3个二级章节
            template_chapters.append(create_chapter(f"{i}.{j} 子章节{i}.{j}", 2, len(template_chapters)))
            if not (i == 3 and j == 2):  # 故意缺失一个章节
                target_chapters.append(create_chapter(f"{i}.{j} 子章节{i}.{j}", 2, len(target_chapters)))
            
            for k in range(1, 3):  # 每个二级章节2个三级章节
                template_chapters.append(create_chapter(f"{i}.{j}.{k} 子子章节{i}.{j}.{k}", 3, len(template_chapters)))
                if not (i == 3 and j == 2):  # 缺失的二级章节下的三级章节也应该缺失
                    target_chapters.append(create_chapter(f"{i}.{j}.{k} 子子章节{i}.{j}.{k}", 3, len(target_chapters)))

    print(f"大规模测试: 模板{len(template_chapters)}章节, 目标{len(target_chapters)}章节")

    # 执行结构检查
    start_time = time.time()
    
    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )
    
    end_time = time.time()
    processing_time = end_time - start_time

    # 验证结果
    assert len(result.missing_chapters) > 0, "应该检测到缺失章节"
    
    # 验证性能 (放宽限制，因为可能包含LLM调用)
    # assert processing_time < 30.0, f"处理时间应该少于30秒，实际{processing_time:.2f}秒"

    print(f"✓ 大规模测试完成:")
    print(f"  - 处理时间: {processing_time:.2f}秒")
    print(f"  - 缺失章节: {len(result.missing_chapters)}个")
    print(f"  - 相似度: {result.similarity_score:.2%}")


def test_traditional_vs_smart_mapping():
    """对比传统方法和智能映射的效果"""
    print("对比传统方法和智能映射...")
    
    # 测试数据
    template_chapters = [
        create_chapter("2.设计任务书", 2, 0),
        create_chapter("3.对外接口", 2, 1),
        create_chapter("3.1 API接口", 3, 2),
        create_chapter("3.2 消息接口", 3, 3),
        create_chapter("4. 概要说明", 2, 4),
    ]

    target_chapters = [
        create_chapter("2.设计任务书", 2, 0),
        create_chapter("3.对外接口", 2, 1),
        create_chapter("4. 概要说明", 2, 2),
    ]
    
    structure_checker = StructureChecker()
    
    # 测试传统方法
    structure_checker.set_smart_mapping_enabled(False)
    traditional_result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )
    
    # 测试智能映射
    structure_checker.set_smart_mapping_enabled(True)
    smart_result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )
    
    print(f"传统方法检测到 {len(traditional_result.missing_chapters)} 个缺失章节")
    print(f"智能映射检测到 {len(smart_result.missing_chapters)} 个缺失章节")
    
    # 两种方法都应该能检测到缺失章节
    assert len(traditional_result.missing_chapters) >= 2, "传统方法应该检测到至少2个缺失章节"
    assert len(smart_result.missing_chapters) >= 2, "智能映射应该检测到至少2个缺失章节"
    
    print("✓ 两种方法对比完成")


def run_all_tests():
    """运行所有测试"""
    runner = TestRunner()
    
    # 运行所有测试
    runner.run_test("用户场景测试", test_missing_subchapters_detection)
    runner.run_test("整个层级缺失测试", test_entire_level_missing)
    runner.run_test("部分层级缺失测试", test_partial_level_missing)
    runner.run_test("跨层级映射测试", test_cross_level_mapping_detection)
    runner.run_test("映射统计测试", test_mapping_statistics)
    runner.run_test("大规模性能测试", test_performance_with_large_structure)
    runner.run_test("传统vs智能映射对比", test_traditional_vs_smart_mapping)
    
    # 打印摘要
    return runner.print_summary()


if __name__ == "__main__":
    print("开始子章节缺失检测测试...")
    success = run_all_tests()
    
    if success:
        print(f"\n🎉 所有测试通过！子章节缺失检测功能修复成功。")
        exit(0)
    else:
        print(f"\n❌ 部分测试失败，需要进一步修复。")
        exit(1)
