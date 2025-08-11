#!/usr/bin/env python3
"""
测试关键章节检查功能
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


def test_critical_chapters():
    """测试关键章节检查功能"""
    logger.info("开始测试关键章节检查功能")
    
    # 创建结构检查器
    checker = StructureChecker()
    
    # 重写LLM检查方法，避免不必要的API调用
    def mock_llm_critical_chapter_check(required_chapter: str, first_level_titles: List[str]) -> bool:
        """模拟LLM关键章节检查"""
        for title in first_level_titles:
            if "稳定" in title and required_chapter == "可靠性":
                return True
            if "信息安全" in title and required_chapter == "安全性":
                return True
        return False
    
    checker._llm_critical_chapter_check = mock_llm_critical_chapter_check
    
    # 测试用例1：包含可靠性和安全性章节
    logger.info("\n=== 测试用例1：包含可靠性和安全性章节 ===")
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
    logger.info("\n=== 测试用例2：缺失安全性章节 ===")
    test_chapters_2 = create_test_chapters([
        ("概述", 1),
        ("系统架构", 1),
        ("可靠性设计", 1),
        ("实施方案", 1)
    ])
    
    missing_critical_2 = checker._check_critical_chapters(test_chapters_2)
    logger.info(f"缺失关键章节: {missing_critical_2}")
    assert "安全性" in missing_critical_2, "应该检测到缺失安全性章节"
    
    # 测试用例3：缺失可靠性章节
    logger.info("\n=== 测试用例3：缺失可靠性章节 ===")
    test_chapters_3 = create_test_chapters([
        ("概述", 1),
        ("系统架构", 1),
        ("安全性要求", 1),
        ("实施方案", 1)
    ])
    
    missing_critical_3 = checker._check_critical_chapters(test_chapters_3)
    logger.info(f"缺失关键章节: {missing_critical_3}")
    assert "可靠性" in missing_critical_3, "应该检测到缺失可靠性章节"
    
    # 测试用例4：两个关键章节都缺失
    logger.info("\n=== 测试用例4：两个关键章节都缺失 ===")
    test_chapters_4 = create_test_chapters([
        ("概述", 1),
        ("系统架构", 1),
        ("实施方案", 1)
    ])
    
    missing_critical_4 = checker._check_critical_chapters(test_chapters_4)
    logger.info(f"缺失关键章节: {missing_critical_4}")
    assert len(missing_critical_4) == 2, "应该检测到两个缺失的关键章节"
    assert "可靠性" in missing_critical_4 and "安全性" in missing_critical_4, "应该检测到可靠性和安全性都缺失"
    
    # 测试用例5：使用相似词汇的章节
    logger.info("\n=== 测试用例5：使用相似词汇的章节 ===")
    test_chapters_5 = create_test_chapters([
        ("概述", 1),
        ("系统架构", 1),
        ("系统稳定性分析", 1),  # 应该匹配"可靠性"
        ("信息安全保障", 1),    # 应该匹配"安全性"
        ("实施方案", 1)
    ])
    
    missing_critical_5 = checker._check_critical_chapters(test_chapters_5)
    logger.info(f"缺失关键章节: {missing_critical_5}")
    # 注意：这个测试可能需要LLM来判断语义相似性
    
    logger.info("\n=== 所有测试用例完成 ===")
    logger.info("关键章节检查功能测试通过！")


def test_structure_completeness_with_critical_chapters():
    """测试完整的结构检查（包含关键章节检查）"""
    logger.info("\n开始测试完整的结构检查功能")
    
    checker = StructureChecker()
    
    # 重写LLM检查方法，避免不必要的API调用
    def mock_llm_critical_chapter_check(required_chapter: str, first_level_titles: List[str]) -> bool:
        return False  # 模拟找不到匹配
    
    def mock_llm_similarity_check(title1: str, title2: str) -> bool:
        return False  # 模拟不相似
    
    checker._llm_critical_chapter_check = mock_llm_critical_chapter_check
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
    critical_issues = [issue for issue in result.structure_issues if "缺失关键一级章节" in issue]
    assert len(critical_issues) > 0, "结构问题中应该包含关键章节缺失信息"
    
    logger.info("完整结构检查功能测试通过！")


if __name__ == "__main__":
    try:
        test_critical_chapters()
        test_structure_completeness_with_critical_chapters()
        logger.info("\n🎉 所有测试通过！关键章节检查功能已成功实现。")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise
