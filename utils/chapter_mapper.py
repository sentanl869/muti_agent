"""
章节映射器核心算法
负责建立模板章节与目标章节之间的智能映射关系
"""

import logging
import time
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

from utils.html_parser import ChapterInfo
from utils.chapter_mapping_types import (
    ChapterMapping, MappingResult, MatchType, SimilarityScores,
    MatchingContext, BatchSemanticRequest, create_mapping, create_empty_mapping
)
from utils.semantic_matcher import SemanticMatcher
from utils.renumbering_detector import RenumberingDetector

logger = logging.getLogger(__name__)


@dataclass
class MappingConfig:
    """映射配置"""
    similarity_threshold: float = 0.5      # 相似度阈值
    exact_match_threshold: float = 0.95    # 精确匹配阈值
    semantic_match_threshold: float = 0.7  # 语义匹配阈值
    position_weight: float = 0.2           # 位置权重
    title_weight: float = 0.4              # 标题权重
    content_weight: float = 0.3            # 内容权重
    structure_weight: float = 0.1          # 结构权重
    max_batch_size: int = 10               # 批量处理大小
    enable_context_aware: bool = True      # 启用上下文感知
    enable_renumbering_detection: bool = True  # 启用重编号检测


class ChapterMapper:
    """章节映射器"""
    
    def __init__(self, config: MappingConfig = None):
        self.config = config or MappingConfig()
        self.semantic_matcher = SemanticMatcher()
        self.renumbering_detector = RenumberingDetector()
        
    def create_global_mapping(self, template_chapters: List[ChapterInfo], 
                            target_chapters: List[ChapterInfo]) -> MappingResult:
        """
        创建全局章节映射关系
        
        Args:
            template_chapters: 模板章节列表
            target_chapters: 目标章节列表
            
        Returns:
            映射结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始创建全局章节映射: 模板{len(template_chapters)}章节 -> 目标{len(target_chapters)}章节")
            
            # 1. 检测重编号模式
            renumbering_patterns = []
            if self.config.enable_renumbering_detection:
                renumbering_patterns = self.renumbering_detector.detect_patterns(
                    template_chapters, target_chapters
                )
            
            # 2. 构建匹配上下文
            context = MatchingContext(
                template_chapters=template_chapters,
                target_chapters=target_chapters,
                global_patterns=renumbering_patterns
            )
            
            # 3. 计算相似度矩阵
            similarity_matrix = self.calculate_similarity_matrix(
                template_chapters, target_chapters, context
            )
            
            # 4. 寻找最优映射
            mappings = self.find_optimal_mapping(
                template_chapters, target_chapters, similarity_matrix, context
            )
            
            # 5. 分析映射结果
            unmapped_template, unmapped_target = self._analyze_unmapped_chapters(
                template_chapters, target_chapters, mappings
            )
            
            # 6. 计算整体置信度
            overall_confidence = self._calculate_overall_confidence(mappings)
            
            # 7. 生成映射摘要
            mapping_summary = self._generate_mapping_summary(mappings)
            
            # 8. 性能指标
            processing_time = time.time() - start_time
            performance_metrics = {
                'processing_time': processing_time,
                'api_calls': self.semantic_matcher.get_api_call_stats()['total_api_calls'],
                'similarity_calculations': len(template_chapters) * len(target_chapters)
            }
            
            result = MappingResult(
                mappings=mappings,
                unmapped_template=unmapped_template,
                unmapped_target=unmapped_target,
                renumbering_patterns=renumbering_patterns,
                overall_confidence=overall_confidence,
                mapping_summary=mapping_summary,
                performance_metrics=performance_metrics
            )
            
            logger.info(f"全局映射完成: 耗时{processing_time:.2f}s, "
                       f"成功映射{len(mappings)}个, 整体置信度{overall_confidence:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"全局章节映射失败: {e}")
            # 返回空结果
            return MappingResult(
                mappings=[],
                unmapped_template=template_chapters,
                unmapped_target=target_chapters,
                renumbering_patterns=[],
                overall_confidence=0.0,
                mapping_summary={'total': 0, 'exact': 0, 'similar': 0, 'semantic': 0, 'positional': 0, 'none': 0},
                performance_metrics={'processing_time': time.time() - start_time}
            )
    
    def calculate_similarity_matrix(self, template_chapters: List[ChapterInfo], 
                                  target_chapters: List[ChapterInfo],
                                  context: MatchingContext) -> List[List[SimilarityScores]]:
        """
        计算章节相似度矩阵
        
        Args:
            template_chapters: 模板章节列表
            target_chapters: 目标章节列表
            context: 匹配上下文
            
        Returns:
            相似度矩阵
        """
        try:
            logger.info(f"计算相似度矩阵: {len(template_chapters)}x{len(target_chapters)}")
            
            # 初始化矩阵
            matrix = [[SimilarityScores() for _ in target_chapters] for _ in template_chapters]
            
            # 批量计算语义相似度
            semantic_matrix = self._calculate_semantic_similarity_batch(
                template_chapters, target_chapters, context
            )
            
            # 逐个计算其他相似度
            for i, template_ch in enumerate(template_chapters):
                for j, target_ch in enumerate(target_chapters):
                    scores = matrix[i][j]
                    
                    # 标题相似度
                    scores.title_similarity = self.semantic_matcher.calculate_title_similarity(
                        template_ch.title, target_ch.title
                    )
                    
                    # 内容相似度
                    scores.content_similarity = self.semantic_matcher.calculate_content_similarity(
                        template_ch.content, target_ch.content
                    )
                    
                    # 位置相似度
                    scores.position_similarity = self.semantic_matcher.calculate_position_similarity(
                        template_ch.position, target_ch.position, len(template_chapters)
                    )
                    
                    # 结构相似度（层级匹配）
                    scores.structure_similarity = 1.0 if template_ch.level == target_ch.level else 0.0
                    
                    # 语义相似度（从批量结果中获取）
                    if i < len(semantic_matrix) and j < len(semantic_matrix[i]):
                        # 这里暂时使用标题相似度作为语义相似度的基础
                        # 实际的语义相似度会在批量处理中计算
                        pass
                    
                    # 计算综合相似度
                    weights = {
                        'title': self.config.title_weight,
                        'content': self.config.content_weight,
                        'position': self.config.position_weight,
                        'structure': self.config.structure_weight
                    }
                    
                    scores.overall_similarity = (
                        scores.title_similarity * weights['title'] +
                        scores.content_similarity * weights['content'] +
                        scores.position_similarity * weights['position'] +
                        scores.structure_similarity * weights['structure']
                    )
            
            logger.info("相似度矩阵计算完成")
            return matrix
            
        except Exception as e:
            logger.error(f"相似度矩阵计算失败: {e}")
            # 返回空矩阵
            return [[SimilarityScores() for _ in target_chapters] for _ in template_chapters]
    
    def _calculate_semantic_similarity_batch(self, template_chapters: List[ChapterInfo], 
                                           target_chapters: List[ChapterInfo],
                                           context: MatchingContext) -> List[List[float]]:
        """批量计算语义相似度"""
        try:
            template_titles = [ch.title for ch in template_chapters]
            target_titles = [ch.title for ch in target_chapters]
            
            # 构建上下文信息
            context_info = ""
            if context.global_patterns:
                pattern_descriptions = [p.description for p in context.global_patterns if p.description]
                if pattern_descriptions:
                    context_info = f"重编号模式: {'; '.join(pattern_descriptions)}"
            
            # 批量语义匹配
            request = BatchSemanticRequest(
                template_titles=template_titles,
                target_titles=target_titles,
                context_info=context_info,
                max_batch_size=self.config.max_batch_size
            )
            
            response = self.semantic_matcher.batch_semantic_match(request)
            return response.similarity_matrix
            
        except Exception as e:
            logger.warning(f"批量语义相似度计算失败: {e}")
            # 返回零矩阵
            return [[0.0 for _ in target_chapters] for _ in template_chapters]
    
    def find_optimal_mapping(self, template_chapters: List[ChapterInfo], 
                           target_chapters: List[ChapterInfo],
                           similarity_matrix: List[List[SimilarityScores]],
                           context: MatchingContext) -> List[ChapterMapping]:
        """
        寻找最优映射方案
        
        Args:
            template_chapters: 模板章节列表
            target_chapters: 目标章节列表
            similarity_matrix: 相似度矩阵
            context: 匹配上下文
            
        Returns:
            章节映射列表
        """
        try:
            logger.info("开始寻找最优映射方案")
            
            mappings = []
            used_targets = set()  # 已使用的目标章节索引
            
            # 按层级分组处理
            template_by_level = self._group_by_level(template_chapters)
            target_by_level = self._group_by_level(target_chapters)
            
            for level in sorted(template_by_level.keys()):
                level_template = template_by_level[level]
                level_target = target_by_level.get(level, [])
                
                level_mappings = self._find_level_optimal_mapping(
                    level_template, level_target, template_chapters, target_chapters,
                    similarity_matrix, context, used_targets
                )
                
                mappings.extend(level_mappings)
                
                # 更新已使用的目标章节
                for mapping in level_mappings:
                    if mapping.target_chapter:
                        try:
                            target_idx = target_chapters.index(mapping.target_chapter)
                            used_targets.add(target_idx)
                        except ValueError:
                            logger.warning(f"目标章节不在列表中: {mapping.target_chapter.title}")
            
            # 处理未映射的模板章节
            for template_ch in template_chapters:
                if not any(m.template_chapter == template_ch for m in mappings):
                    empty_mapping = create_empty_mapping(template_ch)
                    mappings.append(empty_mapping)
            
            logger.info(f"最优映射完成: 找到{len(mappings)}个映射")
            return mappings
            
        except Exception as e:
            logger.error(f"最优映射查找失败: {e}")
            # 返回空映射
            return [create_empty_mapping(ch) for ch in template_chapters]
    
    def _group_by_level(self, chapters: List[ChapterInfo]) -> Dict[int, List[ChapterInfo]]:
        """按层级分组章节"""
        groups = {}
        for chapter in chapters:
            if chapter.level not in groups:
                groups[chapter.level] = []
            groups[chapter.level].append(chapter)
        return groups
    
    def _find_level_optimal_mapping(self, level_template: List[ChapterInfo],
                                  level_target: List[ChapterInfo],
                                  all_template: List[ChapterInfo],
                                  all_target: List[ChapterInfo],
                                  similarity_matrix: List[List[SimilarityScores]],
                                  context: MatchingContext,
                                  used_targets: Set[int]) -> List[ChapterMapping]:
        """寻找特定层级的最优映射"""
        mappings = []
        
        try:
            if not level_template:
                return mappings
            
            # 为每个模板章节寻找最佳匹配
            for template_ch in level_template:
                template_idx = all_template.index(template_ch)
                
                best_target = None
                best_target_idx = -1
                best_score = 0.0
                best_match_type = MatchType.NONE
                best_scores = SimilarityScores()
                best_reasoning = ""
                
                # 在同层级的目标章节中寻找最佳匹配
                for target_ch in level_target:
                    target_idx = all_target.index(target_ch)
                    
                    # 跳过已使用的目标章节
                    if target_idx in used_targets:
                        logger.debug(f"跳过已使用的目标章节: {target_ch.title} (索引: {target_idx})")
                        continue
                    
                    # 获取相似度分数
                    if template_idx < len(similarity_matrix) and target_idx < len(similarity_matrix[template_idx]):
                        scores = similarity_matrix[template_idx][target_idx]
                        overall_score = scores.overall_similarity
                        
                        # 确定匹配类型
                        match_type = self._determine_match_type(scores)
                        
                        logger.debug(f"评估映射: {template_ch.title} -> {target_ch.title}, 相似度: {overall_score:.2f}")
                        
                        # 检查是否为更好的匹配
                        if overall_score > best_score and overall_score >= self.config.similarity_threshold:
                            best_target = target_ch
                            best_target_idx = target_idx
                            best_score = overall_score
                            best_match_type = match_type
                            best_scores = scores
                            best_reasoning = f"相似度: {overall_score:.2f}, 类型: {match_type.value}"
                            logger.debug(f"找到更好的匹配: {template_ch.title} -> {target_ch.title}, 相似度: {overall_score:.2f}")
                
                # 创建映射
                if best_target:
                    mapping = create_mapping(
                        template_ch, best_target, best_match_type, best_scores,
                        best_reasoning, f"层级{template_ch.level}最优匹配"
                    )
                    mappings.append(mapping)
                    
                    # 立即将目标章节标记为已使用，防止重复映射
                    used_targets.add(best_target_idx)
                    logger.debug(f"标记目标章节为已使用: {best_target.title} (索引: {best_target_idx})")
                    
                    # 更新上下文
                    context.sibling_mappings.append(mapping)
                else:
                    # 未找到匹配，创建空映射
                    empty_mapping = create_empty_mapping(template_ch)
                    mappings.append(empty_mapping)
            
        except Exception as e:
            logger.warning(f"层级映射失败: {e}")
        
        return mappings
    
    def _determine_match_type(self, scores: SimilarityScores) -> MatchType:
        """根据相似度分数确定匹配类型"""
        if scores.overall_similarity >= self.config.exact_match_threshold:
            return MatchType.EXACT
        elif scores.title_similarity >= 0.8:
            return MatchType.SIMILAR
        elif scores.overall_similarity >= self.config.semantic_match_threshold:
            return MatchType.SEMANTIC
        elif scores.position_similarity >= 0.7:
            return MatchType.POSITIONAL
        else:
            return MatchType.NONE
    
    def _analyze_unmapped_chapters(self, template_chapters: List[ChapterInfo],
                                 target_chapters: List[ChapterInfo],
                                 mappings: List[ChapterMapping]) -> Tuple[List[ChapterInfo], List[ChapterInfo]]:
        """分析未映射的章节"""
        # 找出未映射的模板章节
        mapped_template_ids = [id(m.template_chapter) for m in mappings if m.target_chapter]
        unmapped_template = [ch for ch in template_chapters if id(ch) not in mapped_template_ids]
        
        # 找出未映射的目标章节
        mapped_target_ids = [id(m.target_chapter) for m in mappings if m.target_chapter]
        unmapped_target = [ch for ch in target_chapters if id(ch) not in mapped_target_ids]
        
        return unmapped_template, unmapped_target
    
    def _calculate_overall_confidence(self, mappings: List[ChapterMapping]) -> float:
        """计算整体映射置信度"""
        if not mappings:
            return 0.0
        
        total_confidence = sum(m.confidence for m in mappings)
        return total_confidence / len(mappings)
    
    def _generate_mapping_summary(self, mappings: List[ChapterMapping]) -> Dict[str, int]:
        """生成映射统计摘要"""
        summary = {
            'total': len(mappings),
            'exact': 0,
            'similar': 0,
            'semantic': 0,
            'positional': 0,
            'none': 0
        }
        
        for mapping in mappings:
            match_type = mapping.match_type.value
            if match_type in summary:
                summary[match_type] += 1
        
        return summary
    
    def enhance_mapping_with_context(self, mappings: List[ChapterMapping],
                                   context: MatchingContext) -> List[ChapterMapping]:
        """
        使用上下文信息增强映射结果
        
        Args:
            mappings: 初始映射结果
            context: 匹配上下文
            
        Returns:
            增强后的映射结果
        """
        if not self.config.enable_context_aware:
            return mappings
        
        try:
            enhanced_mappings = []
            
            for mapping in mappings:
                if mapping.match_type == MatchType.NONE and mapping.target_chapter is None:
                    # 对于未匹配的章节，尝试上下文感知匹配
                    enhanced_mapping = self._enhance_unmapped_chapter(mapping, context)
                    enhanced_mappings.append(enhanced_mapping)
                else:
                    enhanced_mappings.append(mapping)
            
            return enhanced_mappings
            
        except Exception as e:
            logger.warning(f"上下文增强失败: {e}")
            return mappings
    
    def _enhance_unmapped_chapter(self, mapping: ChapterMapping,
                                context: MatchingContext) -> ChapterMapping:
        """使用上下文增强未映射的章节"""
        try:
            template_chapter = mapping.template_chapter
            
            # 获取候选目标章节（同层级或相近层级）
            candidates = []
            for target_ch in context.target_chapters:
                if abs(target_ch.level - template_chapter.level) <= 1:
                    candidates.append(target_ch)
            
            if not candidates:
                return mapping
            
            # 使用上下文感知匹配
            best_chapter, best_score, best_reasoning = self.semantic_matcher.context_aware_match(
                template_chapter, candidates, context
            )
            
            if best_chapter and best_score >= self.config.similarity_threshold:
                # 创建新的映射
                scores = SimilarityScores()
                scores.overall_similarity = best_score
                
                enhanced_mapping = create_mapping(
                    template_chapter, best_chapter, MatchType.SEMANTIC, scores,
                    best_reasoning, "上下文感知匹配"
                )
                
                return enhanced_mapping
            
        except Exception as e:
            logger.warning(f"章节上下文增强失败: {e}")
        
        return mapping
    
    def get_mapping_statistics(self, result: MappingResult) -> Dict[str, any]:
        """获取映射统计信息"""
        try:
            stats = {
                'total_template_chapters': len(result.mappings),
                'total_target_chapters': len(result.mappings) + len(result.unmapped_target),
                'successful_mappings': len([m for m in result.mappings if m.target_chapter]),
                'failed_mappings': len([m for m in result.mappings if not m.target_chapter]),
                'mapping_rate': 0.0,
                'confidence_distribution': {},
                'match_type_distribution': result.mapping_summary,
                'renumbering_patterns_count': len(result.renumbering_patterns),
                'performance_metrics': result.performance_metrics
            }
            
            # 计算映射成功率
            if stats['total_template_chapters'] > 0:
                stats['mapping_rate'] = stats['successful_mappings'] / stats['total_template_chapters']
            
            # 置信度分布
            confidence_ranges = {'high': 0, 'medium': 0, 'low': 0}
            for mapping in result.mappings:
                if mapping.confidence >= 0.8:
                    confidence_ranges['high'] += 1
                elif mapping.confidence >= 0.5:
                    confidence_ranges['medium'] += 1
                else:
                    confidence_ranges['low'] += 1
            
            stats['confidence_distribution'] = confidence_ranges
            
            return stats
            
        except Exception as e:
            logger.error(f"统计信息生成失败: {e}")
            return {}
