#!/usr/bin/env python3
"""
脚注处理程序使用示例
演示各种配置和使用方式
"""
import os
os.chdir(os.path.dirname(__file__))

from footnote_processor import FootnoteProcessor, FootnoteConfig


def example1_basic_usage():
    """示例1：基本使用"""
    print("=" * 60)
    print("示例1：基本使用")
    print("=" * 60)
    
    # 使用默认配置
    processor = FootnoteProcessor()
    
    # 处理文档
    result = processor.process_document('test_document.txt', 'output1.txt')
    print("处理完成，输出文件：output1.txt")
    print("\n处理后的部分内容预览：")
    print(result[:500] + "...")


def example2_custom_config():
    """示例2：自定义配置"""
    print("\n" + "=" * 60)
    print("示例2：自定义配置")
    print("=" * 60)
    
    # 创建自定义配置
    config = FootnoteConfig(
        section_delimiter="########",
        text_footnote_pattern=r'【(\d+)】',  # 使用中文方括号
        footnote_footnote_pattern=r'【(\d+)】',
        output_footnote_format="〔注：{content}〕"  # 自定义输出格式
    )
    
    # 创建测试文档
    test_content = """########第一章
这是正文内容，包含脚注【1】。

另一段文字，又有脚注【2】。

【1】这是第一个脚注的内容。
【2】这是第二个脚注的内容。

########第二章
第二章的内容。
"""
    
    with open('test_custom.txt', 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    # 处理文档
    processor = FootnoteProcessor(config)
    result = processor.process_document('test_custom.txt', 'output2.txt')
    print("处理完成，输出文件：output2.txt")
    # print("\n处理结果：")
    # print(result)


def example3_error_handling():
    """示例3：错误处理和验证"""
    print("\n" + "=" * 60)
    print("示例3：错误处理和验证")
    print("=" * 60)
    
    # 创建包含错误的测试文档
    error_content = """========测试部分
正文包含脚注[[1]]和[[3]]，但缺少[[2]]。

[[1]]第一个脚注。
[[3]]第三个脚注，缺少第二个。
"""
    
    with open('test_error.txt', 'w', encoding='utf-8') as f:
        f.write(error_content)
    
    # 处理文档（将显示错误）
    processor = FootnoteProcessor()
    result = processor.process_document('test_error.txt', 'output_error.txt')
    print("\n由于验证失败，将保持原文档内容不变。")


def example4_complex_footnotes():
    """示例4：处理复杂脚注（多个符号共用内容、换行等）"""
    print("\n" + "=" * 60)
    print("示例4：处理复杂脚注")
    print("=" * 60)
    
    complex_content = """========复杂示例
这是第一个脚注[[1]]，这是第二个[[2]]和第三个[[3]]。

还有第四个脚注[[4]]包含多行内容。

[[1]]简单脚注。
[[2]] [[3]]这两个脚注共用相同的内容。
[[4]]这是第四个脚注的第一行
这是第二行
这是第三行
"""
    
    with open('test_complex.txt', 'w', encoding='utf-8') as f:
        f.write(complex_content)
    
    # 处理文档
    config = FootnoteConfig(
        section_delimiter="========",
        text_footnote_pattern=r'\[\[(\d+)\]\]',  # 使用中文方括号
        footnote_footnote_pattern=r'\[\[(\d+)\]\]',
        output_footnote_format="【注：{content}】"  # 自定义输出格式
    )
    processor = FootnoteProcessor(config)
    result = processor.process_document('test_complex.txt', 'output_complex.txt')
    print("处理完成，输出文件：output_complex.txt")
    # print("\n处理结果：")
    # print(result)


def example5_from_config_file():
    """示例5：从配置文件加载配置"""
    print("\n" + "=" * 60)
    print("示例5：从配置文件加载配置")
    print("=" * 60)
    
    # 使用命令行方式（实际使用时）
    print("命令行使用示例：")
    print("python footnote_processor.py test_document.txt -o output.txt -c config.json")
    print("\n或者在Python代码中：")
    
    import json
    
    # 加载配置文件
    with open('config.json', 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    config = FootnoteConfig(**config_data)
    processor = FootnoteProcessor(config)
    
    # 处理文档
    result = processor.process_document('test_document.txt', 'output5.txt')
    print("处理完成，输出文件：output5.txt")


def example6_different_bracket_styles():
    """示例6：支持不同的括号样式"""
    print("\n" + "=" * 60)
    print("示例6：不同的括号样式")
    print("=" * 60)
    
    # 示例：使用花括号
    config1 = FootnoteConfig(
        text_footnote_pattern=r'\{\{(\d+)\}\}',
        footnote_footnote_pattern=r'\{\{(\d+)\}\}',
        output_footnote_format="[注{content}]"
    )
    
    # 示例：使用圆括号
    config2 = FootnoteConfig(
        text_footnote_pattern=r'\(\((\d+)\)\)',
        footnote_footnote_pattern=r'\(\((\d+)\)\)',
        output_footnote_format="（注释：{content}）"
    )
    
    print("支持的括号样式示例：")
    print("1. 双方括号：[[1]]")
    print("2. 中文方括号：【1】")
    print("3. 花括号：{{1}}")
    print("4. 圆括号：((1))")
    print("等等，可通过正则表达式自定义")


if __name__ == '__main__':
    # 运行所有示例
    # example1_basic_usage()
    example2_custom_config()
    example3_error_handling()
    example4_complex_footnotes()
    # example5_from_config_file()
    example6_different_bracket_styles()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)
