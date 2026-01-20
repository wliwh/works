#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR文本校正工具
用于校正OCR识别后的中文文本，包括标点符号规范化、错别字修正、注释插入等功能。
"""

import os
import re
import json
import logging
import argparse
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from tqdm import tqdm
from handle.api_handler import create_api_handler


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('md_ai.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """配置类"""
    # API配置
    ark_model: str = 'kimi-k2-250711'
    ollama_model: str = 'llama3.1:8b'
    temperature: float = 1.0
    max_tokens: int = 8192
    top_p: float = 0.97
    frequency_penalty: float = 0
    
    # 文件处理配置
    page_marker: str = '========='
    output_suffix: str = '_corrected'
    chunk_size: int = 1000
    
    # 进度保存配置
    save_progress: bool = True
    progress_file: str = 'progress.json'
    
    # 其他配置
    backup_original: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0


class PunctuationConverter:
    """标点符号转换器"""
    
    PUNCT_MAP = {
        ',': '，', '.': '。', ';': '；', ':': '：', '?': '？', '!': '！',
        '(': '（', ')': '）',
        '<': '《', '>': '》',
        '-': '—', '_': '——',
        # 以下根据需要启用
        # '[': '【', ']': '】', '{': '｛', '}': '｝',
        # '@': '＠', '#': '＃', '$': '￥', '%': '％', '^': '＾', '&': '＆', '*': '＊',
        # '+': '＋', '=': '＝', '|': '｜', '\\': '＼', '/': '／', '`': '｀', '~': '～'
    }
    
    @classmethod
    def convert(cls, text: str) -> str:
        """转换标点符号"""
        for eng, chi in cls.PUNCT_MAP.items():
            text = text.replace(eng, chi)
        return text


class AITextCorrector:
    """AI文本校正器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.ark_handler = create_api_handler('ark')
        self.ollama_handler = create_api_handler('ollama')
        
        # 加载进度
        self.progress = self._load_progress()
        
    def _load_progress(self) -> Dict:
        """加载进度文件"""
        if not self.config.save_progress or not os.path.exists(self.config.progress_file):
            return {}
        
        try:
            with open(self.config.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载进度文件失败: {e}")
            return {}
    
    def _save_progress(self, filename: str, current_page: int, total_pages: int):
        """保存进度"""
        if not self.config.save_progress:
            return
        
        self.progress[filename] = {
            'current_page': current_page,
            'total_pages': total_pages,
            'timestamp': str(__import__('datetime').datetime.now())
        }
        
        try:
            with open(self.config.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存进度文件失败: {e}")
    
    def _get_api_args(self, use_ark: bool = True) -> Dict:
        """获取API参数"""
        if use_ark:
            return {
                'extra_headers': {'x-is-encrypted': 'true'},
                'temperature': self.config.temperature,
                'max_tokens': self.config.max_tokens,
                'frequency_penalty': self.config.frequency_penalty,
                'top_p': self.config.top_p,
                'model': self.config.ark_model,
            }
        else:
            return {
                'temperature': self.config.temperature,
                'max_tokens': self.config.max_tokens,
                'frequency_penalty': self.config.frequency_penalty,
                'model': self.config.ollama_model,
            }
    
    def correct_text(self, text: str, rule_template: str, use_ark: bool = True) -> Optional[str]:
        """使用AI校正文本"""
        messages = [
            {"role": "system", "content": rule_template},
            {"role": "user", "content": text}
        ]
        
        kwargs = self._get_api_args(use_ark)
        handler = self.ark_handler if use_ark else self.ollama_handler
        
        for attempt in range(self.config.max_retries):
            try:
                result = handler.chat_completion(messages=messages, **kwargs)
                if result:
                    return result.strip()
            except Exception as e:
                logger.warning(f"AI校正失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    import time
                    time.sleep(self.config.retry_delay)
        
        logger.error("AI校正最终失败")
        return None


class TextProcessor:
    """文本处理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.corrector = AITextCorrector(config)
        
    def extract_pages(self, file_path: str, start_page: int = 1, end_page: Optional[int] = None) -> List[Tuple[int, str]]:
        """提取页面内容"""
        pages = []
        current_page = 0
        current_content = []
        found_start = False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                # 检查是否是所有可能的分页标记 (========n, ========n****, ========n=====)
                if line.startswith(self.config.page_marker):
                    # 尝试从行中提取页码
                    match = re.search(r'(\d+)', line)
                    if not match:
                        if found_start:
                            current_content.append(line)
                        continue
                    
                    page_num = int(match.group(1))
                    
                    if page_num == start_page:
                        found_start = True
                    elif end_page and page_num > end_page:
                        if found_start and current_content:
                            pages.append((current_page, ''.join(current_content)))
                        found_start = False
                        break
                    
                    if found_start:
                        if current_content:
                            pages.append((current_page, ''.join(current_content)))
                        current_page = page_num
                        current_content = []
                    continue
                
                if found_start:
                    current_content.append(line)
            
            if found_start and current_content:
                pages.append((current_page, ''.join(current_content)))
                
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            
        return pages
    
    def process_file_pages(self, file_path: str, start_page: int = 1, end_page: Optional[int] = None) -> str:
        """按页处理文件"""
        pages = self.extract_pages(file_path, start_page, end_page)
        if not pages:
            logger.error("未找到页面内容")
            return ""
        
        output_path = self._get_output_path(file_path)
        processed_pages = []
        
        # 检查进度
        file_key = os.path.basename(file_path)
        saved_progress = self.corrector.progress.get(file_key, {})
        start_from = saved_progress.get('current_page', 0)
        
        logger.info(f"开始处理文件: {file_path}")
        logger.info(f"总页数: {len(pages)}, 从第 {start_from + 1} 页开始")
        
        with tqdm(total=len(pages), desc="处理进度") as pbar:
            for i, (page_num, content) in enumerate(pages):
                if i < start_from:
                    pbar.update(1)
                    continue
                
                # 处理页面
                corrected_content = self.corrector.correct_text(content, self._get_page_rule())
                
                # 构建页面标记
                page_marker = f"{self.config.page_marker}{page_num + 1}"
                if corrected_content and len(corrected_content) > 4:
                    if "】" in corrected_content[-3:] or (len(corrected_content) < 20 and len(content) > 80):
                        page_marker += '*****'
                    page_marker += '\n'
                    processed_pages.append(page_marker + corrected_content + '\n')
                else:
                    page_marker += '=====\n'
                    processed_pages.append(page_marker + '\n')
                
                # 保存进度
                self.corrector._save_progress(file_key, i + 1, len(pages))
                pbar.update(1)
        
        # 写入输出文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(processed_pages)
            logger.info(f"处理完成，输出文件: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"写入输出文件失败: {e}")
            return ""
    
    def process_file_blocks(self, file_path: str, start_line: int = 0, end_line: int = 0) -> str:
        """按块处理文件"""
        output_path = self._get_output_path(file_path)
        processed_lines = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return ""
        
        total_lines = len(lines)
        if end_line == 0 or end_line > total_lines:
            end_line = total_lines
        
        logger.info(f"开始处理文件: {file_path}")
        logger.info(f"处理行数: {start_line} 到 {end_line}")
        
        with tqdm(total=end_line - start_line, desc="处理进度") as pbar:
            for i, line in enumerate(lines):
                if i < start_line:
                    processed_lines.append(line)
                    continue
                if i >= end_line:
                    processed_lines.append(line)
                    break
                
                if self._should_correct_line(line, i, start_line, end_line):
                    corrected_line = self.corrector.correct_text(line, self._get_block_rule())
                    if corrected_line:
                        if not corrected_line.endswith('\n'):
                            corrected_line += '\n'
                        processed_lines.append(corrected_line)
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
                
                pbar.update(1)
        
        # 写入输出文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(processed_lines)
            logger.info(f"处理完成，输出文件: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"写入输出文件失败: {e}")
            return ""
    
    def _get_output_path(self, file_path: str) -> str:
        """获取输出文件路径"""
        path = Path(file_path)
        stem = path.stem
        suffix = path.suffix
        return str(path.parent / f"{stem}{self.config.output_suffix}{suffix}")
    
    def _should_correct_line(self, line: str, line_num: int, start_line: int, end_line: int) -> bool:
        """判断是否需要校正该行"""
        if line.startswith(('#', '**')):
            return False
        elif line_num <= start_line:
            return False
        elif line_num >= end_line:
            return False
        elif line.strip() == '':
            return False
        return True
    
    def _get_page_rule(self) -> str:
        """获取页面处理规则"""
        return """你是一个专业的文本编辑。你的任务是接收OCR识别后的文本，并严格按照以下要求进行处理和输出。请将下方"【待处理文本】"中的内容进行整理。

**任务要求:**

1.  **标点符号规范化:** 将文档中出现的所有标点符号都转换为中文标点符号。例如，将","替换为"，"，将"?"替换为"？"，将":"替换为"："等。包括后面提到的注释。
2.  **错误修正:**
    *   **错别字修正:** 识别并修正OCR过程中可能出现的常见错别字。
    *   **移除多余空格:** 删除单词、句子或段落之间不必要的多余空格。
    *   **修正错误分行:** 将因OCR识别错误而导致的、不符合阅读习惯的错误分行进行合并，确保段落完整连贯。
3.  **注释插入:**
    *   在文本中，你可能会看到一些具有注释性质的段落，它们都在文本的底部（如果有的话）
    *   请将这些注释内容移动到其在正文中对应的引用位置
    *   注释的顺序与正文中注释插入位置的顺序完全一致
    *   使用中文【】括号将插入的注释内容括起来。【】中一定要放入文档中原有的注释，并且不要重复注释
4.  **输出格式:**
    *   **仅输出处理后的文字:** 你的最终输出应该是经过上述所有步骤处理后的完整文本。
    *   **不要进行任何概括或总结:** 严格禁止对文本内容进行任何形式的归纳、总结或提炼。
    *   **不要添加额外内容:** 除了根据要求整理文本和插入注释外，不要添加任何额外的标题、说明、前言或结语。"""
    
    def _get_block_rule(self) -> str:
        """获取块处理规则"""
        return """你是一个专业的文本编辑。你的任务是接收OCR识别后的文本，并严格按照以下要求进行处理和输出。请将下方"【待处理文本】"中的内容进行整理。

**任务要求:**
1.  **错别字修正:** 识别并修正OCR过程中可能出现的常见错别字。
2.  **引文校订：** 文中`> `开头的文字表示引用文献，你要仔细核对校订，输出仍然用`> `开头，不要删去这一符号。
3.  **输出要求:** 你的最终输出应该是经过上述所有步骤处理后的完整文本，不要进行任何概括或总结，也不要添加额外内容。"""


def load_config(config_file: str) -> Config:
    """加载配置文件"""
    if not os.path.exists(config_file):
        logger.info(f"配置文件 {config_file} 不存在，使用默认配置")
        return Config()
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return Config(**config_data)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return Config()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='OCR文本校正工具')
    parser.add_argument('file', help='要处理的文件路径')
    parser.add_argument('--mode', choices=['page', 'block'], default='page', help='处理模式')
    parser.add_argument('--start', type=int, default=1, help='起始页码/行号')
    parser.add_argument('--end', type=int, default=0, help='结束页码/行号 (0表示到文件末尾)')
    parser.add_argument('--suffix', help='输出文件后缀 (默认为 _corrected)')
    parser.add_argument('--marker', help='页面分隔符标记 (默认为 =========)')
    parser.add_argument('--model', help='指定模型名称 (Ark模型)')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--use-ollama', action='store_true', help='使用Ollama API')
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # CLI覆盖配置
    if args.suffix:
        config.output_suffix = args.suffix
    if args.marker:
        config.page_marker = args.marker
    if args.model:
        config.ark_model = args.model
    
    # 创建处理器
    processor = TextProcessor(config)
    
    # 处理文件
    if args.mode == 'page':
        result = processor.process_file_pages(args.file, args.start, args.end)
    else:
        result = processor.process_file_blocks(args.file, args.start, args.end)
    
    if result:
        logger.info("处理完成")
    else:
        logger.error("处理失败")


if __name__ == '__main__':
    # 示例用法
    # python md_ai.py input.txt --mode page --start 1 --end 100
    # python md_ai.py input.txt --mode block --start 285 --end 1889
    
    main()
