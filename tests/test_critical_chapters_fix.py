#!/usr/bin/env python3
"""
测试关键章节检查修复
验证当目标章节为空时，关键章节检查的正确行为
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.structure_checker import StructureChecker
from utils.html_parser import ChapterInfo
from config.config import config

# 配置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_empty_target_chapters():
    """测试目标章节为空时的关键章节检查"""
    print("测试目标章节为空时的关键章节检查...")

    structure_checker = StructureChecker()

    # 测试空的目标章节
    result = structure_checker._check_critical_chapters([])

    print(f"空目标章节检查结果: {result}")

    # 验证结果
    expected_missing = config.structure_check.required_critical_chapters
    print(f"期望的缺失章节: {expected_missing}")

    assert result == expected_missing, f"期望返回 {expected_missing}，但得到 {result}"
    print("✓ 空目标章节测试通过")

def test_target_with_critical_chapters():
    """测试目标章节包含关键章节时的检查"""
    print("\n测试目标章节包含关键章节时的检查...")

    structure_checker = StructureChecker()

    # 创建包含关键章节的目标章节
    target_chapters = [
        ChapterInfo(title="1. 系统概述", level=1, content="", images=[], position=0),
        ChapterInfo(title="2. 功能设计", level=1, content="", images=[], position=1),
        ChapterInfo(title="3. 安全性设计", level=1, content="", images=[], position=2),  # 包含"安全性"
        ChapterInfo(title="4. 可靠性保证", level=1, content="", images=[], position=3),  # 包含"可靠性"
    ]

    result = structure_checker._check_critical_chapters(target_chapters)

    print(f"包含关键章节的目标文档检查结果: {result}")

    # 应该没有缺失的关键章节
    assert result == [], f"期望返回空列表，但得到 {result}"
    print("✓ 包含关键章节测试通过")

def test_target_without_critical_chapters():
    """测试目标章节不包含关键章节时的检查"""
    print("\n测试目标章节不包含关键章节时的检查...")

    structure_checker = StructureChecker()

    # 创建不包含关键章节的目标章节
    target_chapters = [
        ChapterInfo(title="1. 系统概述", level=1, content="", images=[], position=0),
        ChapterInfo(title="2. 功能设计", level=1, content="", images=[], position=1),
        ChapterInfo(title="3. 性能优化", level=1, content="", images=[], position=2),
        ChapterInfo(title="4. 部署说明", level=1, content="", images=[], position=3),
    ]

    result = structure_checker._check_critical_chapters(target_chapters)

    print(f"不包含关键章节的目标文档检查结果: {result}")

    # 应该返回所有必需的关键章节
    expected_missing = config.structure_check.required_critical_chapters
    assert result == expected_missing, f"期望返回 {expected_missing}，但得到 {result}"
    print("✓ 不包含关键章节测试通过")

def run_all_tests():
    """运行所有测试"""
    print("开始关键章节检查修复验证测试...")
    print(f"配置的必需关键章节: {config.structure_check.required_critical_chapters}")

    try:
        test_empty_target_chapters()
        test_target_with_critical_chapters()
        test_target_without_critical_chapters()

        print("\n🎉 所有测试通过！关键章节检查修复成功。")
        print("\n修复总结:")
        print("✓ 当目标章节为空时，返回所有必需的关键章节作为缺失")
        print("✓ 当目标章节包含关键章节时，正确识别并返回空列表")
        print("✓ 当目标章节不包含关键章节时，返回所有必需的关键章节")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
