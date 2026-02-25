"""
测试 md_corr.py 的功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from md_corr import is_cjk, is_near_chinese, replace_quotes_smartly
from md_corr import protect_markdown, restore_markdown, process_text


def test_is_cjk():
    """测试CJK字符检测"""
    print("测试 is_cjk()...")
    
    # 测试汉字
    assert is_cjk('中') == True
    assert is_cjk('文') == True
    assert is_cjk('字') == True
    
    # 测试中文标点
    chs = r'在。，！？（）“”’‘【】——'
    for c in chs:
        if not is_cjk(c):
            print(c)
    assert is_cjk('。') == True
    assert is_cjk('，') == True
    assert is_cjk('！') == True
    assert is_cjk('？') == True
    assert is_cjk('（') == True
    assert is_cjk('）') == True
    assert is_cjk('“') == True
    assert is_cjk('”') == True
    
    # 测试英文字符
    assert is_cjk('a') == False
    assert is_cjk('A') == False
    assert is_cjk('1') == False
    assert is_cjk('.') == False
    assert is_cjk(',') == False
    
    print("✓ is_cjk() 测试通过")


def test_is_near_chinese():
    """测试附近中文字符检测"""
    print("\n测试 is_near_chinese()...")
    
    # 中文字符附近
    assert is_near_chinese("你好世界", 1) == True
    assert is_near_chinese("你好世界", 2) == True
    
    # 空格隔开的中文
    assert is_near_chinese("你好  世界", 3) == True
    
    # 纯英文
    assert is_near_chinese("hello world", 5) == False
    
    print("✓ is_near_chinese() 测试通过")


def test_replace_quotes_smartly():
    """测试引号转换"""
    print("\n测试 replace_quotes_smartly()...")
    
    # 中文附近的引号转换
    result = replace_quotes_smartly('"你好"')
    assert result == '“你好”', f"期望 '“你好”'，得到 '{result}'"
    
    result = replace_quotes_smartly("'世界'")
    assert result == "‘世界’", f"期望 '‘世界’'，得到 '{result}'"
    
    # 英文引号保持不变
    result = replace_quotes_smartly('"Hello World"')
    assert result == '"Hello World"', f"期望 '\"Hello World\"'，得到 '{result}'"
    
    result = replace_quotes_smartly("'English Text'")
    assert result == "'English Text'", f"期望 \"'English Text'\"，得到 '{result}'"
    
    print("✓ replace_quotes_smartly() 测试通过")


def test_protect_restore_markdown():
    """测试markdown保护和恢复"""
    print("\n测试 protect_markdown() 和 restore_markdown()...")
    
    # 测试图片
    text = "这是一张图片 ![图片说明](image.jpg) 结束"
    protected, parts = protect_markdown(text)
    result = restore_markdown(protected, parts)
    assert result == text, f"期望 '{text}'，得到 '{result}'"
    
    # 测试链接
    text = "这是一个链接 [点击这里](https://example.com) 结束"
    protected, parts = protect_markdown(text)
    result = restore_markdown(protected, parts)
    assert result == text, f"期望 '{text}'，得到 '{result}'"
    
    # 测试多个markdown
    text = "![图1](img1.jpg) 和 [链接](url) 和 ![图2](img2.jpg)"
    protected, parts = protect_markdown(text)
    result = restore_markdown(protected, parts)
    assert result == text, f"期望 '{text}'，得到 '{result}'"
    
    print("✓ markdown 保护与恢复测试通过")


def test_process_text_heading():
    """测试标题行空格保护"""
    print("\n测试标题行空格保护...")
    
    # 标题行应保留空格
    lines = ["# 标题 一 二 三\n"]
    result = process_text(lines, 0)
    assert "# 标题 一 二 三" in result, f"标题行空格被删除了: {result}"
    
    lines = ["## 二级 标题\n"]
    result = process_text(lines, 0)
    assert "## 二级 标题" in result, f"二级标题行空格被删除了: {result}"
    
    print("✓ 标题行空格保护测试通过")


def test_process_text_markdown():
    """测试markdown语法保护"""
    print("\n测试markdown语法保护...")
    
    # 图片语法不应被转换
    lines = ["看这张图片 ![图片描述](image.jpg) 很好看\n"]
    result = process_text(lines, 0)
    assert "![图片描述](image.jpg)" in result, f"图片语法被修改了: {result}"
    assert "!【图片描述】(image.jpg)" not in result, f"图片语法中的方括号被转换了"
    
    # 链接语法不应被转换
    lines = ["点击 [链接文字](https://example.com) 查看\n"]
    result = process_text(lines, 0)
    assert "[链接文字](https://example.com)" in result, f"链接语法被修改了: {result}"
    assert "【链接文字】(https://example.com)" not in result, f"链接语法中的方括号被转换了"
    
    print("✓ markdown语法保护测试通过")


def test_process_text_punctuation():
    """测试标点转换"""
    print("\n测试标点转换...")
    
    # 英文标点在中文旁边应转换
    lines = ["你好 ,  '世界'。\n", "测试成功!\n"]
    result = process_text(lines, 0)
    assert "你好，‘世界’" in result, f"逗号未转换: {result}"
    assert "测试成功！" in result, f"感叹号未转换: {result}"
    
    print("✓ 标点转换测试通过")


def test_process_text_merge_lines():
    """测试合并OCR断行功能"""
    print("\n测试合并OCR断行...")
    
    # 测试1: 两段断行合并
    lines = [
        "这是第一段文字\n",
        "\n",
        "这是第二段文字\n",
    ]
    result = process_text(lines, 0)
    assert "这是第一段文字这是第二段文字" in result, f"两段断行未合并: {result}"
    
    # 测试2: 连续多段断行合并（三段）
    lines = [
        "第一段\n",
        "\n",
        "第二段\n",
        "\n",
        "第三段\n",
    ]
    result = process_text(lines, 0)
    assert "第一段第二段第三段" in result, f"三段断行未完全合并: {result}"
    
    # 测试3: 不应该合并的情况 - 以句号结尾
    lines = [
        "这是完整的句子。\n",
        "\n",
        "这是另一句话\n",
    ]
    result = process_text(lines, 0)
    assert "这是完整的句子。\n\n这是另一句话" in result, f"不应该合并的行被合并了: {result}"
    
    # 测试4: 不应该合并的情况 - 标题行
    lines = [
        "# 标题\n",
        "\n",
        "正文内容\n",
    ]
    result = process_text(lines, 0)
    assert "# 标题\n\n正文内容" in result, f"标题行被合并了: {result}"
    
    # 测试5: 混合场景 - 有的应该合并，有的不应该
    lines = [
        "第一段未完结\n",
        "\n",
        "继续的内容\n",
        "\n",
        "第二段完结。\n",
        "\n",
        "第三段开始\n",
        "\n",
        "第三段继续\n",
    ]
    result = process_text(lines, 0)
    assert "第一段未完结继续的内容" in result, f"未完结段落未合并: {result}"
    assert "第二段完结。\n\n第三段开始第三段继续" in result, f"合并逻辑错误: {result}"
    
    # 测试6: 以逗号结尾的行应该合并
    # lines = [
    #     "他说：\n",
    #     "\n",
    #     "\"你好\"\n",
    # ]
    # result = process_text(lines, 0)
    # assert "他说：\"你好\"" in result or "他说：“你好”" in result, f"冒号后的断行未合并: {result}"
    
    print("✓ 合并OCR断行测试通过")


def test_process_text_integration():
    """综合测试"""
    print("\n运行综合测试...")
    
    lines = [
        "# 标题 有 空格\n",
        "\n",
        "这是一段文字,包含英文标点.\n",
        "\n",
        "看这张图片![示例图片](test.jpg)很好看!\n",
        "\n",
        "点击[这里](https://example.com)访问链接.\n",
    ]
    
    result = process_text(lines, 0)
    
    # 检查标题空格保留
    assert "# 标题 有 空格" in result, "标题空格未保留"
    
    # 检查标点转换
    assert "，" in result, "逗号未转换"
    assert "。" in result, "句号未转换"
    assert "！" in result, "感叹号未转换"
    
    # 检查markdown保护
    assert "![示例图片](test.jpg)" in result, "图片语法未保护"
    assert "[这里](https://example.com)" in result, "链接语法未保护"
    
    print("✓ 综合测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试 md_corr.py")
    print("=" * 60)
    
    try:
        test_is_cjk()
        test_is_near_chinese()
        test_replace_quotes_smartly()
        test_protect_restore_markdown()
        test_process_text_heading()
        test_process_text_markdown()
        test_process_text_punctuation()
        test_process_text_merge_lines()  # 新增：测试合并行功能
        test_process_text_integration()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
