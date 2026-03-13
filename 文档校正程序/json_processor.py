import json
import re
import os
import requests
from urllib.parse import urlparse
from typing import Callable, Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ExtractorConfig:
    """提取器配置类，增强用户自定义能力。"""
    # 提取开关
    save_text: bool = True
    save_images: bool = True
    save_formulas: bool = True
    save_footnotes: bool = True
    save_header: bool = False
    save_footer: bool = False

    # 标题解析配置：正则表达式映射到标题层级
    title_patterns: List[Dict[str, Union[str, int]]] = field(default_factory=lambda: [
        {"pattern": r'^第[一二三四五六七八九十]{1,2}章', "level": 2},
        {"pattern": r'^第[一二三四五六七八九十]{1,2}节', "level": 3},
        {"pattern": r'^[一二三四五六七八九十]{1,2}', "level": 4},
    ])
    default_title_level: int = 2

    # 样式配置
    formula_style: str = "${content}$"  # 行内公式样式
    image_caption_style: str = "\n> 【图：{caption}】"
    page_break_marker: str = "========{page_num}"

    # 过滤配置
    # bbox 格式: [x0, y0, x1, y1]
    # 比如过滤宽度过窄的块或特定区域
    coordinate_filter: Optional[Callable[[Dict[str, Any], str], bool]] = None

class TitleParser:
    """处理标题级别解析。"""
    def __init__(self, patterns: List[Dict[str, Union[str, int]]], default_level: int):
        self.patterns = patterns
        self.default_level = default_level

    def get_level(self, text: str) -> int:
        for item in self.patterns:
            if re.match(item["pattern"], text.strip()):
                return item["level"]
        return self.default_level

class TextExtractor:
    """核心文本提取逻辑。"""
    def __init__(self, config: ExtractorConfig):
        self.config = config

    def get_text_basic(self, block: Dict[str, Any], btype: str) -> str:
        """从具有 lines 的块中提取文本。"""
        if 'lines' not in block:
            return ""
        
        # 坐标过滤逻辑
        if self.config.coordinate_filter and not self.config.coordinate_filter(block, btype):
            return ""

        lines_text = []
        for line in block.get('lines', []):
            spans = line.get('spans', [])
            line_parts = []
            for span in spans:
                stype = span.get('type')
                content = span.get('content', '')
                if not content:
                    continue

                if stype == 'text':
                    line_parts.append(content)
                elif stype == 'inline_equation' and self.config.save_formulas:
                    line_parts.append(self.config.formula_style.format(content=content))
            
            lines_text.append("".join(line_parts))
        
        return "".join(lines_text)

    def get_text_from_block(self, block: Dict[str, Any], btype: str) -> str:
        """迭代式提取文本，支持嵌套 list。"""
        if 'lines' in block:
            return self.get_text_basic(block, btype)
        
        if btype != 'list' or 'blocks' not in block:
            return ""

        stack = [[iter(block['blocks']), []]]
        while stack:
            it, collected = stack[-1]
            try:
                curr_item = next(it)
                if 'lines' in curr_item:
                    text = self.get_text_basic(curr_item, btype)
                    if text:
                        collected.append(text)
                elif 'blocks' in curr_item:
                    stack.append([iter(curr_item['blocks']), []])
            except StopIteration:
                _, finished_collected = stack.pop()
                joined = "\n".join(finished_collected)
                if not stack:
                    return joined
                if joined:
                    stack[-1][1].append(joined)
        return ""

class MarkdownConverter:
    """主逻辑：解析 JSON 并生成 Markdown。"""
    def __init__(self, config: ExtractorConfig):
        self.config = config
        self.extractor = TextExtractor(config)
        self.title_parser = TitleParser(config.title_patterns, config.default_title_level)

    def _download_image(self, image_url: str, asset_dir: Path, page_idx: int) -> str:
        """下载图片并返回本地路径。"""
        try:
            response = requests.get(image_url, stream=True, timeout=10)
            response.raise_for_status()
            
            filename = os.path.basename(urlparse(image_url).path)
            local_filename = f"{page_idx:04d}@{filename}"
            local_path = asset_dir / local_filename
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return str(local_path)
        except Exception as e:
            print(f"Warning: Failed to download image {image_url}: {e}")
            return image_url

    def convert(self, json_path: str, output_path: str):
        """执行转换流程。"""
        json_path = Path(json_path)
        output_path = Path(output_path)
        
        if self.config.save_images:
            # 修改图片保存路径，使其与 JSON 文件名相关
            asset_dir_name = f"{json_path.stem}.assets"
            asset_dir = json_path.parent / asset_dir_name
            asset_dir.mkdir(exist_ok=True)
        else:
            asset_dir = None
            asset_dir_name = ""

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        md_parts = []
        for page in data.get('pdf_info', []):
            page_idx = page.get('page_idx', 0)
            md_parts.append(self.config.page_break_marker.format(page_num=page_idx + 1))
            
            # 处理正文块
            for block in page.get('para_blocks', []):
                btype = block.get('type')
                
                if btype == 'title' and self.config.save_text:
                    text = self.extractor.get_text_from_block(block, btype)
                    if text:
                        level = self.title_parser.get_level(text)
                        md_parts.append(f"{'#' * level} {text}")
                
                elif btype in ('text', 'list') and self.config.save_text:
                    text = self.extractor.get_text_from_block(block, btype)
                    if text:
                        md_parts.append(text)
                
                elif btype == 'image' and self.config.save_images:
                    img_url, caption = None, ""
                    for sub in block.get('blocks', []):
                        if sub.get('type') == 'image_body':
                            try:
                                img_url = sub['lines'][0]['spans'][0]['image_path']
                            except (KeyError, IndexError): continue
                        elif sub.get('type') == 'image_caption':
                            caption = self.extractor.get_text_from_block(sub, 'title')
                    
                    if img_url:
                        local_abs_path = self._download_image(img_url, asset_dir, page_idx)
                        # 使用相对于 markdown 文件的文件夹路径
                        if local_abs_path != img_url:
                            local_filename = os.path.basename(local_abs_path)
                            local_rel_path = f"{asset_dir_name}/{local_filename}"
                        else:
                            local_rel_path = img_url
                        
                        img_md = f"![]({local_rel_path})"
                        if caption:
                            img_md += self.config.image_caption_style.format(caption=caption)
                        md_parts.append(img_md)

            # 处理脚注/摒弃块 (如果开启)
            if self.config.save_footnotes or self.config.save_header or self.config.save_footer:
                for block in page.get('discarded_blocks', []):
                    btype = block.get('type')
                    # 这里可以根据规则进一步精细化，比如判断是否是 page_footnote
                    if btype == 'page_footnote' and self.config.save_footnotes:
                        text = self.extractor.get_text_from_block(block, btype)
                        if text:
                            md_parts.append(text)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(md_parts))
        
        print(f"Successfully converted {json_path} to {output_path}")

if __name__ == "__main__":
    # 示例用法
    def my_filter(block, btype):
        if 'bbox' not in block: return True
        x0, y0, x1, y1 = block['bbox']
        # 示例：过滤掉宽度太小的块
        if abs(x1 - x0) < 50: return False
        return True

    cfg = ExtractorConfig(
        save_images=True,
        coordinate_filter=my_filter
    )
    
    # 假设有这个文件
    # processor = MarkdownConverter(cfg)
    # processor.convert("test.json", "output.md")
    pass
