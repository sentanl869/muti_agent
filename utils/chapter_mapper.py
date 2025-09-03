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
    MatchingContext, BatchSemanticRequest, create_mapping, create_empty_mapping,
    RenumberingPatternType
)
from utils.semantic_matcher import SemanticMatcher
from utils.renumbering_detector import RenumberingDetector
from config.config import config

logger = logging.getLogger(__name__)


@dataclass
class MappingConfig:
    """映射配置"""
    similarity_threshold: float = 0.5      # 相似度阈值
    exact_match_threshold: float = 0.95    # 精确匹配阈值
    semantic_match_threshold: float = 0.7  # 语义匹配阈值
    position_weight: float = 0.2           # 位置权重
    title_weight: float = 0.5              # 标题权重
    content_weight: float = 0.2            # 内容权重
    structure_weight: float = 0.1          # 结构权重
    max_batch_size: int = 30               # 批量处理大小
    enable_context_aware: bool = True      # 启用上下文感知
    enable_renumbering_detection: bool = True  # 启用重编号检测


class ChapterMapper:
    """章节映射器"""
    
    def __init__(self, mapping_config: MappingConfig = None):
        # 优先使用传入的配置，其次使用全局配置，最后使用默认配置
        self.config = mapping_config or config.mapping
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
            
            # 5. 使用上下文信息增强映射结果
            enhanced_mappings = self.enhance_mapping_with_context(mappings, context)
            
            # 6. 分析映射结果
            unmapped_template, unmapped_target = self._analyze_unmapped_chapters(
                template_chapters, target_chapters, enhanced_mappings
            )
            
            # 7. 计算整体置信度
            overall_confidence = self._calculate_overall_confidence(enhanced_mappings)
            
            # 8. 生成映射摘要
            mapping_summary = self._generate_mapping_summary(enhanced_mappings)
            
            # 9. 性能指标
            processing_time = time.time() - start_time
            performance_metrics = {
                'processing_time': processing_time,
                'api_calls': self.semantic_matcher.get_api_call_stats()['total_api_calls'],
                'similarity_calculations': len(template_chapters) * len(target_chapters)
            }
            
            result = MappingResult(
                mappings=enhanced_mappings,
                unmapped_template=unmapped_template,
                unmapped_target=unmapped_target,
                renumbering_patterns=renumbering_patterns,
                overall_confidence=overall_confidence,
                mapping_summary=mapping_summary,
                performance_metrics=performance_metrics
            )
            
            logger.info(f"全局映射完成: 耗时{processing_time:.2f}s, "
                       f"成功映射{len(enhanced_mappings)}个, 整体置信度{overall_confidence:.2%}")
            
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
                    
                    # 语义相似度（从批量结果中获取，如果可用的话）
                    semantic_similarity = 0.0
                    if i < len(semantic_matrix) and j < len(semantic_matrix[i]):
                        semantic_similarity = semantic_matrix[i][j]
                    
                    # 计算综合相似度：结合语义相似度和其他相似度
                    # 如果有语义相似度，则使用加权平均；否则仅使用其他相似度

                    # 根据重编号模式动态调整权重
                    weights = self._adjust_weights_based_on_patterns(
                        template_ch, target_ch, context
                    )

                    base_similarity = (
                        scores.title_similarity * weights['title'] +
                        scores.content_similarity * weights['content'] +
                        scores.position_similarity * weights['position'] +
                        scores.structure_similarity * weights['structure']
                    )
                    
                    # 智能权重融合：根据语义相似度高低调整权重
                    if semantic_similarity > 0:
                        # 对于高分语义匹配（可能是泛化标题），大幅提高语义权重
                        if semantic_similarity >= 0.85:
                            # 泛化标题或高置信度语义匹配：语义权重80%，基础权重20%
                            scores.overall_similarity = base_similarity * 0.2 + semantic_similarity * 0.8
                        elif semantic_similarity >= 0.7:
                            # 中高置信度语义匹配：语义权重60%，基础权重40%
                            scores.overall_similarity = base_similarity * 0.4 + semantic_similarity * 0.6
                        else:
                            # 一般语义匹配：语义权重40%，基础权重60%
                            scores.overall_similarity = base_similarity * 0.6 + semantic_similarity * 0.4
                    else:
                        scores.overall_similarity = base_similarity
            
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
                
                # 首先在同层级的目标章节中寻找最佳匹配
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
                
                # 如果同层级没有找到匹配，尝试跨层级匹配
                if not best_target:
                    cross_level_candidates = self._find_cross_level_candidates(
                        template_ch, all_target, used_targets
                    )
                    
                    for target_ch in cross_level_candidates:
                        target_idx = all_target.index(target_ch)
                        
                        # 获取相似度分数
                        if template_idx < len(similarity_matrix) and target_idx < len(similarity_matrix[template_idx]):
                            scores = similarity_matrix[template_idx][target_idx]
                            overall_score = scores.overall_similarity
                            
                            # 跨层级匹配需要更高的阈值
                            cross_level_threshold = self.config.semantic_match_threshold
                            
                            if overall_score > best_score and overall_score >= cross_level_threshold:
                                match_type = MatchType.SEMANTIC  # 跨层级匹配标记为语义匹配
                                best_target = target_ch
                                best_target_idx = target_idx
                                best_score = overall_score
                                best_match_type = match_type
                                best_scores = scores
                                best_reasoning = f"跨层级匹配 - 相似度: {overall_score:.2f}, 层级: H{template_ch.level}->H{target_ch.level}"
                                logger.debug(f"找到跨层级匹配: {template_ch.title} -> {target_ch.title}, 相似度: {overall_score:.2f}")
                
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
                    # 未找到匹配，创建空映射（表示缺失章节）
                    empty_mapping = create_empty_mapping(template_ch)
                    mappings.append(empty_mapping)
                    logger.info(f"章节缺失: {template_ch.title} (层级: H{template_ch.level})")
        
        except Exception as e:
            logger.warning(f"层级映射失败: {e}")
        
        return mappings
    
    def _find_cross_level_candidates(self, template_ch: ChapterInfo, 
                                   all_target: List[ChapterInfo],
                                   used_targets: Set[int]) -> List[ChapterInfo]:
        """
        在相邻层级中寻找候选匹配章节
        
        Args:
            template_ch: 模板章节
            all_target: 所有目标章节
            used_targets: 已使用的目标章节索引
            
        Returns:
            候选章节列表
        """
        candidates = []
        target_level = template_ch.level
        
        try:
            # 检查相邻层级（±1），优先考虑相近层级
            level_priorities = [target_level - 1, target_level + 1]
            
            for priority_level in level_priorities:
                for target_ch in all_target:
                    target_idx = all_target.index(target_ch)
                    
                    # 跳过已使用的目标章节
                    if target_idx in used_targets:
                        continue
                    
                    # 匹配相邻层级
                    if target_ch.level == priority_level:
                        candidates.append(target_ch)
                        logger.debug(f"添加跨层级候选: {template_ch.title} (H{target_level}) -> {target_ch.title} (H{priority_level})")
            
            # 如果相邻层级没有候选，扩大搜索范围到±2层级
            if not candidates:
                extended_levels = [target_level - 2, target_level + 2]
                for extended_level in extended_levels:
                    if extended_level > 0:  # 确保层级有效
                        for target_ch in all_target:
                            target_idx = all_target.index(target_ch)
                            
                            if target_idx not in used_targets and target_ch.level == extended_level:
                                candidates.append(target_ch)
                                logger.debug(f"添加扩展层级候选: {template_ch.title} (H{target_level}) -> {target_ch.title} (H{extended_level})")
            
        except Exception as e:
            logger.warning(f"跨层级候选查找失败: {e}")
        
        return candidates
    
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
        # 找出未映射的模板章节 - 修正：所有在mappings中的模板章节都应该被认为是已处理的
        # 不管是否有target_chapter，只要存在映射关系就表示已经处理过了
        mapped_template_ids = [id(m.template_chapter) for m in mappings]
        unmapped_template = [ch for ch in template_chapters if id(ch) not in mapped_template_ids]
        
        # 找出未映射的目标章节 - 只有实际被映射到的目标章节才算已使用
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
    
    def _adjust_weights_based_on_patterns(self, template_ch: ChapterInfo,
                                        target_ch: ChapterInfo,
                                        context: MatchingContext) -> Dict[str, float]:
        """
        根据重编号模式动态调整相似度权重

        Args:
            template_ch: 模板章节
            target_ch: 目标章节
            context: 匹配上下文

        Returns:
            调整后的权重字典
        """
        try:
            # 基础权重
            weights = {
                'title': self.config.title_weight,
                'content': self.config.content_weight,
                'position': self.config.position_weight,
                'structure': self.config.structure_weight
            }

            # 检查是否有影响当前章节的重编号模式
            has_relevant_patterns = False

            logger.info(f"检查章节 {template_ch.title} (层级: H{template_ch.level}) 的权重调整")
            logger.info(f"当前上下文中的重编号模式数量: {len(context.global_patterns)}")

            for pattern in context.global_patterns:
                logger.info(f"检查模式: {pattern.pattern_type.value}, 影响层级: {pattern.affected_levels}")
                # 检查模式是否影响当前章节的层级
                if template_ch.level in pattern.affected_levels:
                    has_relevant_patterns = True
                    logger.info(f"模式 {pattern.pattern_type.value} 影响当前章节层级 H{template_ch.level}")

                    # 根据模式类型调整权重
                    if pattern.pattern_type in [RenumberingPatternType.DELETION, RenumberingPatternType.INSERTION]:
                        # 删除或插入模式：大幅降低位置权重，提高标题和内容权重
                        weights['position'] = max(0.02, weights['position'] * 0.2)  # 降低到20%或最小0.02
                        weights['title'] = min(0.8, weights['title'] * 1.5)        # 提高到150%或最大0.8
                        weights['content'] = min(0.4, weights['content'] * 1.5)    # 提高到150%或最大0.4
                        logger.info(f"检测到{pattern.pattern_type.value}模式，调整权重: 位置{weights['position']:.2f}, 标题{weights['title']:.2f}, 内容{weights['content']:.2f}")

                    elif pattern.pattern_type == RenumberingPatternType.OFFSET:
                        # 偏移模式：适度降低位置权重
                        weights['position'] = max(0.1, weights['position'] * 0.7)  # 降低到70%或最小0.1
                        weights['title'] = min(0.65, weights['title'] * 1.1)      # 适度提高标题权重
                        logger.info(f"检测到偏移模式，调整权重: 位置{weights['position']:.2f}, 标题{weights['title']:.2f}")

                    elif pattern.pattern_type == RenumberingPatternType.REORDER:
                        # 重排序模式：显著降低位置权重
                        weights['position'] = max(0.05, weights['position'] * 0.3)  # 降低到30%或最小0.05
                        weights['title'] = min(0.7, weights['title'] * 1.3)        # 显著提高标题权重
                        logger.info(f"检测到重排序模式，调整权重: 位置{weights['position']:.2f}, 标题{weights['title']:.2f}")

            if not has_relevant_patterns:
                logger.info(f"章节 {template_ch.title} 没有相关的重编号模式，使用默认权重")

            # 归一化权重，确保总和为1
            total_weight = sum(weights.values())
            if total_weight > 0:
                for key in weights:
                    weights[key] = weights[key] / total_weight

            return weights

        except Exception as e:
            logger.warning(f"权重调整失败: {e}")
            # 返回默认权重
            return {
                'title': self.config.title_weight,
                'content': self.config.content_weight,
                'position': self.config.position_weight,
                'structure': self.config.structure_weight
            }

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
