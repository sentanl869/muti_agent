"""
增强的语义匹配器
提供批量语义匹配和上下文感知的章节匹配功能
"""

import logging
import time
import re
from typing import List, Dict, Tuple, Optional

from utils.llm_client import LLMClient
from utils.html_parser import ChapterInfo
from utils.chapter_mapping_types import (
    BatchSemanticRequest, BatchSemanticResponse, 
    SimilarityScores, MatchingContext
)
from prompts import PromptBuilder

logger = logging.getLogger(__name__)


class SemanticMatcher:
    """增强的语义匹配器"""
    
    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()
        self.cache = {}  # 缓存语义匹配结果
        self.api_call_count = 0
        
    def batch_semantic_match(self, request: BatchSemanticRequest) -> BatchSemanticResponse:
        """
        批量语义匹配，减少LLM API调用次数
        
        Args:
            request: 批量匹配请求
            
        Returns:
            批量匹配响应，包含相似度矩阵
        """
        start_time = time.time()
        
        try:
            template_titles = request.template_titles
            target_titles = request.target_titles
            
            # 计算总的章节对数量
            total_pairs = len(template_titles) * len(target_titles)
            
            # 智能批量策略：根据章节数量决定处理方式
            if total_pairs <= 150:  # 小规模：一次性处理
                api_calls = 1
                batch_result = self._process_batch(
                    template_titles, target_titles, request.context_info
                )
                similarity_matrix = batch_result['similarities']
                reasoning_matrix = batch_result['reasoning']
                
            elif total_pairs <= 400:  # 中等规模：按模板章节分批
                api_calls = 0
                similarity_matrix = []
                reasoning_matrix = []
                
                # 按模板章节分批，每批处理所有目标章节
                batch_size = min(10, len(template_titles))
                for i in range(0, len(template_titles), batch_size):
                    batch_template = template_titles[i:i + batch_size]
                    
                    batch_result = self._process_batch(
                        batch_template, target_titles, request.context_info
                    )
                    
                    similarity_matrix.extend(batch_result['similarities'])
                    reasoning_matrix.extend(batch_result['reasoning'])
                    api_calls += 1
                    
            else:  # 大规模：使用文本相似度替代语义匹配
                logger.info(f"章节数量过多({total_pairs}对)，使用文本相似度替代语义匹配")
                api_calls = 0
                similarity_matrix = self._calculate_text_similarity_matrix(template_titles, target_titles)
                reasoning_matrix = [["文本相似度计算" for _ in target_titles] for _ in template_titles]
            
            self.api_call_count += api_calls
            processing_time = time.time() - start_time
            
            logger.info(f"批量语义匹配完成: {len(template_titles)}x{len(target_titles)} 矩阵, "
                       f"API调用: {api_calls}, 耗时: {processing_time:.2f}s")
            
            return BatchSemanticResponse(
                similarity_matrix=similarity_matrix,
                reasoning_matrix=reasoning_matrix,
                processing_time=processing_time,
                api_calls_count=api_calls
            )
            
        except Exception as e:
            logger.error(f"批量语义匹配失败: {e}")
            # 返回空结果矩阵
            return BatchSemanticResponse(
                similarity_matrix=[[0.0 for _ in request.target_titles] for _ in request.template_titles],
                reasoning_matrix=[["匹配失败" for _ in request.target_titles] for _ in request.template_titles],
                processing_time=time.time() - start_time,
                api_calls_count=0
            )
    
    def _process_batch(self, template_titles: List[str], target_titles: List[str], 
                      context_info: str = "") -> Dict:
        """处理单个批次的语义匹配"""
        try:
            # 构建批量匹配提示词
            prompt = PromptBuilder.build_batch_semantic_matching_prompt(
                template_titles, target_titles, context_info
            )
            
            # 调用LLM
            response = self.llm_client.chat(prompt)
            
            # 解析响应
            return self._parse_batch_response(response, len(template_titles), len(target_titles))
            
        except Exception as e:
            logger.warning(f"批次处理失败: {e}")
            # 返回默认结果
            return {
                'similarities': [[0.0 for _ in target_titles] for _ in template_titles],
                'reasoning': [["处理失败" for _ in target_titles] for _ in template_titles]
            }
    
    def _parse_batch_response(self, response: str, template_count: int, 
                            target_count: int) -> Dict:
        """解析批量匹配响应"""
        similarities = [[0.0 for _ in range(target_count)] for _ in range(template_count)]
        reasoning = [["" for _ in range(target_count)] for _ in range(template_count)]
        
        try:
            # 查找相似度矩阵部分
            matrix_start = response.find("SIMILARITY_MATRIX:")
            if matrix_start == -1:
                logger.warning("未找到相似度矩阵标记")
                return {'similarities': similarities, 'reasoning': reasoning}
            
            matrix_content = response[matrix_start:]
            
            # 解析每一行
            lines = matrix_content.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('SIMILARITY_MATRIX:') or line.startswith('```'):
                    continue
                
                # 匹配格式：T1-G1: 0.9 | 原因：...
                match = re.match(r'T(\d+)-G(\d+):\s*([\d.]+)\s*\|\s*原因：(.+)', line)
                if match:
                    t_idx = int(match.group(1)) - 1
                    g_idx = int(match.group(2)) - 1
                    score = float(match.group(3))
                    reason = match.group(4).strip()
                    
                    if 0 <= t_idx < template_count and 0 <= g_idx < target_count:
                        similarities[t_idx][g_idx] = min(1.0, max(0.0, score))
                        reasoning[t_idx][g_idx] = reason
            
        except Exception as e:
            logger.warning(f"解析批量响应失败: {e}")
        
        return {'similarities': similarities, 'reasoning': reasoning}
    
    def context_aware_match(self, template_chapter: ChapterInfo, 
                          target_chapters: List[ChapterInfo],
                          context: MatchingContext) -> Tuple[Optional[ChapterInfo], float, str]:
        """
        上下文感知的章节匹配
        
        Args:
            template_chapter: 模板章节
            target_chapters: 候选目标章节列表
            context: 匹配上下文
            
        Returns:
            (最佳匹配章节, 相似度分数, 推理过程)
        """
        if not target_chapters:
            return None, 0.0, "无候选章节"
        
        try:
            # 构建上下文信息
            context_info = self._build_context_info(template_chapter, context)
            
            # 构建上下文感知的匹配提示词
            prompt = PromptBuilder.build_context_aware_matching_prompt(
                template_chapter.title,
                template_chapter.level,
                template_chapter.position,
                target_chapters,
                context_info
            )
            
            # 调用LLM
            response = self.llm_client.chat(prompt)
            self.api_call_count += 1
            
            # 解析响应
            best_chapter, best_score, best_reasoning = self._parse_context_aware_response(
                response, target_chapters
            )
            
            return best_chapter, best_score, best_reasoning
            
        except Exception as e:
            logger.error(f"上下文感知匹配失败: {e}")
            return None, 0.0, f"匹配失败: {e}"
    
    def _parse_context_aware_response(self, response: str, 
                                    target_chapters: List[ChapterInfo]) -> Tuple[Optional[ChapterInfo], float, str]:
        """解析上下文感知匹配响应"""
        best_score = 0.0
        best_chapter = None
        best_reasoning = ""
        
        try:
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 匹配格式：候选1: 0.9 | 原因：...
                match = re.match(r'候选(\d+):\s*([\d.]+)\s*\|\s*原因：(.+)', line)
                if match:
                    candidate_idx = int(match.group(1)) - 1
                    score = float(match.group(2))
                    reasoning = match.group(3).strip()
                    
                    if 0 <= candidate_idx < len(target_chapters) and score > best_score:
                        best_score = score
                        best_chapter = target_chapters[candidate_idx]
                        best_reasoning = reasoning
            
        except Exception as e:
            logger.warning(f"解析上下文感知响应失败: {e}")
        
        return best_chapter, best_score, best_reasoning
    
    def _build_context_info(self, template_chapter: ChapterInfo, 
                          context: MatchingContext) -> str:
        """构建上下文信息"""
        context_parts = []
        
        # 添加章节层级信息
        context_parts.append(f"章节层级: H{template_chapter.level}")
        
        # 添加父章节信息
        if template_chapter.parent_path:
            context_parts.append(f"父章节路径: {template_chapter.parent_path}")
        
        # 添加位置信息
        context_parts.append(f"章节位置: 第{template_chapter.position + 1}个")
        
        # 添加重编号模式信息
        if context.global_patterns:
            pattern_descriptions = []
            for pattern in context.global_patterns:
                if pattern.description:
                    pattern_descriptions.append(pattern.description)
            if pattern_descriptions:
                context_parts.append(f"检测到的重编号模式: {'; '.join(pattern_descriptions)}")
        
        # 添加同级章节信息
        if context.sibling_mappings:
            sibling_info = []
            for mapping in context.sibling_mappings[-3:]:  # 最近的3个同级映射
                if mapping.target_chapter:
                    sibling_info.append(f"{mapping.template_chapter.title} → {mapping.target_chapter.title}")
            if sibling_info:
                context_parts.append(f"同级章节映射: {'; '.join(sibling_info)}")
        
        return "\n".join(context_parts)
    
    def calculate_semantic_similarity(self, title1: str, title2: str, 
                                    use_cache: bool = True) -> Tuple[float, str]:
        """
        计算两个标题的语义相似度
        
        Args:
            title1: 第一个标题
            title2: 第二个标题
            use_cache: 是否使用缓存
            
        Returns:
            (相似度分数, 推理过程)
        """
        # 检查缓存
        cache_key = f"{title1}||{title2}"
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # 使用批量匹配接口
            request = BatchSemanticRequest(
                template_titles=[title1],
                target_titles=[title2],
                max_batch_size=1
            )
            
            response = self.batch_semantic_match(request)
            
            if response.similarity_matrix and response.similarity_matrix[0]:
                score = response.similarity_matrix[0][0]
                reasoning = response.reasoning_matrix[0][0] if response.reasoning_matrix else ""
            else:
                score = 0.0
                reasoning = "匹配失败"
            
            # 缓存结果
            if use_cache:
                self.cache[cache_key] = (score, reasoning)
            
            return score, reasoning
            
        except Exception as e:
            logger.warning(f"语义相似度计算失败: {e}")
            return 0.0, f"计算失败: {e}"
    
    def calculate_content_similarity(self, content1: str, content2: str) -> float:
        """
        计算内容相似度（基于简单的文本分析）
        
        Args:
            content1: 第一个内容
            content2: 第二个内容
            
        Returns:
            相似度分数 (0.0-1.0)
        """
        try:
            if not content1 or not content2:
                return 0.0
            
            # 简单的关键词匹配方法
            words1 = set(self._extract_keywords(content1))
            words2 = set(self._extract_keywords(content2))
            
            if not words1 or not words2:
                return 0.0
            
            # 计算Jaccard相似度
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"内容相似度计算失败: {e}")
            return 0.0
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        try:
            # 移除标点符号和数字
            text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
            text = re.sub(r'\d+', ' ', text)
            
            # 分词（简单的空格分割）
            words = text.split()
            
            # 过滤短词和停用词
            stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '而', '了', '着', '过'}
            keywords = [word for word in words if len(word) > 1 and word not in stop_words]
            
            return keywords
            
        except Exception as e:
            logger.warning(f"关键词提取失败: {e}")
            return []
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        计算标题相似度（基于文本分析）
        
        Args:
            title1: 第一个标题
            title2: 第二个标题
            
        Returns:
            相似度分数 (0.0-1.0)
        """
        try:
            # 清理标题
            clean_title1 = self._clean_title(title1)
            clean_title2 = self._clean_title(title2)
            
            # 完全匹配
            if clean_title1 == clean_title2:
                return 1.0
            
            # 包含关系
            if clean_title1 in clean_title2 or clean_title2 in clean_title1:
                return 0.8
            
            # 关键词相似度
            words1 = set(self._extract_keywords(clean_title1))
            words2 = set(self._extract_keywords(clean_title2))
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"标题相似度计算失败: {e}")
            return 0.0
    
    def _clean_title(self, title: str) -> str:
        """清理章节标题"""
        try:
            # 移除数字编号
            title = re.sub(r'^\d+\.?\s*', '', title)
            # 移除特殊字符
            title = re.sub(r'[^\w\s\u4e00-\u9fff]', '', title)
            # 移除多余空格
            title = ' '.join(title.split())
            return title.lower().strip()
        except Exception as e:
            logger.warning(f"标题清理失败: {e}")
            return title.strip()
    
    def calculate_position_similarity(self, pos1: int, pos2: int, total_count: int) -> float:
        """
        计算位置相似度
        
        Args:
            pos1: 第一个位置
            pos2: 第二个位置
            total_count: 总章节数
            
        Returns:
            相似度分数 (0.0-1.0)
        """
        try:
            if total_count <= 1:
                return 1.0
            
            # 计算位置差异的相对值
            position_diff = abs(pos1 - pos2)
            max_diff = total_count - 1
            
            # 转换为相似度分数
            similarity = 1.0 - (position_diff / max_diff)
            return max(0.0, similarity)
            
        except Exception as e:
            logger.warning(f"位置相似度计算失败: {e}")
            return 0.0
    
    def get_api_call_stats(self) -> Dict[str, int]:
        """获取API调用统计"""
        return {
            'total_api_calls': self.api_call_count,
            'cache_size': len(self.cache)
        }
    
    def _calculate_text_similarity_matrix(self, template_titles: List[str], 
                                        target_titles: List[str]) -> List[List[float]]:
        """
        计算文本相似度矩阵（用于大规模章节匹配时替代语义匹配）
        
        Args:
            template_titles: 模板章节标题列表
            target_titles: 目标章节标题列表
            
        Returns:
            相似度矩阵
        """
        try:
            similarity_matrix = []
            
            for template_title in template_titles:
                row = []
                for target_title in target_titles:
                    # 使用标题相似度计算
                    similarity = self.calculate_title_similarity(template_title, target_title)
                    row.append(similarity)
                similarity_matrix.append(row)
            
            logger.info(f"文本相似度矩阵计算完成: {len(template_titles)}x{len(target_titles)}")
            return similarity_matrix
            
        except Exception as e:
            logger.error(f"文本相似度矩阵计算失败: {e}")
            # 返回零矩阵
            return [[0.0 for _ in target_titles] for _ in template_titles]
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("语义匹配缓存已清空")
