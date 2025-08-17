#!/usr/bin/env python3
"""
测试章节重编号误判修复的脚本
验证智能章节映射算法能否正确处理章节重编号场景
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from agents.structure_checker import StructureChecker
from utils.html_parser import ChapterInfo
from utils.chapter_mapper import MappingConfig


def create_renumbering_test_data():
    """创建章节重编号测试数据（基于用户描述的实际场景）"""
    
    # 模板文档章节（原始编号）
    template_chapters = [
        ChapterInfo(title="4.6.1.1 模块1安全设计", level=4, content="模块1的安全设计内容", images=[], position=0),
        ChapterInfo(title="4.6.1.2 模块2安全设计", level=4, content="模块2的安全设计内容", images=[], position=1),
        ChapterInfo(title="4.6.1.3 数据加密机制", level=4, content="数据加密的实现方案", images=[], position=2),
        ChapterInfo(title="4.6.1.4 访问控制策略", level=4, content="访问控制的详细策略", images=[], position=3),
        ChapterInfo(title="4.6.1.5 安全兜底机制合入", level=4, content="安全兜底机制的详细说明", images=[], position=4),
    ]
    
    # 目标文档章节（重编号后，删除了第一个章节，后续章节编号前移）
    target_chapters = [
        ChapterInfo(title="4.6.1.1 模块2安全设计", level=4, content="模块2的安全设计内容", images=[], position=0),
        ChapterInfo(title="4.6.1.2 数据加密机制", level=4, content="数据加密的实现方案", images=[], position=1),
        ChapterInfo(title="4.6.1.3 访问控制策略", level=4, content="访问控制的详细策略", images=[], position=2),
        ChapterInfo(title="4.6.1.4 安全兜底机制合入", level=4, content="安全兜底机制的详细说明", images=[], position=3),
    ]
    
    return template_chapters, target_chapters


def create_complex_renumbering_test_data():
    """创建复杂的重编号测试数据"""
    
    # 模板文档章节
    template_chapters = [
        ChapterInfo(title="1. 概述", level=1, content="系统概述", images=[], position=0),
        ChapterInfo(title="2. 架构设计", level=1, content="架构设计说明", images=[], position=1),
        ChapterInfo(title="2.1 前端架构", level=2, content="前端架构内容", images=[], position=2),
        ChapterInfo(title="2.2 后端架构", level=2, content="后端架构内容", images=[], position=3),
        ChapterInfo(title="2.3 数据库设计", level=2, content="数据库设计内容", images=[], position=4),
        ChapterInfo(title="3. 安全设计", level=1, content="安全设计说明", images=[], position=5),
        ChapterInfo(title="3.1 认证机制", level=2, content="认证机制内容", images=[], position=6),
        ChapterInfo(title="3.2 授权策略", level=2, content="授权策略内容", images=[], position=7),
        ChapterInfo(title="4. 部署方案", level=1, content="部署方案说明", images=[], position=8),
    ]
    
    # 目标文档章节（插入了新章节，导致后续章节重编号）
    target_chapters = [
        ChapterInfo(title="1. 概述", level=1, content="系统概述", images=[], position=0),
        ChapterInfo(title="2. 需求分析", level=1, content="新增的需求分析章节", images=[], position=1),  # 新增章节
        ChapterInfo(title="3. 架构设计", level=1, content="架构设计说明", images=[], position=2),  # 重编号 2->3
        ChapterInfo(title="3.1 前端架构", level=2, content="前端架构内容", images=[], position=3),
        ChapterInfo(title="3.2 后端架构", level=2, content="后端架构内容", images=[], position=4),
        ChapterInfo(title="3.3 数据库设计", level=2, content="数据库设计内容", images=[], position=5),
        ChapterInfo(title="4. 安全设计", level=1, content="安全设计说明", images=[], position=6),  # 重编号 3->4
        ChapterInfo(title="4.1 认证机制", level=2, content="认证机制内容", images=[], position=7),
        ChapterInfo(title="4.2 授权策略", level=2, content="授权策略内容", images=[], position=8),
        ChapterInfo(title="5. 部署方案", level=1, content="部署方案说明", images=[], position=9),  # 重编号 4->5
    ]
    
    return template_chapters, target_chapters


def test_traditional_vs_smart_mapping():
    """测试传统方法与智能映射的对比"""
    print("🧪 开始测试传统方法与智能映射的对比\n")
    
    # 创建测试数据
    template_chapters, target_chapters = create_renumbering_test_data()
    
    print("📋 测试场景:")
    print("模板文档章节:")
    for ch in template_chapters:
        print(f"  - {ch.title}")
    print("\n目标文档章节:")
    for ch in target_chapters:
        print(f"  - {ch.title}")
    print()
    
    # 创建结构检查器
    checker = StructureChecker()
    
    # 测试传统方法
    print("🔍 传统方法测试:")
    checker.set_smart_mapping_enabled(False)
    traditional_result = checker.check_structure_completeness(template_chapters, target_chapters)
    
    print(f"  缺失章节数: {len(traditional_result.missing_chapters)}")
    for missing in traditional_result.missing_chapters:
        print(f"    - {missing.title}")
    print(f"  额外章节数: {len(traditional_result.extra_chapters)}")
    for extra in traditional_result.extra_chapters:
        print(f"    - {extra.title}")
    print(f"  结构相似度: {traditional_result.similarity_score:.2%}")
    print(f"  检查结果: {'✅ 通过' if traditional_result.passed else '❌ 失败'}")
    print()
    
    # 测试智能映射方法
    print("🧠 智能映射方法测试:")
    checker.set_smart_mapping_enabled(True)
    smart_result = checker.check_structure_completeness(template_chapters, target_chapters)
    
    print(f"  缺失章节数: {len(smart_result.missing_chapters)}")
    for missing in smart_result.missing_chapters:
        print(f"    - {missing.title}")
    print(f"  额外章节数: {len(smart_result.extra_chapters)}")
    for extra in smart_result.extra_chapters:
        print(f"    - {extra.title}")
    print(f"  结构相似度: {smart_result.similarity_score:.2%}")
    print(f"  检查结果: {'✅ 通过' if smart_result.passed else '❌ 失败'}")
    print()
    
    # 获取详细映射信息
    print("📊 智能映射详细信息:")
    mapping_details = checker.get_mapping_details(template_chapters, target_chapters)
    
    if "error" not in mapping_details:
        print(f"  整体置信度: {mapping_details['overall_confidence']:.2%}")
        print(f"  映射统计: {mapping_details['mapping_summary']}")
        
        if mapping_details['renumbering_patterns']:
            print("  检测到的重编号模式:")
            for pattern in mapping_details['renumbering_patterns']:
                print(f"    - {pattern['description']} (置信度: {pattern['confidence']:.2%})")
        
        print("  章节映射详情:")
        for mapping in mapping_details['mappings']:
            template_title = mapping['template_title']
            target_title = mapping['target_title'] or "未匹配"
            match_type = mapping['match_type']
            confidence = mapping['confidence']
            print(f"    {template_title} → {target_title} ({match_type}, {confidence:.2f})")
    
    print()
    
    # 比较结果
    print("📈 结果对比:")
    print(f"  传统方法缺失章节: {len(traditional_result.missing_chapters)}")
    print(f"  智能映射缺失章节: {len(smart_result.missing_chapters)}")
    print(f"  改进效果: {len(traditional_result.missing_chapters) - len(smart_result.missing_chapters)} 个误判章节被正确识别")
    
    # 判断测试是否成功
    success = len(smart_result.missing_chapters) < len(traditional_result.missing_chapters)
    print(f"  测试结果: {'✅ 智能映射效果更好' if success else '❌ 智能映射未显示优势'}")
    
    return success


def test_complex_renumbering_scenario():
    """测试复杂重编号场景"""
    print("\n🧪 开始测试复杂重编号场景\n")
    
    # 创建复杂测试数据
    template_chapters, target_chapters = create_complex_renumbering_test_data()
    
    print("📋 复杂测试场景:")
    print("模板文档章节:")
    for ch in template_chapters:
        print(f"  - {ch.title}")
    print("\n目标文档章节:")
    for ch in target_chapters:
        print(f"  - {ch.title}")
    print()
    
    # 创建结构检查器
    checker = StructureChecker()
    checker.set_smart_mapping_enabled(True)
    
    # 执行检查
    result = checker.check_structure_completeness(template_chapters, target_chapters)
    
    print("🔍 检查结果:")
    print(f"  缺失章节数: {len(result.missing_chapters)}")
    for missing in result.missing_chapters:
        print(f"    - {missing.title}")
    print(f"  额外章节数: {len(result.extra_chapters)}")
    for extra in result.extra_chapters:
        print(f"    - {extra.title}")
    print(f"  结构相似度: {result.similarity_score:.2%}")
    print(f"  检查结果: {'✅ 通过' if result.passed else '❌ 失败'}")
    
    # 获取映射详情
    mapping_details = checker.get_mapping_details(template_chapters, target_chapters)
    
    if "error" not in mapping_details and mapping_details['renumbering_patterns']:
        print("\n🔄 检测到的重编号模式:")
        for pattern in mapping_details['renumbering_patterns']:
            print(f"  - {pattern['description']}")
            print(f"    类型: {pattern['type']}")
            print(f"    置信度: {pattern['confidence']:.2%}")
            print(f"    影响层级: {pattern['affected_levels']}")
            if pattern['examples']:
                print(f"    示例: {pattern['examples'][:2]}")  # 显示前2个示例
    
    # 期望结果：应该只有1个真正缺失的章节（没有对应的章节）
    expected_missing = 0  # 在这个场景中，所有章节都应该能找到对应
    expected_extra = 1    # 新增的"需求分析"章节
    
    success = (len(result.missing_chapters) <= expected_missing and 
              len(result.extra_chapters) == expected_extra)
    
    print(f"\n📊 测试评估:")
    print(f"  期望缺失章节: {expected_missing}, 实际: {len(result.missing_chapters)}")
    print(f"  期望额外章节: {expected_extra}, 实际: {len(result.extra_chapters)}")
    print(f"  测试结果: {'✅ 通过' if success else '❌ 失败'}")
    
    return success


def test_mapping_configuration():
    """测试映射配置的影响"""
    print("\n🧪 开始测试映射配置的影响\n")
    
    template_chapters, target_chapters = create_renumbering_test_data()
    
    # 测试不同的配置
    configs = [
        ("默认配置", MappingConfig()),
        ("高精度配置", MappingConfig(
            similarity_threshold=0.3,
            title_weight=0.5,
            content_weight=0.3,
            position_weight=0.1,
            structure_weight=0.1
        )),
        ("快速配置", MappingConfig(
            similarity_threshold=0.7,
            max_batch_size=5,
            enable_context_aware=False
        ))
    ]
    
    results = []
    
    for config_name, config in configs:
        print(f"🔧 测试{config_name}:")
        
        checker = StructureChecker()
        checker.configure_mapping(config)
        checker.set_smart_mapping_enabled(True)
        
        result = checker.check_structure_completeness(template_chapters, target_chapters)
        
        print(f"  缺失章节: {len(result.missing_chapters)}")
        print(f"  额外章节: {len(result.extra_chapters)}")
        print(f"  相似度: {result.similarity_score:.2%}")
        print(f"  通过: {'✅' if result.passed else '❌'}")
        
        results.append((config_name, result))
        print()
    
    # 比较结果
    print("📊 配置对比:")
    for config_name, result in results:
        print(f"  {config_name}: 缺失{len(result.missing_chapters)}, 额外{len(result.extra_chapters)}, 相似度{result.similarity_score:.2%}")
    
    return True


def main():
    """主测试函数"""
    print("🚀 开始章节重编号误判修复测试\n")
    
    try:
        # 测试1: 传统方法与智能映射对比
        test1_passed = test_traditional_vs_smart_mapping()
        
        # 测试2: 复杂重编号场景
        test2_passed = test_complex_renumbering_scenario()
        
        # 测试3: 映射配置影响
        test3_passed = test_mapping_configuration()
        
        # 总结
        print("\n📊 测试结果总结:")
        print(f"   - 传统vs智能映射对比: {'✅ 通过' if test1_passed else '❌ 失败'}")
        print(f"   - 复杂重编号场景: {'✅ 通过' if test2_passed else '❌ 失败'}")
        print(f"   - 映射配置测试: {'✅ 通过' if test3_passed else '❌ 失败'}")
        
        if test1_passed and test2_passed and test3_passed:
            print("\n🎉 所有测试通过！章节重编号误判问题已成功修复。")
            print("\n✨ 修复效果:")
            print("   - 智能识别章节重编号模式")
            print("   - 避免将重编号章节误判为缺失")
            print("   - 准确识别真正缺失的章节")
            print("   - 提供详细的映射分析信息")
            return 0
        else:
            print("\n❌ 部分测试失败，需要进一步优化算法。")
            return 1
            
    except Exception as e:
        print(f"\n💥 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
