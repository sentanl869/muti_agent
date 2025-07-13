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
            
            # 比较结构
            missing_chapters = self._find_missing_chapters(template_structure, target_structure)
            extra_chapters = self._find_extra_chapters(template_structure, target_structure, target_chapters)
            structure_issues = self._analyze_structure_issues(template_structure, target_structure)
            
            # 计算相似度
            similarity_score = self._calculate_similarity(template_structure, target_structure)
            
            # 判断是否通过
            passed = len(missing_chapters) == 0 and len(structure_issues) == 0
            
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
