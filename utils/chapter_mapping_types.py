"""
章节映射相关的数据结构和枚举类型
用于智能章节映射算法
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

from utils.html_parser import ChapterInfo


class MatchType(Enum):
    """匹配类型枚举"""
    EXACT = "exact"           # 精确匹配（编号+标题完全相同）
    SIMILAR = "similar"       # 相似匹配（标题相似度高）
    SEMANTIC = "semantic"     # 语义匹配（LLM判断语义相同）
    POSITIONAL = "positional" # 位置匹配（结构位置对应）
    NONE = "none"            # 无匹配


class MatchConfidence(Enum):
    """匹配置信度枚举"""
    HIGH = "high"       # 高置信度 (>0.8)
    MEDIUM = "medium"   # 中等置信度 (0.5-0.8)
    LOW = "low"         # 低置信度 (<0.5)


class RenumberingPatternType(Enum):
    """重编号模式类型"""
    OFFSET = "offset"         # 编号偏移（整体+N或-N）
    REORDER = "reorder"       # 重新排序
    MIXED = "mixed"           # 混合模式
    INSERTION = "insertion"   # 插入新章节导致的重编号
    DELETION = "deletion"     # 删除章节导致的重编号
    NONE = "none"            # 无重编号模式


@dataclass
class SimilarityScores:
    """相似度分数"""
    title_similarity: float = 0.0      # 标题相似度
    content_similarity: float = 0.0    # 内容相似度
    position_similarity: float = 0.0   # 位置相似度
    structure_similarity: float = 0.0  # 结构相似度
    overall_similarity: float = 0.0    # 综合相似度


@dataclass
class ChapterMapping:
    """章节映射关系"""
    template_chapter: ChapterInfo
    target_chapter: Optional[ChapterInfo]
    match_type: MatchType
    confidence: float
    confidence_level: MatchConfidence
    similarity_scores: SimilarityScores
    llm_reasoning: str = ""              # LLM推理过程
    mapping_notes: str = ""              # 映射备注


@dataclass
class RenumberingPattern:
    """重编号模式"""
    pattern_type: RenumberingPatternType
    offset_value: int = 0                    # 编号偏移量
    affected_levels: List[int] = None        # 受影响的章节层级
    confidence: float = 0.0                  # 模式置信度
    examples: List[Tuple[str, str]] = None   # 示例对比 (template_number, target_number)
    description: str = ""                    # 模式描述
    
    def __post_init__(self):
        if self.affected_levels is None:
            self.affected_levels = []
        if self.examples is None:
            self.examples = []


@dataclass
class MappingResult:
    """映射结果"""
    mappings: List[ChapterMapping]
    unmapped_template: List[ChapterInfo]         # 模板中未映射的章节
    unmapped_target: List[ChapterInfo]           # 目标中未映射的章节
    renumbering_patterns: List[RenumberingPattern]
    overall_confidence: float
    mapping_summary: Dict[str, int]              # 映射统计摘要
    performance_metrics: Dict[str, float] = None # 性能指标
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}


@dataclass
class MatchingContext:
    """匹配上下文信息"""
    template_chapters: List[ChapterInfo]
    target_chapters: List[ChapterInfo]
    parent_mappings: Dict[str, ChapterMapping] = None  # 父章节映射关系
    sibling_mappings: List[ChapterMapping] = None      # 同级章节映射关系
    global_patterns: List[RenumberingPattern] = None   # 全局重编号模式
    
    def __post_init__(self):
        if self.parent_mappings is None:
            self.parent_mappings = {}
        if self.sibling_mappings is None:
            self.sibling_mappings = []
        if self.global_patterns is None:
            self.global_patterns = []


@dataclass
class BatchSemanticRequest:
    """批量语义匹配请求"""
    template_titles: List[str]
    target_titles: List[str]
    context_info: str = ""
    max_batch_size: int = 10


@dataclass
class BatchSemanticResponse:
    """批量语义匹配响应"""
    similarity_matrix: List[List[float]]  # 相似度矩阵
    reasoning_matrix: List[List[str]]     # 推理过程矩阵
    processing_time: float = 0.0
    api_calls_count: int = 0


def get_confidence_level(score: float) -> MatchConfidence:
    """根据分数获取置信度等级"""
    if score >= 0.8:
        return MatchConfidence.HIGH
    elif score >= 0.5:
        return MatchConfidence.MEDIUM
    else:
        return MatchConfidence.LOW


def calculate_overall_similarity(scores: SimilarityScores, 
                               weights: Dict[str, float] = None) -> float:
    """计算综合相似度分数"""
    if weights is None:
        # 默认权重配置
        weights = {
            'title': 0.4,
            'content': 0.3,
            'position': 0.2,
            'structure': 0.1
        }
    
    overall = (
        scores.title_similarity * weights.get('title', 0.4) +
        scores.content_similarity * weights.get('content', 0.3) +
        scores.position_similarity * weights.get('position', 0.2) +
        scores.structure_similarity * weights.get('structure', 0.1)
    )
    
    return min(1.0, max(0.0, overall))


def create_empty_mapping(template_chapter: ChapterInfo) -> ChapterMapping:
    """创建空映射（表示未找到匹配）"""
    return ChapterMapping(
        template_chapter=template_chapter,
        target_chapter=None,
        match_type=MatchType.NONE,
        confidence=0.0,
        confidence_level=MatchConfidence.LOW,
        similarity_scores=SimilarityScores(),
        llm_reasoning="未找到匹配的章节",
        mapping_notes="该章节在目标文档中缺失"
    )


def create_mapping(template_chapter: ChapterInfo, 
                  target_chapter: ChapterInfo,
                  match_type: MatchType,
                  similarity_scores: SimilarityScores,
                  llm_reasoning: str = "",
                  mapping_notes: str = "") -> ChapterMapping:
    """创建章节映射"""
    # 计算综合相似度
    overall_similarity = calculate_overall_similarity(similarity_scores)
    similarity_scores.overall_similarity = overall_similarity
    
    return ChapterMapping(
        template_chapter=template_chapter,
        target_chapter=target_chapter,
        match_type=match_type,
        confidence=overall_similarity,
        confidence_level=get_confidence_level(overall_similarity),
        similarity_scores=similarity_scores,
        llm_reasoning=llm_reasoning,
        mapping_notes=mapping_notes
    )
