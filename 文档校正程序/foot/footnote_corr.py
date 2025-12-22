import re
from typing import List, Tuple, Dict

def process_document(input_text: str) -> Tuple[str, List[int]]:
    """
    处理文档，格式化脚注并检查脚注序号的正确性
    
    Args:
        input_text: 输入的文档文本
    
    Returns:
        处理后的文档文本和有问题的页码列表
    """
    lines = input_text.split('\n')
    output_lines = []
    problem_pages = []
    
    current_page = None
    page_footnotes = {}  # 存储每页的脚注
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是页码行
        if line.startswith('========'):
            # 处理上一页的脚注（如果有）
            if current_page is not None and current_page in page_footnotes:
                sorted_footnotes, has_problem = process_page_footnotes(page_footnotes[current_page])
                if has_problem:
                    problem_pages.append(current_page)
                output_lines.extend(sorted_footnotes)
            
            # 更新当前页码
            try:
                current_page = int(line[8:])
            except:
                current_page = None
            
            output_lines.append(line)
            page_footnotes = {}
        
        # 检查是否是空行
        elif line.strip() == '':
            output_lines.append(line)
        
        # 检查是否是脚注行
        elif '[[' in line and ']]' in line:
            # 提取所有脚注
            footnotes = extract_footnotes(line)
            
            if footnotes:
                # 存储脚注以便后续排序
                if current_page not in page_footnotes:
                    page_footnotes[current_page] = []
                page_footnotes[current_page].extend(footnotes)
            else:
                # 不是标准脚注格式，不处理
                output_lines.append(line)
        
        # 其他行不处理
        else:
            output_lines.append(line)
        
        i += 1
    
    # 处理最后一页的脚注（如果有）
    if current_page is not None and current_page in page_footnotes:
        sorted_footnotes, has_problem = process_page_footnotes(page_footnotes[current_page])
        if has_problem:
            problem_pages.append(current_page)
        output_lines.extend(sorted_footnotes)
    
    return '\n'.join(output_lines), problem_pages

def extract_footnotes(line: str) -> List[Tuple[int, str]]:
    """
    从一行中提取所有脚注
    
    Args:
        line: 输入行
    
    Returns:
        脚注列表，每个元素是(脚注编号, 完整脚注内容)
    """
    footnotes = []
    
    # 使用正则表达式匹配所有脚注
    pattern = r'\[\[(\d+)\]\]'
    matches = list(re.finditer(pattern, line))
    
    if not matches:
        return footnotes
    
    # 检查第一个脚注是否在行首
    if matches[0].start() != 0:
        return []  # 不是以脚注开头的行，不处理
    
    # 处理每个脚注
    i = 0
    while i < len(matches):
        match = matches[i]
        footnote_num = int(match.group(1))
        start_pos = match.start()
        
        # 找到当前脚注组的结束位置（连续的脚注标记视为一组）
        j = i
        while j < len(matches) - 1:
            # 检查下一个脚注是否紧邻（只有空格）
            between_content = line[matches[j].end():matches[j+1].start()]
            if between_content.strip() == '':
                j += 1
            else:
                break
        
        # 现在 matches[i] 到 matches[j] 是一组连续的脚注
        group_end = matches[j].end()
        
        # 确定这组脚注的内容结束位置
        if j < len(matches) - 1:
            # 还有后续脚注，内容到下一个脚注开始
            content_end = matches[j + 1].start()
        else:
            # 最后一组脚注，内容到行尾
            content_end = len(line)
        
        # 获取这组脚注的共享内容
        shared_content = line[group_end:content_end].rstrip()
        
        # 为这组中的每个脚注创建完整行
        for k in range(i, j + 1):
            fn_num = int(matches[k].group(1))
            footnote_full = f"[[{fn_num}]]{shared_content}"
            footnotes.append((fn_num, footnote_full))
        
        # 移动到下一组
        i = j + 1
    
    return footnotes

def process_page_footnotes(footnotes: List[Tuple[int, str]]) -> Tuple[List[str], bool]:
    """
    处理一页的脚注：排序并检查序号连续性
    
    Args:
        footnotes: 脚注列表
    
    Returns:
        排序后的脚注行列表和是否有序号问题的标志
    """
    if not footnotes:
        return [], False
    
    # 按脚注编号排序
    footnotes.sort(key=lambda x: x[0])
    
    # 检查序号连续性
    has_problem = False
    expected_num = 1
    footnote_nums = [fn[0] for fn in footnotes]
    
    # 检查是否从1开始且连续
    for num in footnote_nums:
        if num != expected_num:
            has_problem = True
            break
        expected_num += 1
    
    # 检查是否有重复
    if len(footnote_nums) != len(set(footnote_nums)):
        has_problem = True
    
    # 生成输出行
    output_lines = []
    for num, content in footnotes:
        output_lines.append(content)
    
    return output_lines, has_problem

def process_file(input_file: str, output_file: str):
    """
    处理文件
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
    """
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()
    
    # 处理文档
    processed_text, problem_pages = process_document(input_text)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(processed_text)
    
    # 打印有问题的页码
    if problem_pages:
        print(f"以下页码的脚注序号有问题：{problem_pages}")
    else:
        print("所有页面的脚注序号都正确")
    
    print(f"处理完成，结果已保存到 {output_file}")

# 示例使用
if __name__ == "__main__":
    # 测试用例
    with open('/home/hh01/Downloads/works/文档校正/jbzqh-zs.md','r',encoding='utf-8') as f:
        test_input = f.readlines()
    test_input = ''.join(test_input)
    
    # 处理测试输入
    result, problems = process_document(test_input)
    # print("处理结果：")
    # print(result)
    print("\n" + "="*50)
    if problems:
        print(f"有问题的页码：{problems}")
    else:
        print("所有页面的脚注序号都正确")

    # 1. 多(3-X)个月N元的利息
    # 完整的利息
    
    # 如果需要处理文件，可以使用：
    # process_file('input.md', 'output.md')