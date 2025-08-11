#!/usr/bin/env python3
"""
验证关键章节检查现在支持一到三级章节
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


def test_multi_level_critical_chapters():
    """测试一到三级章节的关键章节检查"""
    logger.info("开始测试一到三级章节的关键章节检查")
    
    # 创建结构检查器
    checker = StructureChecker()
    
    # 模拟LLM检查方法
    def mock_llm_check(required_chapter: str, critical_level_titles: List[str]) -> bool:
        return False  # 简单返回False，依赖文本匹配
    
    checker._llm_critical_chapter_check = mock_llm_check
    
    # 测试用例1：关键章节在二级
    logger.info("\n=== 测试用例1：关键章节在二级 ===")
    test_chapters_1 = create_test_chapters([
        ("概述", 1),
        ("系统设计", 1),
        ("可靠性设计", 2),  # 二级章节
        ("安全性要求", 2),  # 二级章节
        ("实施方案", 1)
    ])
    
    missing_critical_1 = checker._check_critical_chapters(test_chapters_1)
    logger.info(f"缺失关键章节: {missing_critical_1}")
    assert len(missing_critical_1) == 0, "应该在二级章节中找到关键章节"
    
    # 测试用例2：关键章节在三级
    logger.info("\n=== 测试用例2：关键章节在三级 ===")
    test_chapters_2 = create_test_chapters([
        ("概述", 1),
        ("系统设计", 1),
        ("详细设计", 2),
        ("可靠性设计", 3),  # 三级章节
        ("安全性要求", 3),  # 三级章节
        ("实施方案", 1)
    ])
    
    missing_critical_2 = checker._check_critical_chapters(test_chapters_2)
    logger.info(f"缺失关键章节: {missing_critical_2}")
    assert len(missing_critical_2) == 0, "应该在三级章节中找到关键章节"
    
    # 测试用例3：关键章节在四级（不应该被检查）
    logger.info("\n=== 测试用例3：关键章节在四级（不应该被检查）===")
    test_chapters_3 = create_test_chapters([
        ("概述", 1),
        ("系统设计", 1),
        ("详细设计", 2),
        ("子系统设计", 3),
        ("可靠性设计", 4),  # 四级章节，不应该被检查
        ("安全性要求", 4),  # 四级章节，不应该被检查
        ("实施方案", 1)
    ])
    
    missing_critical_3 = checker._check_critical_chapters(test_chapters_3)
    logger.info(f"缺失关键章节: {missing_critical_3}")
    assert len(missing_critical_3) == 2, "四级章节不应该被检查，所以应该报告缺失"
    assert "可靠性" in missing_critical_3 and "安全性" in missing_critical_3, "应该报告可靠性和安全性都缺失"
    
    # 测试用例4：混合级别
    logger.info("\n=== 测试用例4：混合级别 ===")
    test_chapters_4 = create_test_chapters([
        ("概述", 1),
        ("系统设计", 1),
        ("可靠性设计", 2),  # 二级章节
        ("详细设计", 2),
        ("安全性要求", 3),  # 三级章节
        ("实施方案", 1)
    ])
    
    missing_critical_4 = checker._check_critical_chapters(test_chapters_4)
    logger.info(f"缺失关键章节: {missing_critical_4}")
    assert len(missing_critical_4) == 0, "应该在不同级别中找到关键章节"
    
    logger.info("\n🎉 一到三级章节的关键章节检查功能验证通过！")


if __name__ == "__main__":
    try:
        test_multi_level_critical_chapters()
        logger.info("\n✅ 验证完成：关键章节检查现在支持一到三级章节！")
    except Exception as e:
        logger.error(f"验证失败: {e}")
        raise
