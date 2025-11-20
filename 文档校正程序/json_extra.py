from enum import Enum
import json
import re
import os
import requests
from urllib.parse import urlparse
from typing import Optional, Callable

def fliter_box_width(blocks, btype):
    if btype=='title': return True
    if 'bbox' not in blocks:
        return False
    x0,_,x1,_ = blocks['bbox']
    if abs(x1-x0)<130 and (x1<170 or x0>230):
        return False
    return True

def fliter_box_top(blocks, btype):
    if 'bbox' not in blocks:
        return False
    y1 = blocks['bbox'][3]
    if y1<120: return False
    return True

def get_text_from_block(block,btype, fliter_fun:Optional[Callable] = None):
    """从一个块（block）中提取并拼接所有文本内容。"""
    full_text = []
    if 'lines' in block:
        fres = True if fliter_fun is None else fliter_box_top(block,btype)
        if fres:
            for line in block.get('lines', []):
                line_text = []
                if 'spans' in line:
                    for span in line.get('spans', []):
                        if span.get('type') in ('text','inline_equation') and 'content' in span:
                            if span['type'] == 'inline_equation':
                                cont = f"${span['content']}$"
                            else:
                                cont = span['content']
                            line_text.append(cont)
                full_text.append("".join(line_text))
    return "".join(full_text)

def parse_title_level(text):
    kws = r'[一二三四五六七八九十]{1,2}'
    level = 2
    if re.match(r'第'+kws+r'章', text):
        level = 2
    elif re.match(r'第'+kws+r'节',text):
        level = 3
    elif re.match(kws,text):
        level = 4
    return level

class Save_Types(Enum):
    Text_Image = 1
    Text_Only = 2
    Image_Only = 3
    Footnote = 4

def process_json_to_md(json_file_path, output_md_path,
                       save_types: Save_Types = Save_Types.Text_Image,
                       fliter_fun:Optional[Callable] = None):
    """
    处理给定的JSON文件，将其内容转换为Markdown格式的文档，并添加页面标记和跨页处理。

    Args:
        json_file_path (str): 输入的JSON文件路径。
        output_md_path (str): 输出的Markdown文件路径。
    """
    # 定义并创建用于存放图片的文件夹
    save_imgs = save_types in (Save_Types.Text_Image, Save_Types.Image_Only)
    save_text = save_types in (Save_Types.Text_Image, Save_Types.Text_Only)
    save_footnote = save_types is Save_Types.Footnote
    pblocks_name = 'discarded_blocks' if save_footnote else 'para_blocks'
    if save_imgs:
        asset_dir = os.path.join(os.path.dirname(json_file_path), 'assert')
        os.makedirs(asset_dir, exist_ok=True)

    # 读取并解析JSON文件
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：文件 {json_file_path} 未找到。")
        return
    except json.JSONDecodeError as e:
        print(f"错误：文件 {json_file_path} 不是有效的JSON格式。错误信息: {e}")
        return

    md_content_parts = []

    # 遍历JSON中的每一页
    for page in data.get('pdf_info', []):
        # 1. 在每页开始前插入页码标记
        md_content_parts.append(f"========{page.get('page_idx')+1}")
        page_blocks = page.get(pblocks_name, [])
        if not page_blocks: continue
       
        # 遍历页面内的所有块
        for block in page_blocks:
            block_type = block.get('type')
            
            if save_text and block_type == 'title':
                title_text = get_text_from_block(block,block_type)
                level = parse_title_level(title_text)
                if title_text:
                    md_content_parts.append('#'*level + f" {title_text}")

            elif save_text and block_type == 'text':
                paragraph_text = get_text_from_block(block,block_type, fliter_fun)
                if paragraph_text:
                    md_content_parts.append(paragraph_text)
            
            elif save_footnote and block_type == 'discarded':
                paragraph_text = get_text_from_block(block,block_type,fliter_fun)
                if paragraph_text:
                    md_content_parts.append(paragraph_text)

            elif save_imgs and block_type == 'image':
                image_url, caption_text = None, None
                for sub_block in block.get('blocks', []):
                    if sub_block.get('type') == 'image_body':
                        try:
                            image_url = sub_block['lines'][0]['spans'][0]['image_path']
                        except (KeyError, IndexError): continue
                    elif sub_block.get('type') == 'image_caption':
                        caption_text = get_text_from_block(sub_block,'title')

                if image_url:
                    try:
                        response = requests.get(image_url, stream=True)
                        response.raise_for_status()
                        filename = os.path.basename(urlparse(image_url).path)
                        page_filename = '{:04d}@{}'.format(page['page_idx'],filename)
                        local_image_path = os.path.join(asset_dir, page_filename)
                        with open(local_image_path, 'wb') as img_file:
                            for chunk in response.iter_content(chunk_size=8192):
                                img_file.write(chunk)

                    except requests.exceptions.RequestException as e:
                        local_image_path = image_url
                        print(f"警告：无法下载图片 {image_url}。错误: {e}")
                        # md_content_parts.append(f"[图片下载失败: {image_url}]")
                    md_image_line = f"![]({local_image_path})"
                    if caption_text:
                        md_image_line += f"\n> 【图：{caption_text}】"
                    md_content_parts.append(md_image_line)


    # 自定义连接逻辑来生成最终的Markdown字符串
    final_md = ""
    for i, part in enumerate(md_content_parts):
        final_md += part
        # 如果当前部分不是最后一部分，则决定使用什么分隔符
        if i < len(md_content_parts) - 1:
            final_md += '\n\n'

    # 将最终内容写入输出文件
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(final_md)
    
    print(f"成功将 {json_file_path} 转换为 {output_md_path}")


def process_markdown_pagination(input_file, output_file):
    """
    处理Markdown文档中的分页衔接问题
    
    Args:
        input_file: 输入的markdown文件路径
        output_file: 输出的markdown文件路径
    
    Returns:
        tuple: (marked_pages, unmarked_pages) 分别为添加了标记和未添加标记的页码列表
    """
    
    # 读取文件内容
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 将内容按行分割
    lines = content.split('\n')
    
    # 处理后的行列表
    processed_lines = []
    
    # 记录添加了标记的页码和未添加标记的页码
    marked_pages = []
    unmarked_pages = []
    
    i = 0
    while i < len(lines):
        current_line = lines[i]
        
        # 检查是否是分页符行（格式：========<页码>）
        page_match = re.match(r'^=+(\d+)$', current_line.strip())
        if page_match:
            # 提取页码
            page_number = page_match.group(1)
            # 找到分页符，检查前后段落
            
            # 找到前一段最后一行（跳过空行）
            prev_paragraph_end = None
            prev_idx = i - 1
            
            # 向前查找非空行
            while prev_idx >= 0 and lines[prev_idx].strip() == '':
                prev_idx -= 1
            
            if prev_idx >= 0:
                prev_paragraph_end = lines[prev_idx]
            
            # 找到下一段第一行（跳过空行和分页符后的空行）
            next_paragraph_start = None
            next_idx = i + 1
            
            # 向后查找非空行
            while next_idx < len(lines) and lines[next_idx].strip() == '':
                next_idx += 1
            
            if next_idx < len(lines):
                next_paragraph_start = lines[next_idx]
            
            # 判断是否需要添加<nobreak>标志
            should_add_nobreak = False
            para_is_break = False
            
            if prev_paragraph_end and next_paragraph_start:
                # 检查前一段是否以##开头（标题行）
                is_prev_title = prev_paragraph_end.strip().startswith('##')
                # 检查后一段是否以##开头（标题行）
                is_next_title = next_paragraph_start.strip().startswith('##')
                
                # 如果前后都不是标题行
                if not is_prev_title and not is_next_title:
                    # 检查前一段结尾是否是文字或逗号等标点符号
                    # 排除句号、问号、感叹号、冒号、分号等表示句子结束的标点
                    ending_punctuation = ['.', '。', '!', '！', '?', '？', ':', '：', ';', '；']
                    last_char = prev_paragraph_end.rstrip()[-1] if prev_paragraph_end.rstrip() else ''
                    
                    # 如果结尾不是结束性标点符号，则需要衔接
                    if last_char and last_char not in ending_punctuation:
                        should_add_nobreak = True
                    else:
                        para_is_break = True
            
            # 如果需要添加<nobreak>，修改已处理的最后一个非空行
            if should_add_nobreak:
                # 找到processed_lines中最后一个非空行的索引
                for j in range(len(processed_lines) - 1, -1, -1):
                    if processed_lines[j].strip():
                        # 在该行末尾添加<nobreak>
                        processed_lines[j] = processed_lines[j].rstrip() + '<nobreak>'
                        marked_pages.append(page_number)
                        break
            else:
                pass
                # 记录未添加标记的页码
            if para_is_break:
                unmarked_pages.append(page_number)
        
        # 将当前行添加到处理结果中
        processed_lines.append(current_line)
        i += 1
    
    # 将处理后的内容写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(processed_lines))
    
    print(f"处理完成！结果已保存到 {output_file}")
    print(f"\n统计信息：")
    # print(f"添加了<nobreak>标记的页码: {', '.join(marked_pages) if marked_pages else '无'}")
    print(f"未添加标记的页码: {', '.join(unmarked_pages) if unmarked_pages else '无'}; 总计：{len(unmarked_pages)}")
    print(f"总计处理页数: {len(marked_pages) + len(unmarked_pages)}")
    
    return marked_pages, unmarked_pages


# --- 主程序执行 ---
if __name__ == '__main__':
    input_json_file = "D:\works\文档校正\sxln.json"
    output_markdown_file = "D:\works\文档校正\sxln.md"
    process_json_to_md(input_json_file, output_markdown_file, Save_Types.Text_Only, None)
    process_markdown_pagination(output_markdown_file, 'D:\works\文档校正\sxln.md')
    pass