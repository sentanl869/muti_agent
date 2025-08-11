#!/usr/bin/env python3
"""
测试关键章节检查功能（简化版本，不依赖LLM）
"""

import logging
import sys
import os
from typing import List

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.structure_checker import StructureChecker
from utils.html_parser import ChapterInfo

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_chapters(titles_and_levels: List[tuple]) -> List[ChapterInfo]:
    """创建测试章节数据"""
    chapters = []
    for i, (title, level) in enumerate(titles_and_levels):
        chapter = ChapterInfo(
            title=title,
            level=level,
            content="",
            images=[],
            position=i,
            html_id="",
            parent_path=""
        )
        chapters.append(chapter)
    return chapters


def test_critical_chapter_matching():
    """测试关键章节匹配功能（不依赖LLM）"""
    logger.info("开始测试关键章节匹配功能")
    
    # 创建结构检查器
    checker = StructureChecker()
    
    # 测试文本匹配功能
    logger.info("\n=== 测试文本匹配功能 ===")
    
    # 测试精确匹配
    assert checker._is_critical_chapter_match("可靠性", "可靠性设计"), "应该匹配可靠性"
    assert checker._is_critical_chapter_match("安全性", "安全性要求"), "应该匹配安全性"
    
    # 测试不匹配的情况
    assert not checker._is_critical_chapter_match("可靠性", "系统架构"), "不应该匹配系统架构"
    assert not checker._is_critical_chapter_match("安全性", "实施方案"), "不应该匹配实施方案"
    
    logger.info("文本匹配功能测试通过！")


def test_first_level_extraction():
    """测试一级章节提取功能"""
    logger.info("\n=== 测试一级章节提取功能 ===")
    
    # 创建测试章节（包含多级）
    test_chapters = create_test_chapters([
        ("概述", 1),
        ("系统架构", 1),
        ("详细设计", 2),
        ("可靠性设计", 1),
        ("安全性要求", 1),
        ("子安全模块", 2),
        ("实施方案", 1)
    ])
    
    # 提取一级章节
    first_level_titles = [
        chapter.title for chapter in test_chapters 
        if chapter.level == 1
    ]
    
    expected_first_level = ["概述", "系统架构", "可靠性设计", "安全性要求", "实施方案"]
    
    logger.info(f"提取的一级章节: {first_level_titles}")
    logger.info(f"期望的一级章节: {expected_first_level}")
    
    assert len(first_level_titles) == 5, f"应该有5个一级章节，实际有{len(first_level_titles)}个"
    assert first_level_titles == expected_first_level, "一级章节列表不匹配"
    
    logger.info("一级章节提取功能测试通过！")


def test_critical_chapters_basic():
    """测试关键章节检查基本功能（模拟LLM失败的情况）"""
    logger.info("\n=== 测试关键章节检查基本功能 ===")
    
    # 创建结构检查器
    checker = StructureChecker()
    
    # 重写LLM检查方法，避免实际调用LLM
    def mock_llm_check(required_chapter: str, critical_level_titles: List[str]) -> bool:
        """模拟LLM检查，基于简单规则"""
        for title in critical_level_titles:
            if "稳定" in title and required_chapter == "可靠性":
                return True
            if "信息安全" in title and required_chapter == "安全性":
                return True
        return False
    
    # 替换LLM检查方法
    checker._llm_critical_chapter_check = mock_llm_check
    
    # 测试用例1：包含可靠性和安全性章节
    logger.info("\n--- 测试用例1：包含可靠性和安全性章节 ---")
    test_chapters_1 = create_test_chapters([
        ("概述", 1),
        ("系统架构", 1),
        ("可靠性设计", 1),
        ("安全性要求", 1),
        ("实施方案", 1)
    ])
    
    missing_critical_1 = checker._check_critical_chapters(test_chapters_1)
    logger.info(f"缺失关键章节: {missing_critical_1}")
    assert len(missing_critical_1) == 0, "应该没有缺失关键章节"
    
    # 测试用例2：缺失安全性章节
    logger.info("\n--- 测试用例2：缺失安全性章节 ---")
    test_chapters_2 = create_test_chapters([
        ("概述", 1),
        ("系统架构", 1),
        ("可靠性设计", 1),
        ("实施方案", 1)
    ])
    
    missing_critical_2 = checker._check_critical_chapters(test_chapters_2)
    logger.info(f"缺失关键章节: {missing_critical_2}")
    assert "安全性" in missing_critical_2, "应该检测到缺失安全性章节"
    
    # 测试用例3：使用相似词汇的章节（通过模拟LLM匹配）
    logger.info("\n--- 测试用例3：使用相似词汇的章节 ---")
    test_chapters_3 = create_test_chapters([
        ("概述", 1),
        ("系统架构", 1),
        ("系统稳定性分析", 1),  # 应该通过模拟LLM匹配"可靠性"
        ("信息安全保障", 1),    # 应该通过模拟LLM匹配"安全性"
        ("实施方案", 1)
    ])
    
    missing_critical_3 = checker._check_critical_chapters(test_chapters_3)
    logger.info(f"缺失关键章节: {missing_critical_3}")
    assert len(missing_critical_3) == 0, "应该通过模拟LLM匹配找到所有关键章节"
    
    logger.info("关键章节检查基本功能测试通过！")


def test_structure_completeness_integration():
    """测试结构检查集成功能"""
    logger.info("\n=== 测试结构检查集成功能 ===")
    
    checker = StructureChecker()
    
    # 重写LLM检查方法，避免实际调用LLM
    def mock_llm_check(required_chapter: str, critical_level_titles: List[str]) -> bool:
        return False  # 模拟找不到匹配
    
    # 重写LLM相似度检查方法，避免实际调用LLM
    def mock_llm_similarity_check(title1: str, title2: str) -> bool:
        return False  # 模拟不相似
    
    checker._llm_critical_chapter_check = mock_llm_check
    checker._llm_similarity_check = mock_llm_similarity_check
    
    # 模板章节（简单示例）
    template_chapters = create_test_chapters([
        ("概述", 1),
        ("系统设计", 1),
        ("详细设计", 2),
        ("实施方案", 1)
    ])
    
    # 目标章节（缺失关键章节）
    target_chapters = create_test_chapters([
        ("概述", 1),
        ("系统设计", 1),
        ("详细设计", 2),
        ("实施方案", 1)
    ])
    
    result = checker.check_structure_completeness(template_chapters, target_chapters)
    
    logger.info(f"结构检查结果: {'通过' if result.passed else '失败'}")
    logger.info(f"结构问题: {result.structure_issues}")
    
    # 应该因为缺失关键章节而失败
    assert not result.passed, "应该因为缺失关键章节而检查失败"
    
    # 检查结构问题中是否包含关键章节缺失信息
    critical_issues = [issue for issue in result.structure_issues if "缺失关键章节" in issue]
    logger.info(f"关键章节相关问题: {critical_issues}")
    assert len(critical_issues) > 0, "结构问题中应该包含关键章节缺失信息"
    
    # 验证具体的缺失章节
    assert any("可靠性" in issue for issue in critical_issues), "应该包含可靠性缺失信息"
    assert any("安全性" in issue for issue in critical_issues), "应该包含安全性缺失信息"
    
    logger.info("结构检查集成功能测试通过！")


if __name__ == "__main__":
    try:
        test_critical_chapter_matching()
        test_first_level_extraction()
        test_critical_chapters_basic()
        test_structure_completeness_integration()
        logger.info("\n🎉 所有测试通过！关键章节检查功能已成功实现。")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise
