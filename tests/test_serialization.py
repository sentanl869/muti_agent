"""
测试序列化问题的修复
"""

import ormsgpack
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.structure_checker import StructureCheckResult, StructureNode, MissingChapter
from utils.html_parser import ChapterInfo, ImageInfo

def test_structure_node_serialization():
    """测试 StructureNode 序列化"""
    print("测试 StructureNode 序列化...")
    
    # 创建测试节点
    child1 = StructureNode(
        title="子章节1",
        level=2,
        children=[],
        path="父章节",
        position=0
    )
    
    child2 = StructureNode(
        title="子章节2", 
        level=2,
        children=[],
        path="父章节",
        position=1
    )
    
    parent = StructureNode(
        title="父章节",
        level=1,
        children=[child1, child2],
        path="",
        position=0
    )
    
    try:
        # 尝试序列化
        serialized = ormsgpack.packb(parent)
        print("✅ StructureNode 序列化成功")
        
        # 尝试反序列化
        deserialized = ormsgpack.unpackb(serialized)
        print("✅ StructureNode 反序列化成功")
        
        return True
    except Exception as e:
        print(f"❌ StructureNode 序列化失败: {e}")
        return False

def test_chapter_info_serialization():
    """测试 ChapterInfo 序列化"""
    print("测试 ChapterInfo 序列化...")
    
    # 创建测试图像
    image = ImageInfo(
        url="https://example.com/image.jpg",
        local_path="/tmp/image.jpg",
        alt_text="测试图像",
        title="图像标题",
        context="图像上下文",
        description="图像描述",
        position="位置1"
    )
    
    # 创建测试章节
    chapter = ChapterInfo(
        title="测试章节",
        level=1,
        content="这是测试内容",
        images=[image],
        position=0,
        html_id="test-chapter",
        parent_path=""
    )
    
    try:
        # 尝试序列化
        serialized = ormsgpack.packb(chapter)
        print("✅ ChapterInfo 序列化成功")
        
        # 尝试反序列化
        deserialized = ormsgpack.unpackb(serialized)
        print("✅ ChapterInfo 反序列化成功")
        
        return True
    except Exception as e:
        print(f"❌ ChapterInfo 序列化失败: {e}")
        return False

def test_structure_check_result_serialization():
    """测试 StructureCheckResult 序列化"""
    print("测试 StructureCheckResult 序列化...")
    
    # 创建测试数据
    template_structure = StructureNode(
        title="根节点",
        level=0,
        children=[],
        path="",
        position=0
    )
    
    target_structure = StructureNode(
        title="根节点",
        level=0,
        children=[],
        path="",
        position=0
    )
    
    missing_chapter = MissingChapter(
        title="缺失章节",
        level=1,
        expected_path="",
        parent_title="",
        position=0
    )
    
    image = ImageInfo(
        url="https://example.com/image.jpg",
        local_path="/tmp/image.jpg",
        alt_text="测试图像",
        title="图像标题",
        context="图像上下文",
        description="图像描述",
        position="位置1"
    )
    
    extra_chapter = ChapterInfo(
        title="额外章节",
        level=1,
        content="额外内容",
        images=[image],
        position=0,
        html_id="extra-chapter",
        parent_path=""
    )
    
    result = StructureCheckResult(
        passed=False,
        missing_chapters=[missing_chapter],
        extra_chapters=[extra_chapter],
        structure_issues=["测试问题"],
        template_structure=template_structure,
        target_structure=target_structure,
        similarity_score=0.8
    )
    
    try:
        # 尝试序列化
        serialized = ormsgpack.packb(result)
        print("✅ StructureCheckResult 序列化成功")
        
        # 尝试反序列化
        deserialized = ormsgpack.unpackb(serialized)
        print("✅ StructureCheckResult 反序列化成功")
        
        return True
    except Exception as e:
        print(f"❌ StructureCheckResult 序列化失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始序列化测试...")
    print("=" * 50)
    
    tests = [
        test_structure_node_serialization,
        test_chapter_info_serialization,
        test_structure_check_result_serialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 30)
    
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有序列化测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步修复")
        return False

if __name__ == "__main__":
    main()
