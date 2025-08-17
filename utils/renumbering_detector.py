"""
章节重编号检测器
识别章节编号模式变化，如偏移、重排序等
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter

from utils.html_parser import ChapterInfo
from utils.chapter_mapping_types import (
    RenumberingPattern, RenumberingPatternType
)

logger = logging.getLogger(__name__)


class RenumberingDetector:
    """章节重编号检测器"""
    
    def __init__(self):
        self.number_pattern = re.compile(r'(\d+(?:\.\d+)*)')
        
    def detect_patterns(self, template_chapters: List[ChapterInfo], 
                       target_chapters: List[ChapterInfo]) -> List[RenumberingPattern]:
        """
        检测重编号模式
        
        Args:
            template_chapters: 模板章节列表
            target_chapters: 目标章节列表
            
        Returns:
            检测到的重编号模式列表
        """
        patterns = []
        
        try:
            # 按层级分组检测
            template_by_level = self._group_by_level(template_chapters)
            target_by_level = self._group_by_level(target_chapters)
            
            for level in sorted(set(template_by_level.keys()) | set(target_by_level.keys())):
                template_level_chapters = template_by_level.get(level, [])
                target_level_chapters = target_by_level.get(level, [])
                
                if template_level_chapters and target_level_chapters:
                    level_patterns = self._detect_level_patterns(
                        template_level_chapters, target_level_chapters, level
                    )
                    patterns.extend(level_patterns)
            
            # 检测全局模式
            global_patterns = self._detect_global_patterns(template_chapters, target_chapters)
            patterns.extend(global_patterns)
            
            # 合并和优化模式
            patterns = self._merge_patterns(patterns)
            
            logger.info(f"检测到 {len(patterns)} 个重编号模式")
            for pattern in patterns:
                logger.debug(f"模式: {pattern.pattern_type.value}, 置信度: {pattern.confidence:.2f}, "
                           f"描述: {pattern.description}")
            
            return patterns
            
        except Exception as e:
            logger.error(f"重编号模式检测失败: {e}")
            return []
    
    def _group_by_level(self, chapters: List[ChapterInfo]) -> Dict[int, List[ChapterInfo]]:
        """按层级分组章节"""
        groups = defaultdict(list)
        for chapter in chapters:
            groups[chapter.level].append(chapter)
        return dict(groups)
    
    def _detect_level_patterns(self, template_chapters: List[ChapterInfo], 
                             target_chapters: List[ChapterInfo], 
                             level: int) -> List[RenumberingPattern]:
        """检测特定层级的重编号模式"""
        patterns = []
        
        try:
            # 提取编号
            template_numbers = [self._extract_number_sequence(ch.title) for ch in template_chapters]
            target_numbers = [self._extract_number_sequence(ch.title) for ch in target_chapters]
            
            # 过滤无效编号
            template_valid = [(i, num) for i, num in enumerate(template_numbers) if num]
            target_valid = [(i, num) for i, num in enumerate(target_numbers) if num]
            
            if len(template_valid) < 2 or len(target_valid) < 2:
                return patterns
            
            # 检测偏移模式
            offset_pattern = self._detect_offset_pattern(template_valid, target_valid, level)
            if offset_pattern:
                patterns.append(offset_pattern)
            
            # 检测重排序模式
            reorder_pattern = self._detect_reorder_pattern(template_valid, target_valid, level)
            if reorder_pattern:
                patterns.append(reorder_pattern)
            
            # 检测插入/删除模式
            insertion_pattern = self._detect_insertion_pattern(template_valid, target_valid, level)
            if insertion_pattern:
                patterns.append(insertion_pattern)
            
            deletion_pattern = self._detect_deletion_pattern(template_valid, target_valid, level)
            if deletion_pattern:
                patterns.append(deletion_pattern)
            
        except Exception as e:
            logger.warning(f"层级 {level} 模式检测失败: {e}")
        
        return patterns
    
    def _extract_number_sequence(self, title: str) -> Optional[List[int]]:
        """从标题中提取数字序列"""
        try:
            match = self.number_pattern.search(title)
            if match:
                number_str = match.group(1)
                return [int(x) for x in number_str.split('.')]
            return None
        except Exception as e:
            logger.warning(f"数字序列提取失败: {e}")
            return None
    
    def _detect_offset_pattern(self, template_valid: List[Tuple[int, List[int]]], 
                             target_valid: List[Tuple[int, List[int]]], 
                             level: int) -> Optional[RenumberingPattern]:
        """检测偏移模式"""
        try:
            if len(template_valid) < 2 or len(target_valid) < 2:
                return None
            
            # 计算可能的偏移量
            offsets = []
            examples = []
            
            for t_idx, t_num in template_valid:
                for g_idx, g_num in target_valid:
                    if len(t_num) == len(g_num):
                        # 计算最后一级的偏移
                        offset = g_num[-1] - t_num[-1]
                        offsets.append(offset)
                        examples.append((
                            '.'.join(map(str, t_num)),
                            '.'.join(map(str, g_num))
                        ))
            
            if not offsets:
                return None
            
            # 统计最常见的偏移量
            offset_counter = Counter(offsets)
            most_common_offset, count = offset_counter.most_common(1)[0]
            
            # 计算置信度
            confidence = count / len(offsets)
            
            if confidence >= 0.6 and abs(most_common_offset) > 0:  # 至少60%的章节有相同偏移
                # 选择代表性示例
                representative_examples = []
                for i, (t_str, g_str) in enumerate(examples):
                    if offsets[i] == most_common_offset:
                        representative_examples.append((t_str, g_str))
                        if len(representative_examples) >= 3:
                            break
                
                description = f"H{level} 章节编号整体偏移 {most_common_offset:+d}"
                
                return RenumberingPattern(
                    pattern_type=RenumberingPatternType.OFFSET,
                    offset_value=most_common_offset,
                    affected_levels=[level],
                    confidence=confidence,
                    examples=representative_examples,
                    description=description
                )
            
        except Exception as e:
            logger.warning(f"偏移模式检测失败: {e}")
        
        return None
    
    def _detect_reorder_pattern(self, template_valid: List[Tuple[int, List[int]]], 
                              target_valid: List[Tuple[int, List[int]]], 
                              level: int) -> Optional[RenumberingPattern]:
        """检测重排序模式"""
        try:
            if len(template_valid) < 3 or len(target_valid) < 3:
                return None
            
            # 提取编号序列
            template_sequence = [num[-1] for _, num in template_valid]
            target_sequence = [num[-1] for _, num in target_valid]
            
            # 检查是否为重排序（相同元素，不同顺序）
            if sorted(template_sequence) == sorted(target_sequence) and template_sequence != target_sequence:
                # 计算位置变化
                position_changes = 0
                examples = []
                
                for i, t_num in enumerate(template_sequence):
                    if i < len(target_sequence) and t_num != target_sequence[i]:
                        position_changes += 1
                        if len(examples) < 3:
                            examples.append((
                                str(t_num),
                                str(target_sequence[i])
                            ))
                
                confidence = 1.0 - (position_changes / len(template_sequence))
                
                if confidence >= 0.3:  # 至少70%的章节位置发生变化
                    description = f"H{level} 章节顺序重新排列"
                    
                    return RenumberingPattern(
                        pattern_type=RenumberingPatternType.REORDER,
                        affected_levels=[level],
                        confidence=confidence,
                        examples=examples,
                        description=description
                    )
            
        except Exception as e:
            logger.warning(f"重排序模式检测失败: {e}")
        
        return None
    
    def _detect_insertion_pattern(self, template_valid: List[Tuple[int, List[int]]], 
                                target_valid: List[Tuple[int, List[int]]], 
                                level: int) -> Optional[RenumberingPattern]:
        """检测插入模式"""
        try:
            if len(target_valid) <= len(template_valid):
                return None
            
            template_numbers = set(tuple(num) for _, num in template_valid)
            target_numbers = set(tuple(num) for _, num in target_valid)
            
            # 检查是否有新增的章节
            new_numbers = target_numbers - template_numbers
            
            if new_numbers:
                confidence = len(new_numbers) / len(target_numbers)
                
                if confidence >= 0.1:  # 至少10%的章节是新增的
                    examples = []
                    for new_num in list(new_numbers)[:3]:
                        examples.append(("", '.'.join(map(str, new_num))))
                    
                    description = f"H{level} 插入了 {len(new_numbers)} 个新章节"
                    
                    return RenumberingPattern(
                        pattern_type=RenumberingPatternType.INSERTION,
                        affected_levels=[level],
                        confidence=confidence,
                        examples=examples,
                        description=description
                    )
            
        except Exception as e:
            logger.warning(f"插入模式检测失败: {e}")
        
        return None
    
    def _detect_deletion_pattern(self, template_valid: List[Tuple[int, List[int]]], 
                               target_valid: List[Tuple[int, List[int]]], 
                               level: int) -> Optional[RenumberingPattern]:
        """检测删除模式"""
        try:
            if len(template_valid) <= len(target_valid):
                return None
            
            template_numbers = set(tuple(num) for _, num in template_valid)
            target_numbers = set(tuple(num) for _, num in target_valid)
            
            # 检查是否有删除的章节
            deleted_numbers = template_numbers - target_numbers
            
            if deleted_numbers:
                confidence = len(deleted_numbers) / len(template_numbers)
                
                if confidence >= 0.1:  # 至少10%的章节被删除
                    examples = []
                    for deleted_num in list(deleted_numbers)[:3]:
                        examples.append(('.'.join(map(str, deleted_num)), ""))
                    
                    description = f"H{level} 删除了 {len(deleted_numbers)} 个章节"
                    
                    return RenumberingPattern(
                        pattern_type=RenumberingPatternType.DELETION,
                        affected_levels=[level],
                        confidence=confidence,
                        examples=examples,
                        description=description
                    )
            
        except Exception as e:
            logger.warning(f"删除模式检测失败: {e}")
        
        return None
    
    def _detect_global_patterns(self, template_chapters: List[ChapterInfo], 
                              target_chapters: List[ChapterInfo]) -> List[RenumberingPattern]:
        """检测全局重编号模式"""
        patterns = []
        
        try:
            # 检测混合模式（多种模式同时存在）
            level_patterns_count = defaultdict(int)
            
            # 简单统计不同层级的模式数量
            template_by_level = self._group_by_level(template_chapters)
            target_by_level = self._group_by_level(target_chapters)
            
            pattern_types = set()
            affected_levels = []
            
            for level in template_by_level.keys():
                if level in target_by_level:
                    template_count = len(template_by_level[level])
                    target_count = len(target_by_level[level])
                    
                    if template_count != target_count:
                        if target_count > template_count:
                            pattern_types.add(RenumberingPatternType.INSERTION)
                        else:
                            pattern_types.add(RenumberingPatternType.DELETION)
                        affected_levels.append(level)
            
            # 如果检测到多种模式，创建混合模式
            if len(pattern_types) > 1:
                confidence = 0.7  # 混合模式的默认置信度
                description = f"检测到混合重编号模式，影响层级: {affected_levels}"
                
                patterns.append(RenumberingPattern(
                    pattern_type=RenumberingPatternType.MIXED,
                    affected_levels=affected_levels,
                    confidence=confidence,
                    description=description
                ))
            
        except Exception as e:
            logger.warning(f"全局模式检测失败: {e}")
        
        return patterns
    
    def _merge_patterns(self, patterns: List[RenumberingPattern]) -> List[RenumberingPattern]:
        """合并和优化重编号模式"""
        if not patterns:
            return patterns
        
        try:
            # 按类型分组
            patterns_by_type = defaultdict(list)
            for pattern in patterns:
                patterns_by_type[pattern.pattern_type].append(pattern)
            
            merged_patterns = []
            
            for pattern_type, type_patterns in patterns_by_type.items():
                if len(type_patterns) == 1:
                    merged_patterns.append(type_patterns[0])
                else:
                    # 合并相同类型的模式
                    merged_pattern = self._merge_same_type_patterns(type_patterns)
                    if merged_pattern:
                        merged_patterns.append(merged_pattern)
            
            # 按置信度排序
            merged_patterns.sort(key=lambda p: p.confidence, reverse=True)
            
            return merged_patterns
            
        except Exception as e:
            logger.warning(f"模式合并失败: {e}")
            return patterns
    
    def _merge_same_type_patterns(self, patterns: List[RenumberingPattern]) -> Optional[RenumberingPattern]:
        """合并相同类型的模式"""
        try:
            if not patterns:
                return None
            
            if len(patterns) == 1:
                return patterns[0]
            
            # 合并基本信息
            pattern_type = patterns[0].pattern_type
            affected_levels = []
            all_examples = []
            descriptions = []
            
            total_confidence = 0.0
            
            for pattern in patterns:
                affected_levels.extend(pattern.affected_levels)
                all_examples.extend(pattern.examples)
                if pattern.description:
                    descriptions.append(pattern.description)
                total_confidence += pattern.confidence
            
            # 去重和限制
            affected_levels = sorted(list(set(affected_levels)))
            all_examples = all_examples[:5]  # 最多保留5个示例
            avg_confidence = total_confidence / len(patterns)
            
            merged_description = "; ".join(descriptions) if descriptions else ""
            
            return RenumberingPattern(
                pattern_type=pattern_type,
                affected_levels=affected_levels,
                confidence=avg_confidence,
                examples=all_examples,
                description=merged_description
            )
            
        except Exception as e:
            logger.warning(f"相同类型模式合并失败: {e}")
            return patterns[0] if patterns else None
    
    def analyze_numbering_shift(self, template_chapters: List[ChapterInfo], 
                              target_chapters: List[ChapterInfo]) -> Dict[str, any]:
        """
        分析编号偏移情况
        
        Args:
            template_chapters: 模板章节
            target_chapters: 目标章节
            
        Returns:
            编号偏移分析结果
        """
        try:
            analysis = {
                'has_shift': False,
                'shift_patterns': [],
                'affected_levels': [],
                'confidence': 0.0,
                'summary': ""
            }
            
            patterns = self.detect_patterns(template_chapters, target_chapters)
            
            if patterns:
                analysis['has_shift'] = True
                analysis['shift_patterns'] = patterns
                analysis['affected_levels'] = list(set(
                    level for pattern in patterns for level in pattern.affected_levels
                ))
                analysis['confidence'] = max(pattern.confidence for pattern in patterns)
                
                # 生成摘要
                pattern_descriptions = [pattern.description for pattern in patterns if pattern.description]
                analysis['summary'] = "; ".join(pattern_descriptions)
            
            return analysis
            
        except Exception as e:
            logger.error(f"编号偏移分析失败: {e}")
            return {
                'has_shift': False,
                'shift_patterns': [],
                'affected_levels': [],
                'confidence': 0.0,
                'summary': "分析失败"
            }
    
    def validate_pattern(self, pattern: RenumberingPattern, 
                        template_chapters: List[ChapterInfo], 
                        target_chapters: List[ChapterInfo]) -> bool:
        """
        验证重编号模式的有效性
        
        Args:
            pattern: 要验证的模式
            template_chapters: 模板章节
            target_chapters: 目标章节
            
        Returns:
            模式是否有效
        """
        try:
            # 基本验证
            if pattern.confidence < 0.3:
                return False
            
            if not pattern.affected_levels:
                return False
            
            # 根据模式类型进行特定验证
            if pattern.pattern_type == RenumberingPatternType.OFFSET:
                return self._validate_offset_pattern(pattern, template_chapters, target_chapters)
            elif pattern.pattern_type == RenumberingPatternType.REORDER:
                return self._validate_reorder_pattern(pattern, template_chapters, target_chapters)
            elif pattern.pattern_type in [RenumberingPatternType.INSERTION, RenumberingPatternType.DELETION]:
                return self._validate_insertion_deletion_pattern(pattern, template_chapters, target_chapters)
            
            return True
            
        except Exception as e:
            logger.warning(f"模式验证失败: {e}")
            return False
    
    def _validate_offset_pattern(self, pattern: RenumberingPattern, 
                               template_chapters: List[ChapterInfo], 
                               target_chapters: List[ChapterInfo]) -> bool:
        """验证偏移模式"""
        try:
            if pattern.offset_value == 0:
                return False
            
            # 检查示例的一致性
            if len(pattern.examples) < 2:
                return False
            
            for template_num_str, target_num_str in pattern.examples:
                if not template_num_str or not target_num_str:
                    continue
                
                try:
                    template_parts = [int(x) for x in template_num_str.split('.')]
                    target_parts = [int(x) for x in target_num_str.split('.')]
                    
                    if len(template_parts) != len(target_parts):
                        continue
                    
                    actual_offset = target_parts[-1] - template_parts[-1]
                    if actual_offset != pattern.offset_value:
                        return False
                        
                except ValueError:
                    continue
            
            return True
            
        except Exception as e:
            logger.warning(f"偏移模式验证失败: {e}")
            return False
    
    def _validate_reorder_pattern(self, pattern: RenumberingPattern, 
                                template_chapters: List[ChapterInfo], 
                                target_chapters: List[ChapterInfo]) -> bool:
        """验证重排序模式"""
        # 重排序模式的验证相对简单，主要检查置信度
        return pattern.confidence >= 0.3
    
    def _validate_insertion_deletion_pattern(self, pattern: RenumberingPattern, 
                                           template_chapters: List[ChapterInfo], 
                                           target_chapters: List[ChapterInfo]) -> bool:
        """验证插入/删除模式"""
        try:
            template_count = len([ch for ch in template_chapters if ch.level in pattern.affected_levels])
            target_count = len([ch for ch in target_chapters if ch.level in pattern.affected_levels])
            
            if pattern.pattern_type == RenumberingPatternType.INSERTION:
                return target_count > template_count
            elif pattern.pattern_type == RenumberingPatternType.DELETION:
                return template_count > target_count
            
            return True
            
        except Exception as e:
            logger.warning(f"插入/删除模式验证失败: {e}")
            return False
