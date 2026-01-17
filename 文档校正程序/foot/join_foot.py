import re

def reformat_markdown_citations(input_file, output_file):
    # 读取文件内容
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 解析文末的引用列表
    # 匹配格式: [数字]: URL "标题"
    # 例如: [18]: https://... "许纪霖简历-近代中国"
    ref_pattern = re.compile(r'^\[(\d+)\]:\s+.*?\s+"(.*)"$', re.MULTILINE)
    
    # 构建引用字典: { '18': '近代中国', ... }
    ref_map = {}
    for match in ref_pattern.finditer(content):
        ref_id = match.group(1)
        full_title = match.group(2)
        
        # 提取说明文字：采用文末说明中-符号分割开的最后一条
        # 如果标题中包含 '-'，取最后一个部分；如果不包含，则取整个标题
        short_title = full_title.split('-')[-1].strip()
        ref_map[ref_id] = short_title

    # 2. 定义替换函数
    def replace_citation_block(match):
        # match.group(0) 是匹配到的完整引用块，例如 "[[1]](url)[[2]](url)"
        
        # 在该块中查找所有的 [[ID]] 模式
        # 注意：这里假设引用格式严格为 [[数字]](URL)
        citations = re.findall(r'\[\[(\d+)\]\]\([^\)]+\)', match.group(0))
        
        formatted_list = []
        for ref_id in citations:
            # 获取对应的标题，如果未找到则标记为 Unknown
            title = ref_map.get(ref_id, f"Unknown_ID_{ref_id}")
            # 格式化为 [标题][ID]
            formatted_list.append(f"[{title}][{ref_id}]")
        
        # 将多个引用用 '、' 隔开，并用 '()' 包裹
        # 结果形式: ([标题1][1]、[标题2][2])
        return f"({'、'.join(formatted_list)})"

    # 3. 替换正文中的引用
    # 匹配连续的一个或多个引用块
    # 正则解释:
    # \[\[\d+\]\]   匹配 [[数字]]
    # \([^\)]+\)    匹配 (URL)，非贪婪匹配直到遇到 )
    # (?: ... )+    匹配连续出现的上述模式
    citation_block_pattern = re.compile(r'(?:\[\[\d+\]\]\([^\)]+\))+')
    
    new_content = citation_block_pattern.sub(replace_citation_block, content)

    # 写入处理后的内容
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"处理完成！文件已保存为: {output_file}")
    
    # 打印部分预览

    print("-" * 30)
    print("处理结果预览 (前500字符):")
    print(new_content[:500])
    print("-" * 30)

# 使用示例
# 请确保当前目录下存在 '许的情况.md' 文件
if __name__ == "__main__":
    input_filename = '/home/hh01/Documents/works/文档校正/许的情况.md'
    output_filename = '/home/hh01/Documents/works/文档校正/许的情况_process.md'
    
    try:
        reformat_markdown_citations(input_filename, output_filename)
    except FileNotFoundError:
        print(f"错误：找不到文件 '{input_filename}'。请确保文件在当前目录下。")
