"""
内容规范检查 Agent
负责检查文档内容是否符合规范要求
"""

import logging
import yaml
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from utils.content_integrator import IntegratedChapter
from utils.llm_client import MultiModalClient
from config.config import config
from prompts import PromptBuilder

logger = logging.getLogger(__name__)


@dataclass
class Violation:
    """违规项"""
    rule: str
    content: str
    content_type: str  # "text" 或 "image"
    position: str
    suggestion: str
    severity: str = "warning"  # "critical", "warning", "info"
    chapter_title: str = ""


@dataclass
class ChapterCheckResult:
    """章节检查结果"""
    chapter_title: str
    violations: List[Violation]
    passed: bool
    total_rules_checked: int
    violation_count: int


@dataclass
class ContentCheckResult:
    """内容检查结果"""
    passed: bool
    chapters: List[ChapterCheckResult]
    total_violations: int
    rules_summary: Dict[str, int]
    severity_summary: Dict[str, int]


class ContentChecker:
    """内容规范检查 Agent"""
    
    def __init__(self):
        self.multimodal_client = MultiModalClient()
        self.rules = self._load_rules()
        self.severity_mapping = self._load_severity_mapping()
    
    def _load_rules(self) -> Dict[str, List[str]]:
        """加载规范规则"""
        try:
            with open('config/rules.yaml', 'r', encoding='utf-8') as f:
                rules_config = yaml.safe_load(f)
            
            rules = rules_config.get('rules', {})
            
            # 合并所有规则类型
            all_rules = []
            for rule_type, rule_list in rules.items():
                all_rules.extend(rule_list)
            
            logger.info(f"加载规范规则: {len(all_rules)} 条")
            
            return {
                'all_rules': all_rules,
                'text_rules': rules.get('text_rules', []),
                'image_rules': rules.get('image_rules', []),
                'structure_rules': rules.get('structure_rules', []),
                'format_rules': rules.get('format_rules', [])
            }
            
        except Exception as e:
            logger.error(f"加载规范规则失败: {e}")
            return {'all_rules': []}
    
    def _load_severity_mapping(self) -> Dict[str, str]:
        """加载严重程度映射"""
        try:
            with open('config/rules.yaml', 'r', encoding='utf-8') as f:
                rules_config = yaml.safe_load(f)
            
            severity_levels = rules_config.get('severity_levels', {})
            mapping = {}
            
            for severity, rules in severity_levels.items():
                for rule in rules:
                    mapping[rule] = severity
            
            return mapping
            
        except Exception as e:
            logger.warning(f"加载严重程度映射失败: {e}")
            return {}
    
    def check_content_compliance(self, chapters: List[IntegratedChapter]) -> ContentCheckResult:
        """
        检查内容规范合规性
        
        Args:
            chapters: 整合后的章节列表
            
        Returns:
            内容检查结果
        """
        try:
            logger.info(f"开始内容规范检查: {len(chapters)} 个章节")
            
            chapter_results = []
            total_violations = 0
            rules_summary = {}
            severity_summary = {"critical": 0, "warning": 0, "info": 0}
            
            for chapter in chapters:
                chapter_result = self._check_chapter_content(chapter)
                chapter_results.append(chapter_result)
                
                total_violations += chapter_result.violation_count
                
                # 统计违规规则
                for violation in chapter_result.violations:
                    rule = violation.rule
                    rules_summary[rule] = rules_summary.get(rule, 0) + 1
                    severity_summary[violation.severity] += 1
            
            # 判断整体是否通过
            passed = total_violations == 0
            
            result = ContentCheckResult(
                passed=passed,
                chapters=chapter_results,
                total_violations=total_violations,
                rules_summary=rules_summary,
                severity_summary=severity_summary
            )
            
            logger.info(f"内容规范检查完成: {'通过' if passed else '失败'}")
            logger.info(f"总违规项: {total_violations}")
            logger.info(f"严重程度分布: {severity_summary}")
            
            return result
            
        except Exception as e:
            logger.error(f"内容规范检查失败: {e}")
            raise
    
    def _check_chapter_content(self, chapter: IntegratedChapter) -> ChapterCheckResult:
        """检查单个章节的内容"""
        try:
            logger.debug(f"检查章节: {chapter.title}")
            
            violations = []
            
            # 使用 LLM 检查内容规范
            chapter_violations = self._llm_check_content(chapter)
            violations.extend(chapter_violations)
            
            # 特定规则检查
            specific_violations = self._specific_rule_checks(chapter)
            violations.extend(specific_violations)
            
            # 设置违规项的严重程度
            for violation in violations:
                violation.severity = self._get_violation_severity(violation.rule)
                violation.chapter_title = chapter.title
            
            passed = len(violations) == 0
            
            result = ChapterCheckResult(
                chapter_title=chapter.title,
                violations=violations,
                passed=passed,
                total_rules_checked=len(self.rules['all_rules']),
                violation_count=len(violations)
            )
            
            if violations:
                logger.debug(f"章节 {chapter.title} 发现 {len(violations)} 个违规项")
            
            return result
            
        except Exception as e:
            logger.error(f"章节内容检查失败 {chapter.title}: {e}")
            # 返回一个空的结果
            return ChapterCheckResult(
                chapter_title=chapter.title,
                violations=[],
                passed=True,
                total_rules_checked=0,
                violation_count=0
            )
    
    def _llm_check_content(self, chapter: IntegratedChapter) -> List[Violation]:
        """使用 LLM 检查内容规范"""
        violations = []
        
        try:
            # 构建检查提示词
            prompt = self._build_check_prompt(chapter)
            
            # 调用 LLM 进行检查
            response = self.multimodal_client.analyze_text(prompt)
            
            # 解析 LLM 响应
            parsed_violations = self._parse_llm_response(response, chapter)
            violations.extend(parsed_violations)
            
        except Exception as e:
            logger.error(f"LLM 内容检查失败: {e}")
        
        return violations
    
    def _build_check_prompt(self, chapter: IntegratedChapter) -> str:
        """构建内容检查提示词"""
        rules_text = "\n".join([f"- {rule}" for rule in self.rules['all_rules']])
        return PromptBuilder.build_content_check_prompt(rules_text, chapter.combined_content)
    
    def _parse_llm_response(self, response: str, chapter: IntegratedChapter) -> List[Violation]:
        """解析 LLM 响应，提取违规项"""
        violations = []
        
        try:
            if "未发现违规项" in response:
                return violations
            
            # 简单的解析逻辑
            lines = response.split('\n')
            current_violation = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('违规项'):
                    # 保存前一个违规项
                    if current_violation:
                        violation = self._create_violation_from_dict(current_violation, chapter)
                        if violation:
                            violations.append(violation)
                    current_violation = {}
                
                elif line.startswith('规范:'):
                    current_violation['rule'] = line[3:].strip()
                elif line.startswith('内容:'):
                    current_violation['content'] = line[3:].strip()
                elif line.startswith('位置:'):
                    current_violation['position'] = line[3:].strip()
                elif line.startswith('建议:'):
                    current_violation['suggestion'] = line[3:].strip()
            
            # 处理最后一个违规项
            if current_violation:
                violation = self._create_violation_from_dict(current_violation, chapter)
                if violation:
                    violations.append(violation)
            
        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
        
        return violations
    
    def _create_violation_from_dict(self, violation_dict: Dict[str, str], 
                                  chapter: IntegratedChapter) -> Optional[Violation]:
        """从字典创建违规项对象"""
        try:
            rule = violation_dict.get('rule', '').strip()
            content = violation_dict.get('content', '').strip()
            position = violation_dict.get('position', '').strip()
            suggestion = violation_dict.get('suggestion', '').strip()
            
            if not rule or not content:
                return None
            
            # 判断内容类型
            content_type = "image" if "图" in content or "图片" in content else "text"
            
            violation = Violation(
                rule=rule,
                content=content,
                content_type=content_type,
                position=position or f"章节: {chapter.title}",
                suggestion=suggestion or "请根据规范要求进行修改",
                chapter_title=chapter.title
            )
            
            return violation
            
        except Exception as e:
            logger.error(f"创建违规项失败: {e}")
            return None
    
    def _specific_rule_checks(self, chapter: IntegratedChapter) -> List[Violation]:
        """特定规则检查（基于规则的硬编码检查）"""
        violations = []
        
        try:
            # 检查章节标题
            title_violations = self._check_title_rules(chapter)
            violations.extend(title_violations)
            
            # 检查图像规范（根据配置决定是否执行）
            if config.check.enable_image_check:
                image_violations = self._check_image_rules(chapter)
                violations.extend(image_violations)
                logger.debug(f"章节 {chapter.title} 图像检查完成: {len(image_violations)} 个违规项")
            else:
                logger.debug(f"章节 {chapter.title} 跳过图像检查（已禁用）")
            
            # 检查格式规范
            format_violations = self._check_format_rules(chapter)
            violations.extend(format_violations)
            
        except Exception as e:
            logger.error(f"特定规则检查失败: {e}")
        
        return violations
    
    def _check_title_rules(self, chapter: IntegratedChapter) -> List[Violation]:
        """检查标题规范"""
        violations = []
        
        # 检查标题是否为空
        if not chapter.title.strip():
            violations.append(Violation(
                rule="每个章节必须有明确的标题",
                content=f"章节标题为空",
                content_type="text",
                position=f"章节位置: {chapter.position}",
                suggestion="请为章节添加明确的标题"
            ))
        
        # 检查标题层级
        if chapter.level > 4:
            violations.append(Violation(
                rule="子章节层级不应超过4级",
                content=f"章节 '{chapter.title}' 层级为 H{chapter.level}",
                content_type="text",
                position=f"章节: {chapter.title}",
                suggestion="请调整章节层级结构，避免过深的嵌套"
            ))
        
        return violations
    
    def _check_image_rules(self, chapter: IntegratedChapter) -> List[Violation]:
        """检查图像规范"""
        violations = []
        
        for image in chapter.images:
            # 检查图像是否有描述
            if not image.description or "图像处理失败" in image.description:
                violations.append(Violation(
                    rule="图片必须有相关的文字说明或说明文字",
                    content=f"图片 {image.position} 缺少有效描述",
                    content_type="image",
                    position=image.position,
                    suggestion="请为图片添加清晰的说明文字或确保图片质量"
                ))
            
            # 检查 Alt 文本
            if not image.alt_text:
                violations.append(Violation(
                    rule="图片必须有相关的文字说明或说明文字",
                    content=f"图片 {image.position} 缺少 Alt 文本",
                    content_type="image",
                    position=image.position,
                    suggestion="请为图片添加 Alt 属性文本"
                ))
        
        return violations
    
    def _check_format_rules(self, chapter: IntegratedChapter) -> List[Violation]:
        """检查格式规范"""
        violations = []
        
        content = chapter.text_content
        
        # 检查代码块
        if "```" in content:
            # 简单检查代码块是否指定了语言
            import re
            code_blocks = re.findall(r'```(\w*)', content)
            for i, lang in enumerate(code_blocks):
                if not lang:
                    violations.append(Violation(
                        rule="代码块必须指定编程语言",
                        content=f"第 {i+1} 个代码块未指定编程语言",
                        content_type="text",
                        position=f"章节: {chapter.title}",
                        suggestion="请在代码块开始处指定编程语言，如 ```python"
                    ))
        
        return violations
    
    def _get_violation_severity(self, rule: str) -> str:
        """获取违规项的严重程度"""
        return self.severity_mapping.get(rule, "warning")
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """获取规则摘要"""
        return {
            'total_rules': len(self.rules['all_rules']),
            'rule_categories': {
                'text_rules': len(self.rules.get('text_rules', [])),
                'image_rules': len(self.rules.get('image_rules', [])),
                'structure_rules': len(self.rules.get('structure_rules', [])),
                'format_rules': len(self.rules.get('format_rules', []))
            },
            'severity_distribution': {
                'critical': len([r for r, s in self.severity_mapping.items() if s == 'critical']),
                'warning': len([r for r, s in self.severity_mapping.items() if s == 'warning']),
                'info': len([r for r, s in self.severity_mapping.items() if s == 'info'])
            }
        }
