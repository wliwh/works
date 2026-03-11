import re
import argparse
from pathlib import Path
from pypdf import PdfWriter, PdfReader, Transformation


def _scan_and_classify_pdfs(directory, output_filename):
    """
    扫描目录下的PDF文件并按命名规则分类

    Returns:
        tuple: (covers列表, contents列表, 输出文件路径) 或失败时返回 (None, None, None)
    """
    # 正则表达式定义
    re_a = re.compile(r'^([a-zA-Z0-9]{32})\.pdf$')      # 封面页
    re_b = re.compile(r'^([a-zA-Z0-9]{32})(\d+)-(\d+)\.pdf$')  # 带hash的内容页
    re_c = re.compile(r'^(\d+)-(\d+)\.pdf$')           # 简单命名的内容页

    covers = []
    contents = []

    # 扫描PDF文件
    pdf_files = list(directory.glob('*.pdf'))
    if not pdf_files:
        print("未在目录中找到任何PDF文件。")
        return None, None, None

    # 分类文件
    for filepath in pdf_files:
        filename = filepath.name
        if filename == output_filename:
            continue

        match = re_b.match(filename)
        if match:
            contents.append({
                'filepath': filepath, 'filename': filename,
                'start': int(match.group(2)), 'end': int(match.group(3))
            })
            continue

        if re_a.match(filename):
            covers.append({
                'filepath': filepath, 'filename': filename,
                'start': 0, 'end': 0
            })
            continue

        match = re_c.match(filename)
        if match:
            contents.append({
                'filepath': filepath, 'filename': filename,
                'start': int(match.group(1)), 'end': int(match.group(2))
            })

    if not contents and not covers:
        print("未找到符合命名规则的 PDF 文件。")
        return None, None, None

    # 按起始页排序
    contents.sort(key=lambda x: x['start'])

    # 构建输出文件路径
    if not output_filename:
        output_filename = "merged_document.pdf"
    elif not output_filename.lower().endswith('.pdf'):
        output_filename += ".pdf"
    out_filepath = directory / output_filename

    return covers, contents, out_filepath


def _merge_pages(covers, contents, out_filepath, resize):
    """
    执行PDF合并操作

    Args:
        covers: 封面文件列表
        contents: 内容文件列表
        out_filepath: 输出文件路径
        resize: 是否启用尺寸调整
    """
    print(f"\n========================================")
    print("开始处理目录下的 PDF 文件组合...")
    if len(covers) > 1:
        print(f"  [警告] 发现多个封面页，将只使用第一个找到的封面: {covers[0]['filename']}")

    # 确定目标宽度
    target_width = None
    if resize and contents:
        first_reader = PdfReader(contents[0]['filepath'])
        if first_reader.pages:
            target_width = float(first_reader.pages[0].mediabox.width)
            print(f"  [尺寸基准] 启用等比缩放，统一宽度为: {target_width:.2f} (基于 {contents[0]['filename']})")

    merger = PdfWriter()

    # 页面缩放处理函数
    def add_page_resized(page):
        if not (resize and target_width):
            merger.add_page(page)
            return

        current_width = float(page.mediabox.width)
        if abs(current_width - target_width) > 2:
            scale = target_width / current_width
            new_height = float(page.mediabox.height) * scale
            page.add_transformation(Transformation().scale(sx=scale, sy=scale))
            page.mediabox.lower_left = (0, 0)
            page.mediabox.upper_right = (target_width, new_height)
            page.cropbox.lower_left = (0, 0)
            page.cropbox.upper_right = (target_width, new_height)
        merger.add_page(page)

    # 合并封面
    if covers:
        print(f"  合并封面: {covers[0]['filename']}")
        if resize and target_width:
            reader = PdfReader(covers[0]['filepath'])
            for page in reader.pages:
                add_page_resized(page)
        else:
            merger.append(covers[0]['filepath'])

    # 合并内容页
    current_end_page = 0
    for c in contents:
        filepath = c['filepath']
        start_page = c['start']
        end_page = c['end']
        num_pages = len(PdfReader(filepath).pages)

        if start_page <= current_end_page:
            overlap = current_end_page - start_page + 1
            if overlap > (end_page - start_page + 1):
                print(f"  [跳过] '{c['filename']}' 完全被前面的页面覆盖。")
                continue
            print(f"  合并内容页: '{c['filename']}' (剔除前 {overlap} 页由于重叠，原范围 {start_page}-{end_page})")

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
    print(f"\n  -> 合并成功！输出文件已保存为 {out_filepath.name}")
    print(f"========================================")


def merge_pdfs(directory, output_filename=None, resize=False):
    """
    合并目录下符合命名规则的PDF文件

    Args:
        directory: PDF文件所在目录
        output_filename: 输出文件名（可选）
        resize: 是否启用尺寸调整（可选）
    """
    directory = Path(directory)
    if not directory.is_dir():
        print(f"错误: 目录 {directory} 不存在或不是一个有效的目录。")
        return

    # 扫描并分类文件
    covers, contents, out_filepath = _scan_and_classify_pdfs(directory, output_filename)
    if covers is None:
        return

    # 执行合并
    _merge_pages(covers, contents, out_filepath, resize)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="扫描目录下的PDF文件，并根据命名规则自动拼接。")
    parser.add_argument("directory", help="需要扫描的包含PDF文档的目录路径")
    parser.add_argument("-o", "--output", help="可选: 指定输出文件名 (默认: merged_document.pdf)", default=None)
    parser.add_argument("--resize", action="store_true", help="可选: 将所有页面等比例缩放并居中至第一张内容页的大小")
    args = parser.parse_args()

    merge_pdfs(args.directory, args.output, args.resize)
