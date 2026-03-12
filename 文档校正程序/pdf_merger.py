import re
import argparse
from pathlib import Path
from pypdf import PdfWriter, PdfReader, Transformation

class PDFMerger:
    # Regex patterns for identifying PDF parts
    RE_COVER = re.compile(r'^([a-zA-Z0-9]{32})\.pdf$')
    RE_HASH_CONTENT = re.compile(r'^([a-zA-Z0-9]{32})(\d+)-(\d+)\.pdf$')
    RE_SIMPLE_CONTENT = re.compile(r'^(\d+)-(\d+)\.pdf$')

    def __init__(self, output_filename="merged_document.pdf", resize=False):
        self.output_filename = self._ensure_pdf_extension(output_filename)
        self.resize = resize
        self.writer = PdfWriter()
        self.target_width = None
        self.current_end_page = 0

    @staticmethod
    def _ensure_pdf_extension(filename):
        if not filename:
            return "merged_document.pdf"
        if not filename.lower().endswith('.pdf'):
            return f"{filename}.pdf"
        return filename

    def scan_directory(self, directory):
        """
        Scan directory and classify PDF files.
        """
        directory = Path(directory)
        if not directory.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")

        covers = []
        contents = []
        
        pdf_files = list(directory.glob('*.pdf'))
        for filepath in pdf_files:
            filename = filepath.name
            if filename == self.output_filename:
                continue

            # Classify by regex
            match_hash_content = self.RE_HASH_CONTENT.match(filename)
            if match_hash_content:
                contents.append({
                    'filepath': filepath, 'filename': filename,
                    'start': int(match_hash_content.group(2)), 
                    'end': int(match_hash_content.group(3))
                })
                continue

            if self.RE_COVER.match(filename):
                covers.append({'filepath': filepath, 'filename': filename})
                continue

            match_simple = self.RE_SIMPLE_CONTENT.match(filename)
            if match_simple:
                contents.append({
                    'filepath': filepath, 'filename': filename,
                    'start': int(match_simple.group(1)), 
                    'end': int(match_simple.group(2))
                })

        contents.sort(key=lambda x: x['start'])
        return covers, contents

    def _add_page(self, page, source_name):
        """
        Add a single page to the writer, with optional resizing.
        """
        if not self.resize or not self.target_width:
            self.writer.add_page(page)
            return

        current_width = float(page.mediabox.width)
        if abs(current_width - self.target_width) > 2:
            scale = self.target_width / current_width
            new_height = float(page.mediabox.height) * scale
            
            # Apply transformation
            page.add_transformation(Transformation().scale(sx=scale, sy=scale))
            
            # Reset boxes to new dimensions
            for box_name in ["mediabox", "cropbox", "bleedbox", "trimbox", "artbox"]:
                box = getattr(page, box_name)
                box.lower_left = (0, 0)
                box.upper_right = (self.target_width, new_height)
        
        self.writer.add_page(page)

    def _process_file(self, file_info, is_cover=False):
        """
        Open a file once and process its pages.
        """
        filepath = file_info['filepath']
        filename = file_info['filename']
        
        try:
            reader = PdfReader(filepath)
        except Exception as e:
            print(f"  [错误] 无法读取文件 {filename}: {e}")
            return False

        pages = reader.pages
        num_pages = len(pages)

        if not pages:
            return False

        # Set target width if not already set (anchor to first content page)
        if self.resize and not self.target_width and not is_cover:
            self.target_width = float(pages[0].mediabox.width)
            print(f"  [尺寸基准] 统一宽度为: {self.target_width:.2f} (基于 {filename})")

        if is_cover:
            print(f"  合并封面: {filename}")
            for page in pages:
                self._add_page(page, filename)
            return True

        # Content page logic
        start_page = file_info['start']
        end_page = file_info['end']

        if start_page <= self.current_end_page:
            overlap = self.current_end_page - start_page + 1
            if overlap >= num_pages:
                print(f"  [跳过] '{filename}' 完全被前面的页面覆盖。")
                return True
            print(f"  合并内容页: '{filename}' (剔除前 {overlap} 页重叠，范围 {start_page}-{end_page})")
            for i in range(overlap, num_pages):
                self._add_page(pages[i], filename)
        else:
            # Check for gap
            if self.current_end_page != 0 and start_page > self.current_end_page + 1:
                print(f"  [发现缺口] {self.current_end_page} 到 {start_page} 之间有缺失。停止合并。")
                return False
            
            print(f"  合并内容页: '{filename}' (范围 {start_page}-{end_page})")
            for page in pages:
                self._add_page(page, filename)

        if end_page > self.current_end_page:
            self.current_end_page = end_page
        
        return True

    def run(self, directory):
        """
        Execute the full merge process.
        """
        print(f"\n========================================")
        print(f"开始处理目录: {directory}")
        
        try:
            covers, contents = self.scan_directory(directory)
        except Exception as e:
            print(f"错误: {e}")
            return

        if not covers and not contents:
            print("未找到符合命名规则的 PDF 文件。")
            return

        # 1. Process Cover
        if covers:
            if len(covers) > 1:
                print(f"  [警告] 发现多个封面，使用第1个: {covers[0]['filename']}")
            self._process_file(covers[0], is_cover=True)

        # 2. Process Contents
        for item in contents:
            success = self._process_file(item)
            if not success:
                break

        # 3. Write Output
        out_path = Path(directory) / self.output_filename
        try:
            with open(out_path, "wb") as f:
                self.writer.write(f)
            print(f"\n  -> 合并成功！输出文件: {out_path.name}")
        except Exception as e:
            print(f"\n  -> [错误] 写入失败: {e}")
        finally:
            self.writer.close()
        
        print(f"========================================")

def merge_pdfs(directory, output_filename=None, resize=False):
    merger = PDFMerger(output_filename, resize)
    merger.run(directory)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="扫描目录下的PDF文件，并根据命名规则自动拼接。")
    parser.add_argument("directory", help="包含PDF文档的目录路径")
    parser.add_argument("-o", "--output", help="指定输出文件名", default=None)
    parser.add_argument("--resize", action="store_true", help="等比例缩放并统一宽度")
    args = parser.parse_args()

    merge_pdfs(args.directory, args.output, args.resize)
