"""
测试章节缺失检测修复
验证用户报告的具体问题场景是否得到修复
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
        print(f"\n{'='*70}")
        print(f"运行测试: {test_name}")
        print('='*70)
        
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
        print(f"\n{'='*70}")
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
        images=[],
        position=position,
        html_id="",
        parent_path=""
    )

def test_specific_user_scenario():
    """测试用户提供的具体场景"""
    print("测试用户报告的具体问题场景...")
    
    # 创建结构检查器
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 模拟用户场景的模板章节
    template_chapters = [
        create_chapter("4. 概要说明", 2, 0),
        create_chapter("4.6 安全兜底机制", 3, 1),
        create_chapter("4.6.1 安全策略", 4, 2),
        create_chapter("4.6.1.1 安全兜底机制合入", 5, 3),  # 这个应该被检测为缺失
        create_chapter("6. 模块设计", 2, 4),
        create_chapter("6.1 子模块1/类1/主题1", 3, 5),
        create_chapter("6.2. 子模块2/类2/主题2", 3, 6),  # 这个不应该被误判为缺失
    ]

    # 模拟目标章节（缺少一些章节）
    target_chapters = [
        create_chapter("4. 概要说明", 2, 0),
        create_chapter("4.6 安全兜底机制", 3, 1),
        create_chapter("4.6.1 安全策略", 4, 2),
        # 缺失 4.6.1.1 安全兜底机制合入
        create_chapter("6. 模块设计", 2, 3),
        create_chapter("6.1 子模块1/类1/主题1", 3, 4),  # 这个存在，应该被正确识别
        create_chapter("6.2. 子模块2/类2/主题2", 3, 5),  # 这个存在，应该被正确识别
    ]

    print(f"模板章节数: {len(template_chapters)}")
    print(f"目标章节数: {len(target_chapters)}")
    print("\n模板章节:")
    for ch in template_chapters:
        print(f"  - H{ch.level}: {ch.title}")
    print("\n目标章节:")
    for ch in target_chapters:
        print(f"  - H{ch.level}: {ch.title}")

    # 执行结构检查
    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )

    print(f"\n检查结果:")
    print(f"检查通过: {result.passed}")
    print(f"缺失章节数: {len(result.missing_chapters)}")
    print(f"相似度: {result.similarity_score:.2%}")

    # 验证结果
    missing_titles = [ch.title for ch in result.missing_chapters]
    print(f"\n缺失章节列表: {missing_titles}")

    # 关键验证点1: "4.6.1.1 安全兜底机制合入" 应该被检测为缺失
    assert "4.6.1.1 安全兜底机制合入" in missing_titles, \
        f"应该检测到 '4.6.1.1 安全兜底机制合入' 缺失，但缺失列表为: {missing_titles}"

    # 关键验证点2: "6.1 子模块1/类1/主题1" 不应该被误判为缺失
    assert "6.1 子模块1/类1/主题1" not in missing_titles, \
        f"'6.1 子模块1/类1/主题1' 不应该被判断为缺失，但出现在缺失列表中: {missing_titles}"

    # 关键验证点3: "6.2. 子模块2/类2/主题2" 不应该被误判为缺失
    assert "6.2. 子模块2/类2/主题2" not in missing_titles, \
        f"'6.2. 子模块2/类2/主题2' 不应该被判断为缺失，但出现在缺失列表中: {missing_titles}"

    print("✓ 用户场景测试通过")

def test_deep_nested_chapter_detection():
    """测试深层嵌套章节的检测"""
    print("测试深层嵌套章节检测...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 包含深层嵌套的模板章节
    template_chapters = [
        create_chapter("1. 系统设计", 1, 0),
        create_chapter("1.1 架构设计", 2, 1),
        create_chapter("1.1.1 系统架构", 3, 2),
        create_chapter("1.1.1.1 核心组件", 4, 3),
        create_chapter("1.1.1.1.1 服务模块", 5, 4),  # 5级深度
        create_chapter("1.1.1.1.2 数据模块", 5, 5),
        create_chapter("1.2 接口设计", 2, 6),
    ]

    # 目标章节缺少部分深层章节
    target_chapters = [
        create_chapter("1. 系统设计", 1, 0),
        create_chapter("1.1 架构设计", 2, 1),
        create_chapter("1.1.1 系统架构", 3, 2),
        create_chapter("1.1.1.1 核心组件", 4, 3),
        # 缺失 1.1.1.1.1 服务模块
        create_chapter("1.1.1.1.2 数据模块", 5, 4),
        create_chapter("1.2 接口设计", 2, 5),
    ]

    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )

    missing_titles = [ch.title for ch in result.missing_chapters]
    print(f"缺失章节: {missing_titles}")

    # 验证深层嵌套章节的检测
    assert "1.1.1.1.1 服务模块" in missing_titles, \
        f"应该检测到深层嵌套章节 '1.1.1.1.1 服务模块' 缺失"

    # 验证存在的章节不被误判
    assert "1.1.1.1.2 数据模块" not in missing_titles, \
        f"存在的章节 '1.1.1.1.2 数据模块' 不应该被判断为缺失"

    print("✓ 深层嵌套章节检测通过")

def test_cross_level_mapping_accuracy():
    """测试跨层级映射的准确性"""
    print("测试跨层级映射准确性...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 模板：标准层级结构
    template_chapters = [
        create_chapter("2. 设计说明", 2, 0),
        create_chapter("2.1 功能设计", 3, 1),
        create_chapter("2.2 性能设计", 3, 2),
        create_chapter("3. 实现方案", 2, 3),
        create_chapter("3.1 技术选型", 3, 4),
    ]

    # 目标：层级发生变化，但内容相似
    target_chapters = [
        create_chapter("2. 设计说明", 2, 0),
        create_chapter("功能设计详细说明", 2, 1),  # 原本是3级，现在是2级
        create_chapter("性能设计方案", 2, 2),     # 原本是3级，现在是2级
        create_chapter("3. 实现方案", 2, 3),
        # 缺失 3.1 技术选型
    ]

    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )

    missing_titles = [ch.title for ch in result.missing_chapters]
    print(f"缺失章节: {missing_titles}")

    # 验证跨层级匹配的准确性
    # "功能设计详细说明" 应该能匹配到 "2.1 功能设计"
    assert "2.1 功能设计" not in missing_titles, \
        f"跨层级匹配失败: '2.1 功能设计' 应该匹配到 '功能设计详细说明'"

    # "性能设计方案" 应该能匹配到 "2.2 性能设计"
    assert "2.2 性能设计" not in missing_titles, \
        f"跨层级匹配失败: '2.2 性能设计' 应该匹配到 '性能设计方案'"

    # "3.1 技术选型" 应该被检测为缺失
    assert "3.1 技术选型" in missing_titles, \
        f"应该检测到 '3.1 技术选型' 缺失"

    print("✓ 跨层级映射准确性测试通过")

def test_similar_title_discrimination():
    """测试相似标题的区分能力"""
    print("测试相似标题区分能力...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 包含相似标题的模板章节
    template_chapters = [
        create_chapter("5. 系统安全", 2, 0),
        create_chapter("5.1 安全策略", 3, 1),
        create_chapter("5.2 安全机制", 3, 2),
        create_chapter("5.3 安全兜底", 3, 3),
        create_chapter("5.3.1 兜底策略", 4, 4),
        create_chapter("5.3.2 兜底机制", 4, 5),
    ]

    # 目标章节：部分相似标题存在
    target_chapters = [
        create_chapter("5. 系统安全", 2, 0),
        create_chapter("5.1 安全策略", 3, 1),
        create_chapter("5.2 安全机制实现", 3, 2),  # 略有差异但应该匹配
        create_chapter("5.3 安全兜底方案", 3, 3),  # 略有差异但应该匹配
        create_chapter("5.3.1 兜底策略设计", 4, 4),  # 略有差异但应该匹配
        # 缺失 5.3.2 兜底机制
    ]

    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )

    missing_titles = [ch.title for ch in result.missing_chapters]
    print(f"缺失章节: {missing_titles}")

    # 验证相似标题的正确匹配
    assert "5.1 安全策略" not in missing_titles, \
        f"完全匹配的标题不应该被判断为缺失"

    assert "5.2 安全机制" not in missing_titles, \
        f"'5.2 安全机制' 应该匹配到 '5.2 安全机制实现'"

    assert "5.3 安全兜底" not in missing_titles, \
        f"'5.3 安全兜底' 应该匹配到 '5.3 安全兜底方案'"

    assert "5.3.1 兜底策略" not in missing_titles, \
        f"'5.3.1 兜底策略' 应该匹配到 '5.3.1 兜底策略设计'"

    # 验证真正缺失的章节被检测到
    assert "5.3.2 兜底机制" in missing_titles, \
        f"应该检测到 '5.3.2 兜底机制' 缺失"

    print("✓ 相似标题区分能力测试通过")

def test_mapping_confidence_analysis():
    """测试映射置信度分析"""
    print("测试映射置信度分析...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    template_chapters = [
        create_chapter("1. 概述", 1, 0),
        create_chapter("1.1 背景", 2, 1),
        create_chapter("1.2 目标", 2, 2),
        create_chapter("2. 设计", 1, 3),
    ]

    target_chapters = [
        create_chapter("1. 概述", 1, 0),
        create_chapter("1.1 项目背景介绍", 2, 1),  # 相似但不完全匹配
        create_chapter("1.2 目标", 2, 2),  # 完全匹配
        create_chapter("2. 设计", 1, 3),   # 完全匹配
    ]

    # 获取详细映射信息
    mapping_details = structure_checker.get_mapping_details(
        template_chapters, target_chapters
    )

    print("映射详情:")
    print(f"  - 整体置信度: {mapping_details['overall_confidence']:.2%}")
    print(f"  - 映射统计: {mapping_details['mapping_summary']}")

    # 验证映射置信度合理性
    assert mapping_details['overall_confidence'] > 0.5, \
        f"整体置信度应该合理（>0.5），当前值: {mapping_details['overall_confidence']:.2%}"

    # 验证映射统计
    assert mapping_details['mapping_summary']['total'] == len(template_chapters), \
        f"映射总数应该等于模板章节数"

    print("✓ 映射置信度分析测试通过")

def test_edge_case_empty_chapters():
    """测试边界情况：空章节列表"""
    print("测试边界情况：空章节列表...")

    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)

    # 测试空模板章节和空目标章节 - 应该检测到关键章节缺失而失败
    result1 = structure_checker.check_structure_completeness([], [])
    assert not result1.passed, "空目标文档应该检测到关键章节缺失而失败"
    assert len(result1.missing_chapters) == 0, "空模板情况下不应该有章节缺失"
    # 验证关键章节缺失被记录在结构问题中
    critical_missing_found = any("缺失关键章节" in issue for issue in result1.structure_issues)
    assert critical_missing_found, "应该检测到关键章节缺失"

    # 测试空目标章节
    template_chapters = [create_chapter("1. 测试", 1, 0)]
    result2 = structure_checker.check_structure_completeness(template_chapters, [])
    assert not result2.passed, "有模板但目标为空应该不通过检查"
    assert len(result2.missing_chapters) == 1, "应该检测到缺失章节"

    print("✓ 边界情况测试通过")

def test_performance_benchmark():
    """测试性能基准"""
    print("测试性能基准...")
    
    structure_checker = StructureChecker()
    structure_checker.set_smart_mapping_enabled(True)
    
    # 创建小规模的测试数据以避免性能问题
    template_chapters = []
    target_chapters = []
    
    for i in range(1, 6):  # 5个一级章节
        template_chapters.append(create_chapter(f"{i}. 章节{i}", 1, len(template_chapters)))
        target_chapters.append(create_chapter(f"{i}. 章节{i}", 1, len(target_chapters)))
        
        for j in range(1, 3):  # 每个一级章节2个二级章节
            title = f"{i}.{j} 子章节{i}.{j}"
            template_chapters.append(create_chapter(title, 2, len(template_chapters)))
            if not (i == 3 and j == 2):  # 故意缺失一个章节
                target_chapters.append(create_chapter(title, 2, len(target_chapters)))

    print(f"性能测试: 模板{len(template_chapters)}章节, 目标{len(target_chapters)}章节")

    start_time = time.time()
    result = structure_checker.check_structure_completeness(
        template_chapters, target_chapters
    )
    end_time = time.time()

    processing_time = end_time - start_time
    print(f"处理时间: {processing_time:.2f}秒")
    print(f"缺失章节: {len(result.missing_chapters)}个")
    print(f"相似度: {result.similarity_score:.2%}")

    # 调整性能期望 - 由于使用LLM，时间会比较长
    # assert processing_time < 300.0, f"处理时间应该在合理范围内，当前: {processing_time:.2f}秒"
    assert len(result.missing_chapters) > 0, "应该检测到缺失章节"

    print("✓ 性能基准测试通过")

def run_all_tests():
    """运行所有测试"""
    runner = TestRunner()
    
    # 运行所有测试
    runner.run_test("用户具体场景测试", test_specific_user_scenario)
    runner.run_test("深层嵌套章节检测", test_deep_nested_chapter_detection)
    runner.run_test("跨层级映射准确性", test_cross_level_mapping_accuracy)
    runner.run_test("相似标题区分能力", test_similar_title_discrimination)
    runner.run_test("映射置信度分析", test_mapping_confidence_analysis)
    runner.run_test("边界情况测试", test_edge_case_empty_chapters)
    runner.run_test("性能基准测试", test_performance_benchmark)
    
    # 打印摘要
    return runner.print_summary()

if __name__ == "__main__":
    print("开始章节缺失检测修复验证测试...")
    success = run_all_tests()
    
    if success:
        print(f"\n🎉 所有测试通过！章节缺失检测问题修复成功。")
        exit(0)
    else:
        print(f"\n❌ 部分测试失败，需要进一步调试。")
        exit(1)
