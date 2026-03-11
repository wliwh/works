import os
import re
import sys
import argparse
from pathlib import Path
from pypdf import PdfWriter, PdfReader, Transformation

def merge_pdfs(directory, output_filename=None, resize=False):
    directory = Path(directory)
    if not directory.is_dir():
        print(f"错误: 目录 {directory} 不存在或不是一个有效的目录。")
        return

    # 正则表达式定义 (根据命名规则)
    # A. [A-Z0-9]{32}\.pdf (封面页)
    re_a = re.compile(r'^([a-zA-Z0-9]{32})\.pdf$')
    # B. [A-Z0-9]{32}(\d+)\-(\d+)\.pdf
    re_b = re.compile(r'^([a-zA-Z0-9]{32})(\d+)-(\d+)\.pdf$')
    # C. (\d+)\-(\d+)\.pdf
    re_c = re.compile(r'^(\d+)-(\d+)\.pdf$')

    covers = []
    contents = []

    if not output_filename:
        output_filename = "merged_document.pdf"
    elif not output_filename.lower().endswith('.pdf'):
        output_filename += ".pdf"
        
    out_filepath = directory / output_filename

    pdf_files = list(directory.glob('*.pdf'))
    if not pdf_files:
        print("未在目录中找到任何PDF文件。")
        return

    for filepath in pdf_files:
        filename = filepath.name
        if filename == output_filename:
            continue

        match_b = re_b.match(filename)
        if match_b:
            contents.append({
                'type': 'B',
                'filepath': filepath,
                'filename': filename,
                'start': int(match_b.group(2)),
                'end': int(match_b.group(3))
            })
            continue

        match_a = re_a.match(filename)
        if match_a:
            covers.append({
                'type': 'A',
                'filepath': filepath,
                'filename': filename,
                'start': 0,
                'end': 0
            })
            continue

        match_c = re_c.match(filename)
        if match_c:
            contents.append({
                'type': 'C',
                'filepath': filepath,
                'filename': filename,
                'start': int(match_c.group(1)),
                'end': int(match_c.group(2))
            })
            continue

    if not contents and not covers:
        print("未找到符合命名规则的 PDF 文件。")
        return

    print(f"\n========================================")
    print("开始处理目录下的 PDF 文件组合...")
    if len(covers) > 1:
        print(f"  [警告] 发现多个封面页，将只使用第一个找到的封面: {covers[0]['filename']}")

    # 按起始页对内容片段进行排序
    contents.sort(key=lambda x: x['start'])

    target_width = None
    
    if resize and contents:
        first_reader = PdfReader(contents[0]['filepath'])
        if first_reader.pages:
            first_page = first_reader.pages[0]
            target_width = float(first_page.mediabox.width)
            print(f"  [尺寸基准] 启用等比缩放，统一宽度为: {target_width:.2f} (基于 {contents[0]['filename']})")

    merger = PdfWriter()
    
    def add_page_resized(page):
        if not (resize and target_width):
            merger.add_page(page)
            return

        current_width = float(page.mediabox.width)
        current_height = float(page.mediabox.height)
        if abs(current_width - target_width) > 2:
            scale = target_width / current_width
            new_height = current_height * scale
            
            page.add_transformation(Transformation().scale(sx=scale, sy=scale))
            page.mediabox.lower_left = (0, 0)
            page.mediabox.upper_right = (target_width, new_height)
            page.cropbox.lower_left = (0, 0)
            page.cropbox.upper_right = (target_width, new_height)
            
        merger.add_page(page)

    # 1. 优先合并封面
    if covers:
        print(f"  合并封面: {covers[0]['filename']}")
        if resize and target_width:
            reader = PdfReader(covers[0]['filepath'])
            for page in reader.pages:
                add_page_resized(page)
        else:
            merger.append(covers[0]['filepath'])
    
    # 2. 依次合并内容并在重叠时进行裁剪
    current_end_page = 0
    for c in contents:
        filepath = c['filepath']
        start_page = c['start']
        end_page = c['end']
        
        # 计算需要截取的页面范围
        if start_page <= current_end_page:
            overlap = current_end_page - start_page + 1
            if overlap > (end_page - start_page + 1):
                print(f"  [跳过] '{c['filename']}' 完全被前面的页面覆盖。")
                continue
            print(f"  合并内容页: '{c['filename']}' (剔除前 {overlap} 页由于重叠，原范围 {start_page}-{end_page})")
            num_pages = len(PdfReader(filepath).pages)
            if resize and target_width:
                reader = PdfReader(filepath)
                for i in range(overlap, num_pages):
                    add_page_resized(reader.pages[i])
            else:
                merger.append(filepath, pages=(overlap, num_pages))
        else:
            if current_end_page != 0 and start_page > current_end_page + 1:
                print(f"  [发现缺口] {current_end_page} 到 {start_page} 之间有缺失。后续文件不再合并，仅保留此前连续的部分。")
                break
            print(f"  合并内容页: '{c['filename']}' (范围 {start_page}-{end_page})")
            if resize and target_width:
                reader = PdfReader(filepath)
                for page in reader.pages:
                    add_page_resized(page)
            else:
                merger.append(filepath)
        
        if end_page > current_end_page:
            current_end_page = end_page
            
    merger.write(out_filepath)
    merger.close()
    print(f"\n  -> 合并成功！输出文件已保存为 {output_filename}")

    print(f"========================================")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="扫描目录下的PDF文件，并根据命名规则自动拼接。")
    parser.add_argument("directory", help="需要扫描的包含PDF文档的目录路径")
    parser.add_argument("-o", "--output", help="可选: 指定输出文件名 (默认: merged_document.pdf)", default=None)
    parser.add_argument("--resize", action="store_true", help="可选: 将所有页面等比例缩放并居中至第一张内容页的大小")
    args = parser.parse_args()
    
    merge_pdfs(args.directory, args.output, args.resize)
