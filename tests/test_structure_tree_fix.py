#!/usr/bin/env python3
"""
测试结构树修复的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.structure_checker import StructureChecker, StructureNode
from agents.report_generator import ReportGenerator
from agents.content_checker import ContentCheckResult, ChapterCheckResult
from utils.html_parser import ChapterInfo


def create_test_chapters():
    """创建测试章节数据"""
    # 模板文档章节
    template_chapters = [
        ChapterInfo(title="概述", level=1, content="概述内容", images=[], position=0),
        ChapterInfo(title="系统架构", level=1, content="架构内容", images=[], position=1),
        ChapterInfo(title="前端设计", level=2, content="前端内容", images=[], position=2),
        ChapterInfo(title="后端设计", level=2, content="后端内容", images=[], position=3),
        ChapterInfo(title="数据库设计", level=1, content="数据库内容", images=[], position=4),
        ChapterInfo(title="部署指南", level=1, content="部署内容", images=[], position=5),
    ]
    
    # 目标文档章节（缺少"后端设计"，多了"测试方案"）
    target_chapters = [
        ChapterInfo(title="概述", level=1, content="概述内容", images=[], position=0),
        ChapterInfo(title="系统架构", level=1, content="架构内容", images=[], position=1),
        ChapterInfo(title="前端设计", level=2, content="前端内容", images=[], position=2),
        ChapterInfo(title="数据库设计", level=1, content="数据库内容", images=[], position=3),
        ChapterInfo(title="测试方案", level=1, content="测试内容", images=[], position=4),
        ChapterInfo(title="部署指南", level=1, content="部署内容", images=[], position=5),
    ]
    
    return template_chapters, target_chapters


def create_mock_content_result():
    """创建模拟的内容检查结果"""
    return ContentCheckResult(
        passed=True,
        total_violations=0,
        chapters=[],
        rules_summary={},
        severity_summary={}
    )


def test_structure_tree_conversion():
    """测试结构树转换功能"""
    print("🧪 开始测试结构树转换功能...")
    
    # 创建测试数据
    template_chapters, target_chapters = create_test_chapters()
    
    # 执行结构检查（禁用LLM调用）
    checker = StructureChecker()
    # 临时替换LLM相似度检查方法，避免认证问题
    original_llm_check = checker._llm_similarity_check
    checker._llm_similarity_check = lambda title1, title2: False
    
    structure_result = checker.check_structure_completeness(template_chapters, target_chapters)
    
    # 恢复原方法
    checker._llm_similarity_check = original_llm_check
    
    print(f"✅ 结构检查完成:")
    print(f"   - 缺失章节: {len(structure_result.missing_chapters)}")
    print(f"   - 额外章节: {len(structure_result.extra_chapters)}")
    print(f"   - 结构相似度: {structure_result.similarity_score:.2%}")
    
    # 测试报告生成器的结构树转换
    generator = ReportGenerator()
    
    try:
        document_tree, template_tree = generator._convert_structure_trees(
            structure_result.target_structure,
            structure_result.template_structure,
            structure_result.missing_chapters,
            structure_result.extra_chapters
        )
        
        print(f"✅ 结构树转换成功:")
        print(f"   - 目标文档节点数: {len(document_tree)}")
        print(f"   - 模板文档节点数: {len(template_tree)}")
        
        # 打印目标文档结构树
        print("\n📄 目标文档结构树:")
        for node in document_tree:
            indent = "  " * node.get('depth', 0)
            status_icon = {"matched": "✅", "extra": "➕", "missing": "❌"}.get(node['status'], "❓")
            print(f"{indent}{status_icon} H{node['level']} {node['title']} ({node['status']})")
        
        # 打印模板文档结构树
        print("\n📋 模板文档结构树:")
        for node in template_tree:
            indent = "  " * node.get('depth', 0)
            status_icon = {"matched": "✅", "extra": "➕", "missing": "❌"}.get(node['status'], "❓")
            print(f"{indent}{status_icon} H{node['level']} {node['title']} ({node['status']})")
        
        # 验证数据格式
        for tree_name, tree_data in [("目标文档", document_tree), ("模板文档", template_tree)]:
            for i, node in enumerate(tree_data):
                required_keys = ['title', 'level', 'status', 'depth']
                for key in required_keys:
                    if key not in node:
                        print(f"❌ {tree_name}节点 {i} 缺少必需字段: {key}")
                        return False
                
                if node['status'] not in ['matched', 'missing', 'extra']:
                    print(f"❌ {tree_name}节点 {i} 状态值无效: {node['status']}")
                    return False
        
        print("✅ 数据格式验证通过")
        return True
        
    except Exception as e:
        print(f"❌ 结构树转换失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_generation():
    """测试完整的报告生成"""
    print("\n🧪 开始测试完整报告生成...")
    
    try:
        # 创建测试数据
        template_chapters, target_chapters = create_test_chapters()
        
        # 执行结构检查（禁用LLM调用）
        checker = StructureChecker()
        # 临时替换LLM相似度检查方法，避免认证问题
        original_llm_check = checker._llm_similarity_check
        checker._llm_similarity_check = lambda title1, title2: False
        
        structure_result = checker.check_structure_completeness(template_chapters, target_chapters)
        
        # 恢复原方法
        checker._llm_similarity_check = original_llm_check
        
        # 创建模拟内容检查结果
        content_result = create_mock_content_result()
        
        # 创建文档信息
        template_doc_info = {
            'url': 'https://example.com/template',
            'chapters': template_chapters,
            'meta_info': {'title': '模板文档'}
        }
        
        target_doc_info = {
            'url': 'https://example.com/target',
            'chapters': target_chapters,
            'meta_info': {'title': '目标文档'}
        }
        
        # 生成报告
        generator = ReportGenerator()
        report_path = generator.generate_report(
            structure_result=structure_result,
            content_result=content_result,
            template_doc_info=template_doc_info,
            target_doc_info=target_doc_info
        )
        
        print(f"✅ 报告生成成功: {report_path}")
        
        # 检查报告文件是否存在
        if os.path.exists(report_path):
            file_size = os.path.getsize(report_path)
            print(f"✅ 报告文件大小: {file_size} 字节")
            
            # 检查HTML内容是否包含结构树数据
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含结构树节点
            has_tree_nodes = 'tree-node matched' in content or 'tree-node missing' in content or 'tree-node extra' in content
            has_tree_structure = '📄 被检测文档结构' in content and '📋 模板文档结构' in content
            
            if has_tree_nodes and has_tree_structure:
                print("✅ 报告包含结构树数据")
            else:
                print("❌ 报告缺少结构树数据")
                return False
            
            if '暂无结构数据' not in content:
                print("✅ 报告不包含'暂无结构数据'提示")
            else:
                print("⚠️  报告仍显示'暂无结构数据'")
                return False
            
            return True
        else:
            print(f"❌ 报告文件不存在: {report_path}")
            return False
            
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 开始结构树修复测试\n")
    
    # 测试结构树转换
    test1_passed = test_structure_tree_conversion()
    
    # 测试完整报告生成
    test2_passed = test_report_generation()
    
    # 总结
    print(f"\n📊 测试结果总结:")
    print(f"   - 结构树转换测试: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"   - 报告生成测试: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！结构树修复成功。")
        return 0
    else:
        print("\n❌ 部分测试失败，需要进一步检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
