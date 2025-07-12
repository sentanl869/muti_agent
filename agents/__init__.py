"""
Agent 模块
包含文档获取、结构检查、内容检查、报告生成等 Agent
"""

from .document_fetcher import DocumentFetcher
from .structure_checker import StructureChecker, StructureCheckResult, MissingChapter, StructureNode
from .content_checker import ContentChecker, ContentCheckResult, Violation, ChapterCheckResult
from .report_generator import ReportGenerator

__all__ = [
    'DocumentFetcher',
    'StructureChecker',
    'StructureCheckResult',
    'MissingChapter',
    'StructureNode',
    'ContentChecker',
    'ContentCheckResult',
    'Violation',
    'ChapterCheckResult',
    'ReportGenerator'
]
