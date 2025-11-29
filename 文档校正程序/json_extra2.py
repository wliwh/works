from enum import Enum
import json
import re
import os
import requests
from urllib.parse import urlparse
from typing import Callable, Optional


class Save_Types(Enum):
    Text_Image_Foot = 30
    Text_Image = 6
    Text_Foot = 10
    Text_Only = 2
    Image_Only = 3

def get_text_from_block(block,btype, fliter_fun:Optional[Callable] = None):
    """从一个块（block）中提取并拼接所有文本内容。"""
    full_text = []
    if 'lines' in block:
        fres = True if fliter_fun is None else fliter_fun(block,btype)
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

def fliter_foot(blocks, btype):
    if btype in ('footer', 'page_footnote'): return True
    else: return False


def process_json_to_md(json_file_path, output_md_path,
                       save_types: Save_Types = Save_Types.Text_Image_Foot,
                       fliter_fun:Optional[Callable] = None):
    """
    处理给定的JSON文件，将其内容转换为Markdown格式的文档，并添加页面标记和跨页处理。

    Args:
        json_file_path (str): 输入的JSON文件路径。
        output_md_path (str): 输出的Markdown文件路径。
    """
    save_type_value = save_types.value
    save_text = (save_type_value % 2) == 0
    save_imgs = (save_type_value % 3) == 0
    save_foot = (save_type_value % 5) == 0

    plain_name, foot_name = 'para_blocks', 'discarded_blocks'

    if save_imgs:
        asset_dir = os.path.join(os.path.dirname(json_file_path), 'assert')
        os.makedirs(asset_dir, exist_ok=True)

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

    for page in data.get('pdf_info', []):
        # 1. 在每页开始前插入页码标记
        md_content_parts.append(f"========{page.get('page_idx')+1}")
        page_blocks = page.get(plain_name, [])
        if not page_blocks: continue

        # 遍历页面内的所有块
        for block in page_blocks:
            block_type = block.get('type')
            
            if save_text and block_type == 'title':
                title_text = get_text_from_block(block,block_type)
                level = parse_title_level(title_text)
                if title_text:
                    md_content_parts.append('#'*level + f" {title_text}")

            elif save_text and block_type in ('text','list'):
                paragraph_text = get_text_from_block(block,block_type, fliter_fun)
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

        for block in page.get(foot_name, []):
            block_type = block.get('type')
            if save_foot:
                foot_text = get_text_from_block(block,block_type, fliter_foot)
                if foot_text:
                    md_content_parts.append(foot_text)
        
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

if __name__ == '__main__':
    input = "/home/hh01/Documents/works/文档校正/MinerU_二十世纪中国历史学.json"
    output = "/home/hh01/Documents/works/文档校正/二十世纪中国历史学.md"
    process_json_to_md(input, output, Save_Types.Text_Image_Foot)
    pass