"""
泛化标题优化效果验证脚本
测试优化后的提示词对泛化标题的识别和匹配效果
包含真实的LLM调用和结果验证
"""

import logging
import sys
import os
import time
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from prompts import PromptBuilder
from utils.llm_client import LLMClient, MultiModalClient
from utils.semantic_matcher import SemanticMatcher
from utils.chapter_mapping_types import BatchSemanticRequest
from utils.html_parser import ChapterInfo
from config.config import config

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """测试结果"""
    passed: bool
    actual_result: str
    expected_result: str
    reasoning: str
    execution_time: float

@dataclass
class TestStats:
    """测试统计"""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    total_time: float = 0.0
    api_calls: int = 0
    
    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.total_tests += 1
        if result.passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        self.total_time += result.execution_time
    
    def get_pass_rate(self) -> float:
        """获取通过率"""
        return (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0.0
    
    def print_summary(self):
        """打印统计摘要"""
        print(f"\n{'='*80}")
        print(f"测试统计摘要")
        print(f"{'='*80}")
        print(f"总测试数: {self.total_tests}")
        print(f"通过: {self.passed_tests}")
        print(f"失败: {self.failed_tests}")
        print(f"通过率: {self.get_pass_rate():.1f}%")
        print(f"总耗时: {self.total_time:.2f}秒")
        print(f"API调用次数: {self.api_calls}")
        if self.total_tests > 0:
            print(f"平均每测试耗时: {self.total_time/self.total_tests:.2f}秒")

class GenericTitleOptimizationTester:
    """泛化标题优化测试器"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.semantic_matcher = SemanticMatcher(self.llm_client)
        self.multimodal_client = MultiModalClient()
        self.stats = TestStats()
        
        logger.info("测试器初始化完成")
        logger.info(f"LLM模型: {config.llm.model}")
        logger.info(f"API地址: {config.llm.base_url}")
    
    def test_single_title_similarity(self, template: str, target: str, expected: str) -> TestResult:
        """测试单个标题相似度判断"""
        start_time = time.time()
        
        try:
            # 构建提示词
            prompt = PromptBuilder.build_title_similarity_prompt(template, target)
            
            # 调用LLM
            response = self.llm_client.chat(prompt)
            self.stats.api_calls += 1
            
            # 解析响应
            actual_result = response.strip()
            
            # 验证结果
            passed = self._verify_similarity_result(actual_result, expected)
            
            execution_time = time.time() - start_time
            
            return TestResult(
                passed=passed,
                actual_result=actual_result,
                expected_result=expected,
                reasoning=f"LLM响应: {response}",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"标题相似度测试失败: {e}")
            
            return TestResult(
                passed=False,
                actual_result=f"错误: {str(e)}",
                expected_result=expected,
                reasoning=f"执行异常: {e}",
                execution_time=execution_time
            )
    
    def _verify_similarity_result(self, actual: str, expected: str) -> bool:
        """验证相似度结果"""
        # 清理响应文本
        actual_clean = actual.lower().strip()
        expected_clean = expected.lower().strip()
        
        # 检查是否包含预期结果
        if expected_clean == "是":
            return "是" in actual_clean and "否" not in actual_clean
        elif expected_clean == "否":
            return "否" in actual_clean and "是" not in actual_clean
        else:
            return actual_clean == expected_clean
    
    def test_generic_title_matching(self):
        """测试泛化标题匹配功能"""
        
        # 测试用例：泛化标题和对应的具体实现
        test_cases = [
            # 括号说明类型
            {
                "template": "流程1(改成具体的流程名字)",
                "target": "用户注册流程",
                "expected": "是",
                "description": "括号说明类型 - 流程替换"
            },
            {
                "template": "功能模块(根据需要可自行添加)",
                "target": "支付功能模块",
                "expected": "是",
                "description": "括号说明类型 - 功能模块"
            },
            
            # 斜杠选择类型
            {
                "template": "子模块1/类1/主题1",
                "target": "用户管理子模块",
                "expected": "是",
                "description": "斜杠选择类型 - 子模块匹配"
            },
            {
                "template": "子模块2/类2/主题2",
                "target": "数据处理类",
                "expected": "是",
                "description": "斜杠选择类型 - 类匹配"
            },
            
            # 变量表达类型
            {
                "template": "流程x(根据需要可自行添加章节)",
                "target": "数据备份流程",
                "expected": "是",
                "description": "变量表达类型 - 流程x"
            },
            
            # 编号类型
            {
                "template": "模块1安全设计",
                "target": "用户认证模块安全设计",
                "expected": "是",
                "description": "编号类型 - 模块编号"
            },
            
            # 占位符类型
            {
                "template": "XX模块功能说明",
                "target": "支付模块功能说明",
                "expected": "是",
                "description": "占位符类型 - XX占位符"
            },
            
            # 可扩展性描述类型
            {
                "template": "扩展功能(根据需要可自行添加)",
                "target": "消息推送功能",
                "expected": "是",
                "description": "可扩展性描述类型"
            },
            
            # 负面测试：确实不相关的情况
            {
                "template": "用户认证模块",
                "target": "数据库配置",
                "expected": "否",
                "description": "负面测试 - 完全不相关"
            },
            
            # 边界测试：相似但不完全匹配
            {
                "template": "用户管理模块",
                "target": "用户认证模块",
                "expected": "否",
                "description": "边界测试 - 相似但不同功能"
            }
        ]
        
        print("=" * 80)
        print("泛化标题匹配测试")
        print("=" * 80)
        
        failed_cases = []
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n测试用例 {i}: {case['description']}")
            print(f"模板标题: {case['template']}")
            print(f"目标标题: {case['target']}")
            print(f"期望结果: {case['expected']}")
            
            # 执行测试
            result = self.test_single_title_similarity(
                case['template'], case['target'], case['expected']
            )
            
            # 记录统计
            self.stats.add_result(result)
            
            # 显示结果
            status = "✅ 通过" if result.passed else "❌ 失败"
            print(f"实际结果: {result.actual_result}")
            print(f"测试状态: {status}")
            print(f"执行时间: {result.execution_time:.2f}秒")
            
            if not result.passed:
                failed_cases.append({
                    'case_id': i,
                    'description': case['description'],
                    'expected': case['expected'],
                    'actual': result.actual_result,
                    'reasoning': result.reasoning
                })
                print(f"失败原因: {result.reasoning}")
            
            print("-" * 50)
        
        # 显示失败案例汇总
        if failed_cases:
            print(f"\n失败案例汇总 ({len(failed_cases)}个):")
            for case in failed_cases:
                print(f"用例{case['case_id']}: {case['description']}")
                print(f"  期望: {case['expected']}, 实际: {case['actual']}")
        
        return len(failed_cases) == 0
    
    def test_batch_semantic_matching(self):
        """测试批量语义匹配功能"""
        
        template_titles = [
            "流程1(改成具体的流程名字)",
            "子模块1/类1/主题1", 
            "模块2安全设计",
            "XX功能实现",
            "扩展模块(根据需要可自行添加)"
        ]
        
        target_titles = [
            "用户注册流程",
            "数据处理模块",
            "用户管理子模块", 
            "支付功能实现",
            "消息推送扩展模块"
        ]
        
        print("\n\n" + "=" * 80)
        print("批量语义匹配测试")
        print("=" * 80)
        
        print("\n模板标题:")
        for i, title in enumerate(template_titles, 1):
            print(f"T{i}: {title}")
        
        print("\n目标标题:")
        for i, title in enumerate(target_titles, 1):
            print(f"G{i}: {title}")
        
        try:
            start_time = time.time()
            
            # 创建批量请求
            request = BatchSemanticRequest(
                template_titles=template_titles,
                target_titles=target_titles,
                context_info="测试泛化标题优化效果"
            )
            
            # 执行批量匹配
            response = self.semantic_matcher.batch_semantic_match(request)
            
            execution_time = time.time() - start_time
            self.stats.api_calls += response.api_calls_count
            
            print(f"\n批量匹配完成!")
            print(f"执行时间: {execution_time:.2f}秒")
            print(f"API调用次数: {response.api_calls_count}")
            
            # 验证结果
            success = self._verify_batch_results(
                response.similarity_matrix, 
                response.reasoning_matrix,
                template_titles,
                target_titles
            )
            
            # 记录测试结果
            test_result = TestResult(
                passed=success,
                actual_result=f"相似度矩阵 {len(response.similarity_matrix)}x{len(response.similarity_matrix[0]) if response.similarity_matrix else 0}",
                expected_result="合理的泛化标题高分匹配",
                reasoning=f"API调用: {response.api_calls_count}, 处理时间: {response.processing_time:.2f}s",
                execution_time=execution_time
            )
            self.stats.add_result(test_result)
            
            return success
            
        except Exception as e:
            logger.error(f"批量语义匹配测试失败: {e}")
            
            test_result = TestResult(
                passed=False,
                actual_result=f"错误: {str(e)}",
                expected_result="成功完成批量匹配",
                reasoning=f"执行异常: {e}",
                execution_time=time.time() - start_time
            )
            self.stats.add_result(test_result)
            
            return False
    
    def _verify_batch_results(self, similarity_matrix: List[List[float]], 
                            reasoning_matrix: List[List[str]],
                            template_titles: List[str],
                            target_titles: List[str]) -> bool:
        """验证批量匹配结果"""
        
        if not similarity_matrix or not similarity_matrix[0]:
            print("❌ 相似度矩阵为空")
            return False
        
        print(f"\n相似度矩阵 ({len(similarity_matrix)}x{len(similarity_matrix[0])}):")
        print("   ", end="")
        for j in range(len(target_titles)):
            print(f"G{j+1:2}", end="  ")
        print()
        
        # 定义预期的高分匹配对 (template_index, target_index)
        expected_matches = [
            (0, 0),  # T1: 流程1(改成具体的流程名字) -> G1: 用户注册流程
            (1, 2),  # T2: 子模块1/类1/主题1 -> G3: 用户管理子模块
            (2, 1),  # T3: 模块2安全设计 -> G2: 数据处理模块 (或其他模块相关)
            (3, 3),  # T4: XX功能实现 -> G4: 支付功能实现
            (4, 4),  # T5: 扩展模块(根据需要可自行添加) -> G5: 消息推送扩展模块
        ]
        
        high_score_count = 0
        total_expected_matches = len(expected_matches)
        
        for i, row in enumerate(similarity_matrix):
            print(f"T{i+1:2}", end=" ")
            for j, score in enumerate(row):
                print(f"{score:4.2f}", end=" ")
                
                # 检查是否为预期的匹配对
                if (i, j) in expected_matches:
                    if score >= 0.8:  # 预期匹配对应该获得高分
                        high_score_count += 1
                        print("✓", end="")
                    else:
                        print("✗", end="")
                else:
                    # 对于非预期匹配，检查是否错误地给了高分
                    if score >= 0.8:
                        print("!", end="")  # 意外的高分
                    else:
                        print(" ", end="")
            print(f"  ({template_titles[i]})")
        
        print(f"\n预期匹配对验证:")
        for i, (t_idx, g_idx) in enumerate(expected_matches, 1):
            score = similarity_matrix[t_idx][g_idx]
            template = template_titles[t_idx]
            target = target_titles[g_idx]
            status = "✓" if score >= 0.8 else "✗"
            print(f"  {i}. T{t_idx+1} -> G{g_idx+1}: {score:.2f} {status}")
            print(f"     {template} -> {target}")
        
        print(f"\n泛化标题高分匹配统计:")
        print(f"预期匹配数量: {total_expected_matches}")
        print(f"实际高分匹配: {high_score_count}")
        print(f"匹配成功率: {(high_score_count/total_expected_matches*100):.1f}%")
        
        # 验证标准：至少80%的预期匹配应该获得高分
        success = (high_score_count / total_expected_matches >= 0.8) if total_expected_matches > 0 else True
        
        status = "✅ 通过" if success else "❌ 失败"
        print(f"验证结果: {status}")
        
        return success
    
    def _is_generic_title(self, title: str) -> bool:
        """判断是否为泛化标题"""
        generic_indicators = [
            "(",  # 括号说明
            "/",  # 斜杠选择
            "XX", "某某",  # 占位符
            "可自行", "根据需要", "按需",  # 可扩展性描述
            "模块1", "模块2", "组件A", "组件B", "系统X", "流程x"  # 编号变量
        ]
        
        return any(indicator in title for indicator in generic_indicators)
    
    def test_context_aware_matching(self):
        """测试上下文感知匹配功能"""
        
        print("\n\n" + "=" * 80)
        print("上下文感知匹配测试")
        print("=" * 80)
        
        # 创建模拟章节信息
        template_chapter = ChapterInfo(
            title="流程x(根据需要可自行添加章节)",
            level=2,
            content="流程相关的详细内容描述",
            images=[],
            position=2,
            parent_path="2.数据管理"
        )
        
        candidate_chapters = [
            ChapterInfo(title="用户注册流程", level=2, content="用户注册相关内容", images=[], position=2),
            ChapterInfo(title="数据备份流程", level=2, content="数据备份相关内容", images=[], position=3), 
            ChapterInfo(title="系统配置", level=2, content="系统配置相关内容", images=[], position=4),
            ChapterInfo(title="接口文档", level=3, content="接口文档相关内容", images=[], position=5)
        ]
        
        context_info = "检测到重编号模式: H2章节整体偏移+1"
        
        print(f"模板章节: {template_chapter.title} (H{template_chapter.level}, 位置{template_chapter.position})")
        print(f"上下文: {context_info}")
        print("\n候选章节:")
        for i, chapter in enumerate(candidate_chapters, 1):
            print(f"候选{i}: {chapter.title} (H{chapter.level}, 位置{chapter.position})")
        
        try:
            start_time = time.time()
            
            # 构建上下文感知匹配提示词
            prompt = PromptBuilder.build_context_aware_matching_prompt(
                template_chapter.title,
                template_chapter.level,
                template_chapter.position,
                candidate_chapters,
                context_info
            )
            
            # 调用LLM
            response = self.llm_client.chat(prompt)
            execution_time = time.time() - start_time
            self.stats.api_calls += 1
            
            print(f"\n上下文感知匹配完成!")
            print(f"执行时间: {execution_time:.2f}秒")
            print(f"\nLLM响应:")
            print("-" * 40)
            print(response)
            print("-" * 40)
            
            # 解析并验证结果
            best_match, best_score = self._parse_context_matching_result(response)
            
            # 验证：应该识别为泛化标题并给出合理匹配
            expected_high_score = 0.85  # 泛化标题应该获得高分
            success = best_score >= expected_high_score
            
            print(f"\n最佳匹配: {best_match}")
            print(f"匹配分数: {best_score:.2f}")
            print(f"验证结果: {'✅ 通过' if success else '❌ 失败'}")
            
            if not success:
                print(f"期望分数 >= {expected_high_score}, 实际分数: {best_score}")
            
            # 记录测试结果
            test_result = TestResult(
                passed=success,
                actual_result=f"最佳匹配: {best_match}, 分数: {best_score:.2f}",
                expected_result=f"泛化标题高分匹配 (>= {expected_high_score})",
                reasoning=response[:200] + "..." if len(response) > 200 else response,
                execution_time=execution_time
            )
            self.stats.add_result(test_result)
            
            return success
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"上下文感知匹配测试失败: {e}")
            
            test_result = TestResult(
                passed=False,
                actual_result=f"错误: {str(e)}",
                expected_result="成功完成上下文感知匹配",
                reasoning=f"执行异常: {e}",
                execution_time=execution_time
            )
            self.stats.add_result(test_result)
            
            return False
    
    def _parse_context_matching_result(self, response: str) -> Tuple[str, float]:
        """解析上下文匹配结果"""
        import re
        
        best_match = "未找到匹配"
        best_score = 0.0
        
        try:
            # 查找所有候选结果
            pattern = r'候选(\d+):\s*([\d.]+)\s*\|\s*原因：(.+)'
            matches = re.findall(pattern, response)
            
            for match in matches:
                candidate_num = int(match[0])
                score = float(match[1])
                reason = match[2]
                
                if score > best_score:
                    best_score = score
                    best_match = f"候选{candidate_num} (分数: {score}, 原因: {reason})"
        
        except Exception as e:
            logger.warning(f"解析上下文匹配结果失败: {e}")
        
        return best_match, best_score
    
    def test_edge_cases(self):
        """测试边界情况"""
        
        print("\n\n" + "=" * 80)
        print("边界情况测试")
        print("=" * 80)
        
        edge_cases = [
            {
                "name": "空字符串",
                "template": "",
                "target": "用户模块",
                "expected": "否"
            },
            {
                "name": "特殊字符",
                "template": "模块@#$%",
                "target": "用户模块",
                "expected": "否"
            },
            {
                "name": "超长标题",
                "template": "这是一个非常非常长的标题" * 10,
                "target": "用户模块",
                "expected": "否"
            },
            {
                "name": "数字标题",
                "template": "123456",
                "target": "654321",
                "expected": "否"
            },
            {
                "name": "混合语言",
                "template": "Module模块1(replace with specific)",
                "target": "User模块设计",
                "expected": "是"
            }
        ]
        
        edge_success = True
        
        for i, case in enumerate(edge_cases, 1):
            print(f"\n边界测试 {i}: {case['name']}")
            print(f"模板: '{case['template']}'")
            print(f"目标: '{case['target']}'")
            
            try:
                result = self.test_single_title_similarity(
                    case['template'], case['target'], case['expected']
                )
                
                self.stats.add_result(result)
                
                status = "✅ 通过" if result.passed else "❌ 失败"
                print(f"结果: {result.actual_result}")
                print(f"状态: {status}")
                
                if not result.passed:
                    edge_success = False
                    
            except Exception as e:
                print(f"❌ 执行异常: {e}")
                edge_success = False
        
        return edge_success
    
    def run_all_tests(self):
        """运行所有测试"""
        
        print("开始泛化标题优化效果验证...")
        print(f"测试环境: {sys.executable}")
        print(f"工作目录: {os.getcwd()}")
        print(f"LLM配置: {config.llm.model}")
        
        start_time = time.time()
        
        try:
            # 执行各项测试
            results = {}
            
            results['generic_matching'] = self.test_generic_title_matching()
            results['batch_matching'] = self.test_batch_semantic_matching()
            results['context_aware'] = self.test_context_aware_matching()
            results['edge_cases'] = self.test_edge_cases()
            
            total_time = time.time() - start_time
            
            # 打印测试统计
            self.stats.print_summary()
            
            # 打印详细结果
            print(f"\n{'='*80}")
            print("详细测试结果")
            print(f"{'='*80}")
            for test_name, success in results.items():
                status = "✅ 通过" if success else "❌ 失败"
                print(f"{test_name}: {status}")
            
            # 总体评价
            all_passed = all(results.values())
            overall_status = "✅ 全部通过" if all_passed else "❌ 部分失败"
            print(f"\n总体结果: {overall_status}")
            print(f"总耗时: {total_time:.2f}秒")
            
            # 优化效果评估
            self.print_optimization_assessment()
            
            return all_passed
            
        except Exception as e:
            logger.error(f"测试执行失败: {e}")
            return False
    
    def print_optimization_assessment(self):
        """打印优化效果评估"""
        
        print(f"\n{'='*80}")
        print("泛化标题优化效果评估")
        print(f"{'='*80}")
        
        pass_rate = self.stats.get_pass_rate()
        
        if pass_rate >= 90:
            assessment = "🌟 优秀"
            color = "优化效果显著，泛化标题识别准确率很高"
        elif pass_rate >= 80:
            assessment = "✅ 良好"
            color = "优化效果良好，大部分泛化标题能被正确识别"
        elif pass_rate >= 70:
            assessment = "⚠️  一般"
            color = "优化有一定效果，但仍有改进空间"
        else:
            assessment = "❌ 较差"
            color = "优化效果不明显，需要进一步调整提示词"
        
        print(f"整体评分: {assessment}")
        print(f"通过率: {pass_rate:.1f}%")
        print(f"评估: {color}")
        
        print(f"\n🎯 核心指标:")
        print(f"   ✓ 测试通过率: {pass_rate:.1f}%")
        print(f"   ✓ API调用效率: {self.stats.api_calls}次调用")
        print(f"   ✓ 平均响应时间: {self.stats.total_time/self.stats.total_tests:.2f}秒" if self.stats.total_tests > 0 else "   ✓ 平均响应时间: N/A")
        
        print(f"\n🔧 支持的泛化标题类型:")
        print(f"   ✓ 括号说明: 流程1(改成具体的流程名字)")
        print(f"   ✓ 斜杠选择: 子模块1/类1/主题1")
        print(f"   ✓ 编号变量: 模块1、模块X、流程x")
        print(f"   ✓ 占位符: XX模块、某某功能")
        print(f"   ✓ 可扩展性: 扩展功能(根据需要可自行添加)")
        
        if pass_rate < 80:
            print(f"\n💡 改进建议:")
            print(f"   • 检查提示词中的泛化特征识别规则")
            print(f"   • 调整相似度阈值设置")
            print(f"   • 增加更多泛化标题训练样例")
            print(f"   • 优化LLM模型参数配置")

def main():
    """主测试函数"""
    
    # 检查API配置
    if not config.llm.api_key:
        print("错误: 未配置LLM API密钥")
        print("请设置环境变量 DEEPSEEK_API_KEY")
        return False
    
    try:
        # 创建测试器并运行测试
        tester = GenericTitleOptimizationTester()
        success = tester.run_all_tests()
        
        # 返回测试结果
        return success
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
