"""
章节完整性检查 Agent
负责检查目标文档的章节结构是否完整
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from utils.html_parser import ChapterInfo
from utils.llm_client import LLMClient
from config.config import config
from prompts import PromptBuilder
from utils.chapter_mapper import ChapterMapper, MappingConfig
from utils.chapter_mapping_types import MatchType, MappingResult

logger = logging.getLogger(__name__)


@dataclass
class StructureNode:
    """章节结构节点"""
    title: str
    level: int
    children: List['StructureNode']
    path: str = ""
    position: int = 0


@dataclass
class MissingChapter:
    """缺失章节信息"""
    title: str
    level: int
    expected_path: str
    parent_title: str = ""
    position: int = 0


@dataclass
class StructureCheckResult:
    """结构检查结果"""
    passed: bool
    missing_chapters: List[MissingChapter]
    extra_chapters: List[ChapterInfo]
    structure_issues: List[str]
    template_structure: StructureNode
    target_structure: StructureNode
    similarity_score: float = 0.0


class StructureChecker:
    """章节完整性检查 Agent"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.chapter_mapper = ChapterMapper()
        self.enable_smart_mapping = config.structure_check.enable_smart_mapping  # 从配置获取
    
    def check_structure_completeness(self, template_chapters: List[ChapterInfo], 
                                   target_chapters: List[ChapterInfo]) -> StructureCheckResult:
        """
        检查章节结构完整性
        
        Args:
            template_chapters: 模板文档章节
            target_chapters: 目标文档章节
            
        Returns:
            结构检查结果
        """
        try:
            logger.info("开始章节完整性检查")
            
            # 构建章节结构树
            template_structure = self._build_structure_tree(template_chapters)
            target_structure = self._build_structure_tree(target_chapters)
            
            # 使用智能映射或传统方法进行比较
            if self.enable_smart_mapping:
                missing_chapters, extra_chapters, similarity_score = self._smart_structure_comparison(
                    template_chapters, target_chapters
                )
            else:
                # 传统方法
                missing_chapters = self._find_missing_chapters(template_structure, target_structure)
                extra_chapters = self._find_extra_chapters(template_structure, target_structure, target_chapters)
                similarity_score = self._calculate_similarity(template_structure, target_structure)
            
            # 分析结构问题
            structure_issues = self._analyze_structure_issues(template_structure, target_structure)
            
            # 关键章节检查
            missing_critical_chapters = self._check_critical_chapters(target_chapters)
            
            # 将缺失的关键章节添加到结构问题中
            for missing_critical in missing_critical_chapters:
                structure_issues.append(f"缺失关键章节: {missing_critical}")
            
            # 判断是否通过 - 使用配置的缺失章节阈值
            passed = len(missing_chapters) <= config.structure_check.missing_chapters_threshold and len(structure_issues) == 0
            
            result = StructureCheckResult(
                passed=passed,
                missing_chapters=missing_chapters,
                extra_chapters=extra_chapters,
                structure_issues=structure_issues,
                template_structure=template_structure,
                target_structure=target_structure,
                similarity_score=similarity_score
            )
            
            logger.info(f"章节完整性检查完成: {'通过' if passed else '失败'}")
            logger.info(f"缺失章节: {len(missing_chapters)}, 额外章节: {len(extra_chapters)}")
            if len(missing_chapters) > 0:
                threshold = config.structure_check.missing_chapters_threshold
                logger.info(f"缺失章节阈值检查: {len(missing_chapters)}/{threshold} {'(通过)' if len(missing_chapters) <= threshold else '(失败)'}")
            logger.info(f"结构问题: {len(structure_issues)}")
            if missing_critical_chapters:
                logger.warning(f"缺失关键章节: {missing_critical_chapters}")
            logger.info(f"结构相似度: {similarity_score:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"章节完整性检查失败: {e}")
            raise
    
    def _build_structure_tree(self, chapters: List[ChapterInfo]) -> StructureNode:
        """构建章节结构树"""
        if not chapters:
            return StructureNode("根节点", 0, [])
        
        root = StructureNode("根节点", 0, [])
        stack = [root]  # 用于跟踪当前路径
        
        for i, chapter in enumerate(chapters):
            # 找到合适的父节点
            while len(stack) > 1 and stack[-1].level >= chapter.level:
                stack.pop()
            
            parent = stack[-1]
            
            # 构建路径
            path_parts = []
            for stack_node in stack[1:]:  # 跳过根节点
                path_parts.append(stack_node.title)
            path = " > ".join(path_parts)
            
            # 创建新节点
            node = StructureNode(
                title=chapter.title,
                level=chapter.level,
                children=[],
                path=path,
                position=i
            )
            
            parent.children.append(node)
            stack.append(node)
        
        return root
    
    def _find_missing_chapters(self, template_tree: StructureNode, 
                             target_tree: StructureNode) -> List[MissingChapter]:
        """查找缺失的章节"""
        missing_chapters = []
        
        def check_node(template_node: StructureNode, target_node: StructureNode):
            # 为模板节点的每个子节点在目标节点中查找对应项
            for template_child in template_node.children:
                found = False
                
                for target_child in target_node.children:
                    if self._is_similar_chapter(template_child.title, target_child.title):
                        found = True
                        # 递归检查子节点
                        check_node(template_child, target_child)
                        break
                
                if not found:
                    # 找不到对应章节，记录为缺失
                    missing_chapter = MissingChapter(
                        title=template_child.title,
                        level=template_child.level,
                        expected_path=template_child.path,
                        parent_title=template_node.title if template_node.title != "根节点" else "",
                        position=template_child.position
                    )
                    missing_chapters.append(missing_chapter)
                    
                    # 递归添加所有子章节为缺失
                    self._add_all_descendants_as_missing(template_child, missing_chapters)
        
        check_node(template_tree, target_tree)
        return missing_chapters
    
    def _add_all_descendants_as_missing(self, node: StructureNode, missing_list: List[MissingChapter]):
        """将节点的所有后代添加为缺失章节"""
        for child in node.children:
            missing_chapter = MissingChapter(
                title=child.title,
                level=child.level,
                expected_path=child.path,
                parent_title=node.title,
                position=child.position
            )
            missing_list.append(missing_chapter)
            self._add_all_descendants_as_missing(child, missing_list)
    
    def _find_extra_chapters(self, template_tree: StructureNode, 
                           target_tree: StructureNode, 
                           target_chapters: List[ChapterInfo]) -> List[ChapterInfo]:
        """查找额外的章节（目标文档有但模板没有的）"""
        extra_chapters = []
        
        def check_node(template_node: StructureNode, target_node: StructureNode):
            for target_child in target_node.children:
                found = False
                
                for template_child in template_node.children:
                    if self._is_similar_chapter(target_child.title, template_child.title):
                        found = True
                        # 递归检查子节点
                        check_node(template_child, target_child)
                        break
                
                if not found:
                    # 找到额外章节，添加该章节及其所有子章节
                    self._add_extra_chapter_and_descendants(target_child, target_chapters, extra_chapters)
        
        check_node(template_tree, target_tree)
        return extra_chapters
    
    def _add_extra_chapter_and_descendants(self, node: StructureNode, 
                                         target_chapters: List[ChapterInfo], 
                                         extra_list: List[ChapterInfo]):
        """将节点及其所有后代添加为额外章节"""
        # 添加当前节点
        for chapter in target_chapters:
            if chapter.title == node.title:
                extra_list.append(chapter)
                break
        
        # 递归添加所有子节点
        for child in node.children:
            self._add_extra_chapter_and_descendants(child, target_chapters, extra_list)
    
    def _analyze_structure_issues(self, template_tree: StructureNode, 
                                target_tree: StructureNode) -> List[str]:
        """分析结构问题"""
        issues = []
        
        # 检查层级跳跃问题
        def check_level_consistency(node: StructureNode, path: str = ""):
            for i, child in enumerate(node.children):
                current_path = f"{path} > {child.title}" if path else child.title
                
                # 检查与父节点的层级关系
                if node.title != "根节点" and child.level != node.level + 1:
                    if child.level > node.level + 1:
                        issues.append(f"章节层级跳跃: {current_path} (从 H{node.level} 跳到 H{child.level})")
                    elif child.level <= node.level:
                        issues.append(f"章节层级异常: {current_path} (H{child.level} 不应在 H{node.level} 之下)")
                
                # 检查同级章节的层级一致性
                if i > 0:
                    prev_child = node.children[i-1]
                    if child.level != prev_child.level:
                        # 允许层级递减，但不允许跳跃式递增
                        if child.level > prev_child.level + 1:
                            issues.append(f"同级章节层级跳跃: {current_path} (从 H{prev_child.level} 跳到 H{child.level})")
                
                # 递归检查子节点
                check_level_consistency(child, current_path)
        
        check_level_consistency(target_tree)
        
        return issues
    
    def _is_similar_chapter(self, title1: str, title2: str) -> bool:
        """判断两个章节标题是否相似"""
        # 简单的相似度判断
        title1_clean = self._clean_title(title1)
        title2_clean = self._clean_title(title2)
        
        # 完全匹配
        if title1_clean == title2_clean:
            return True
        
        # 包含关系
        if title1_clean in title2_clean or title2_clean in title1_clean:
            return True
        
        # 使用 LLM 进行语义相似度判断（对于重要章节）
        if len(title1_clean) > 3 and len(title2_clean) > 3:
            return self._llm_similarity_check(title1, title2)
        
        return False
    
    def _clean_title(self, title: str) -> str:
        """清理章节标题"""
        import re
        # 移除数字编号
        title = re.sub(r'^\d+\.?\s*', '', title)
        # 移除特殊字符
        title = re.sub(r'[^\w\s\u4e00-\u9fff]', '', title)
        # 移除多余空格
        title = ' '.join(title.split())
        return title.lower().strip()
    
    def _llm_similarity_check(self, title1: str, title2: str) -> bool:
        """使用 LLM 检查章节标题语义相似度"""
        try:
            prompt = PromptBuilder.build_title_similarity_prompt(title1, title2)
            response = self.llm_client.chat(prompt)
            return "是" in response
            
        except Exception as e:
            logger.warning(f"LLM 相似度检查失败: {e}")
            return False
    
    def _calculate_similarity(self, template_tree: StructureNode, 
                            target_tree: StructureNode) -> float:
        """计算结构相似度"""
        def count_nodes(node: StructureNode) -> int:
            count = 1 if node.title != "根节点" else 0
            for child in node.children:
                count += count_nodes(child)
            return count
        
        def count_matching_nodes(template_node: StructureNode, target_node: StructureNode) -> int:
            matches = 0
            
            for template_child in template_node.children:
                for target_child in target_node.children:
                    if self._is_similar_chapter(template_child.title, target_child.title):
                        matches += 1
                        matches += count_matching_nodes(template_child, target_child)
                        break
            
            return matches
        
        template_count = count_nodes(template_tree)
        if template_count == 0:
            return 1.0
        
        matching_count = count_matching_nodes(template_tree, target_tree)
        return matching_count / template_count
    
    def get_structure_summary(self, structure: StructureNode) -> Dict[str, Any]:
        """获取结构摘要"""
        def analyze_node(node: StructureNode, depth: int = 0) -> Dict[str, Any]:
            info = {
                'title': node.title,
                'level': node.level,
                'depth': depth,
                'children_count': len(node.children),
                'children': []
            }
            
            for child in node.children:
                info['children'].append(analyze_node(child, depth + 1))
            
            return info
        
        def count_by_level(node: StructureNode, counts: Dict[int, int]):
            if node.title != "根节点":
                counts[node.level] = counts.get(node.level, 0) + 1
            
            for child in node.children:
                count_by_level(child, counts)
        
        level_counts = {}
        count_by_level(structure, level_counts)
        
        return {
            'structure': analyze_node(structure),
            'level_distribution': level_counts,
            'max_depth': max(level_counts.keys()) if level_counts else 0,
            'total_chapters': sum(level_counts.values())
        }
    
    def _check_critical_chapters(self, target_chapters: List[ChapterInfo]) -> List[str]:
        """
        检查关键章节是否存在（一到三级章节）
        
        Args:
            target_chapters: 目标文档章节
            
        Returns:
            缺失的关键章节列表
        """
        try:
            required_chapters = config.structure_check.required_critical_chapters
            missing_chapters = []
            
            # 提取一到三级章节标题
            critical_level_titles = [
                chapter.title for chapter in target_chapters 
                if chapter.level in [1, 2, 3]
            ]
            
            logger.debug(f"检测到的一到三级章节: {critical_level_titles}")
            
            for required_chapter in required_chapters:
                found = False
                
                # 先进行简单的文本匹配
                for title in critical_level_titles:
                    if self._is_critical_chapter_match(required_chapter, title):
                        found = True
                        logger.debug(f"找到匹配的关键章节: {required_chapter} -> {title}")
                        break
                
                # 如果简单匹配未找到，使用 LLM 进行语义检查
                if not found:
                    found = self._llm_critical_chapter_check(required_chapter, critical_level_titles)
                    if found:
                        logger.debug(f"通过 LLM 语义匹配找到关键章节: {required_chapter}")
                
                if not found:
                    missing_chapters.append(required_chapter)
                    logger.info(f"缺失关键章节: {required_chapter}")
            
            return missing_chapters
            
        except Exception as e:
            logger.error(f"关键章节检查失败: {e}")
            return []  # 出错时返回空列表，不影响主流程
    
    def _is_critical_chapter_match(self, required_chapter: str, chapter_title: str) -> bool:
        """简单的章节匹配检查"""
        clean_title = self._clean_title(chapter_title)
        clean_required = self._clean_title(required_chapter)
        return clean_required in clean_title
    
    def _llm_critical_chapter_check(self, required_chapter: str, critical_level_titles: List[str]) -> bool:
        """使用 LLM 检查关键章节是否存在"""
        try:
            prompt = PromptBuilder.build_critical_chapter_check_prompt(
                required_chapter, critical_level_titles
            )
            response = self.llm_client.chat(prompt)
            result = "是" in response
            logger.debug(f"LLM 关键章节检查 - {required_chapter}: {result}")
            return result
        except Exception as e:
            logger.warning(f"LLM 关键章节检查失败: {e}")
            return False
    
    def _smart_structure_comparison(self, template_chapters: List[ChapterInfo], 
                                  target_chapters: List[ChapterInfo]) -> Tuple[List[MissingChapter], List[ChapterInfo], float]:
        """
        使用智能映射进行结构比较
        
        Args:
            template_chapters: 模板章节列表
            target_chapters: 目标章节列表
            
        Returns:
            (缺失章节列表, 额外章节列表, 相似度分数)
        """
        try:
            logger.info("使用智能映射算法进行结构比较")
            
            # 创建全局章节映射
            mapping_result = self.chapter_mapper.create_global_mapping(
                template_chapters, target_chapters
            )
            
            # 记录映射统计信息
            stats = self.chapter_mapper.get_mapping_statistics(mapping_result)
            logger.info(f"映射统计: 成功率{stats.get('mapping_rate', 0):.2%}, "
                       f"API调用{stats.get('performance_metrics', {}).get('api_calls', 0)}次")
            
            # 记录重编号模式
            if mapping_result.renumbering_patterns:
                pattern_descriptions = [p.description for p in mapping_result.renumbering_patterns if p.description]
                logger.info(f"检测到重编号模式: {'; '.join(pattern_descriptions)}")
            
            # 基于映射结果分析缺失和额外章节
            missing_chapters = self._analyze_missing_chapters_from_mapping(mapping_result)
            extra_chapters = self._analyze_extra_chapters_from_mapping(mapping_result)
            
            # 使用映射结果的整体置信度作为相似度
            similarity_score = mapping_result.overall_confidence
            
            logger.info(f"智能映射完成: 缺失{len(missing_chapters)}个, 额外{len(extra_chapters)}个, "
                       f"相似度{similarity_score:.2%}")
            
            return missing_chapters, extra_chapters, similarity_score
            
        except Exception as e:
            logger.error(f"智能结构比较失败: {e}")
            # 回退到传统方法
            logger.info("回退到传统章节匹配方法")
            template_structure = self._build_structure_tree(template_chapters)
            target_structure = self._build_structure_tree(target_chapters)
            
            missing_chapters = self._find_missing_chapters(template_structure, target_structure)
            extra_chapters = self._find_extra_chapters(template_structure, target_structure, target_chapters)
            similarity_score = self._calculate_similarity(template_structure, target_structure)
            
            return missing_chapters, extra_chapters, similarity_score
    
    def _analyze_missing_chapters_from_mapping(self, mapping_result: MappingResult) -> List[MissingChapter]:
        """基于映射结果分析缺失章节"""
        missing_chapters = []
        
        try:
            # 添加调试信息
            logger.debug(f"开始分析映射结果，共有 {len(mapping_result.mappings)} 个映射")
            
            # 分析映射结果中的所有映射关系
            for i, mapping in enumerate(mapping_result.mappings):
                template_ch = mapping.template_chapter
                target_ch = mapping.target_chapter
                match_type = mapping.match_type
                
                # 详细的调试日志
                logger.debug(f"映射 {i+1}: {template_ch.title} -> {target_ch.title if target_ch else 'None'}, "
                           f"类型: {match_type.value}, 置信度: {mapping.confidence:.2f}")
                
                # 检查未找到匹配的章节 - 修正：置信度为0的映射也应该被认为是缺失
                if match_type == MatchType.NONE or target_ch is None or mapping.confidence == 0.0:
                    # 构建更详细的父级路径信息
                    parent_title = self._extract_parent_title(template_ch)
                    
                    missing_chapter = MissingChapter(
                        title=template_ch.title,
                        level=template_ch.level,
                        expected_path=template_ch.parent_path if hasattr(template_ch, 'parent_path') else "",
                        parent_title=parent_title,
                        position=template_ch.position
                    )
                    missing_chapters.append(missing_chapter)
                    
                    logger.info(f"识别缺失章节: {template_ch.title} (层级: H{template_ch.level}, 位置: {template_ch.position})")
                else:
                    logger.debug(f"非缺失章节: {template_ch.title} -> {target_ch.title}, 类型: {match_type.value}")
            
            # 额外检查 unmapped_template 以防遗漏
            logger.debug(f"检查未映射的模板章节: {len(mapping_result.unmapped_template)} 个")
            processed_titles = {ch.title for ch in missing_chapters}
            
            for unmapped_ch in mapping_result.unmapped_template:
                logger.debug(f"未映射模板章节: {unmapped_ch.title}")
                
                if unmapped_ch.title not in processed_titles:
                    parent_title = self._extract_parent_title(unmapped_ch)
                    
                    missing_chapter = MissingChapter(
                        title=unmapped_ch.title,
                        level=unmapped_ch.level,
                        expected_path=unmapped_ch.parent_path if hasattr(unmapped_ch, 'parent_path') else "",
                        parent_title=parent_title,
                        position=unmapped_ch.position
                    )
                    missing_chapters.append(missing_chapter)
                    
                    logger.warning(f"额外发现缺失章节: {unmapped_ch.title} (可能的映射遗漏)")
            
        except Exception as e:
            logger.error(f"分析缺失章节失败: {e}", exc_info=True)
        
        # 按位置排序，确保缺失章节列表的逻辑顺序
        missing_chapters.sort(key=lambda x: (x.level, x.position))
        
        logger.info(f"缺失章节分析完成: 共发现 {len(missing_chapters)} 个缺失章节")
        if missing_chapters:
            logger.info(f"缺失章节列表: {[ch.title for ch in missing_chapters]}")
        
        return missing_chapters
    
    def _extract_parent_title(self, chapter: ChapterInfo) -> str:
        """
        提取章节的父级标题
        
        Args:
            chapter: 章节信息
            
        Returns:
            父级章节标题，如果没有则返回空字符串
        """
        try:
            # 如果章节有 parent_path 属性，从中提取父级标题
            if hasattr(chapter, 'parent_path') and chapter.parent_path:
                # parent_path 格式通常为 "父章节1 > 父章节2"
                path_parts = chapter.parent_path.split(' > ')
                if path_parts:
                    return path_parts[-1].strip()  # 返回最直接的父级
            
            # 如果没有 parent_path，尝试从标题中推断
            # 例如：从 "3.1 API接口" 推断父级可能是 "3. 对外接口"
            title = chapter.title.strip()
            
            # 匹配编号格式：3.1, 3.2 等
            import re
            match = re.match(r'^(\d+)\.(\d+)', title)
            if match:
                parent_number = match.group(1)
                # 构建可能的父级标题模式（这里只是示例，实际可能需要更复杂的逻辑）
                return f"第{parent_number}级章节"
            
            # 如果章节层级大于1，表示可能有父级
            if chapter.level > 1:
                return f"H{chapter.level - 1}级章节"
            
            return ""
            
        except Exception as e:
            logger.warning(f"提取父级标题失败: {e}")
            return ""
    
    def _analyze_extra_chapters_from_mapping(self, mapping_result: MappingResult) -> List[ChapterInfo]:
        """基于映射结果分析额外章节"""
        extra_chapters = []
        
        try:
            # 直接使用未映射的目标章节作为额外章节
            extra_chapters = mapping_result.unmapped_target.copy()
            
            for chapter in extra_chapters:
                logger.debug(f"识别额外章节: {chapter.title}")
            
        except Exception as e:
            logger.warning(f"分析额外章节失败: {e}")
        
        return extra_chapters
    
    def get_mapping_details(self, template_chapters: List[ChapterInfo], 
                          target_chapters: List[ChapterInfo]) -> Dict[str, Any]:
        """
        获取详细的映射信息（用于调试和分析）
        
        Args:
            template_chapters: 模板章节列表
            target_chapters: 目标章节列表
            
        Returns:
            详细的映射信息
        """
        try:
            if not self.enable_smart_mapping:
                return {"error": "智能映射未启用"}
            
            # 创建映射
            mapping_result = self.chapter_mapper.create_global_mapping(
                template_chapters, target_chapters
            )
            
            # 构建详细信息
            details = {
                "mapping_summary": mapping_result.mapping_summary,
                "overall_confidence": mapping_result.overall_confidence,
                "renumbering_patterns": [],
                "mappings": [],
                "unmapped_template": [ch.title for ch in mapping_result.unmapped_template],
                "unmapped_target": [ch.title for ch in mapping_result.unmapped_target],
                "performance_metrics": mapping_result.performance_metrics
            }
            
            # 重编号模式详情
            for pattern in mapping_result.renumbering_patterns:
                pattern_info = {
                    "type": pattern.pattern_type.value,
                    "confidence": pattern.confidence,
                    "description": pattern.description,
                    "affected_levels": pattern.affected_levels,
                    "examples": pattern.examples
                }
                details["renumbering_patterns"].append(pattern_info)
            
            # 映射详情
            for mapping in mapping_result.mappings:
                mapping_info = {
                    "template_title": mapping.template_chapter.title,
                    "target_title": mapping.target_chapter.title if mapping.target_chapter else None,
                    "match_type": mapping.match_type.value,
                    "confidence": mapping.confidence,
                    "confidence_level": mapping.confidence_level.value,
                    "similarity_scores": {
                        "title": mapping.similarity_scores.title_similarity,
                        "content": mapping.similarity_scores.content_similarity,
                        "position": mapping.similarity_scores.position_similarity,
                        "structure": mapping.similarity_scores.structure_similarity,
                        "overall": mapping.similarity_scores.overall_similarity
                    },
                    "llm_reasoning": mapping.llm_reasoning,
                    "mapping_notes": mapping.mapping_notes
                }
                details["mappings"].append(mapping_info)
            
            return details
            
        except Exception as e:
            logger.error(f"获取映射详情失败: {e}")
            return {"error": str(e)}
    
    def set_smart_mapping_enabled(self, enabled: bool):
        """设置是否启用智能映射"""
        self.enable_smart_mapping = enabled
        logger.info(f"智能映射已{'启用' if enabled else '禁用'}")
    
    def configure_mapping(self, config: MappingConfig):
        """配置映射参数"""
        self.chapter_mapper = ChapterMapper(config)
        logger.info("章节映射器配置已更新")
