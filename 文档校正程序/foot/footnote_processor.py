#!/usr/bin/env python3
"""
通用脚注处理程序
用于处理文档中的脚注，包括验证、映射和插入功能
"""

import re
import unicodedata
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json


@dataclass
class FootnoteConfig:
    """脚注配置类"""
    section_delimiter: str = "======="  # 部分开始标志
    text_footnote_pattern: str = r'\[(\d+)\]'     # r'([\u2460-\u2473])' # r'【(\d+)】'  # 正文中脚注符号的正则表达式
    footnote_footnote_pattern: str = r'\[(\d+)\]' # r'([\u2460-\u2473])' # r'【(\d+)】'  # 脚注中符号的正则表达式
    output_footnote_format: str = "【{content}】"  # 输出时脚注内容的格式
    

class FootnoteProcessor:
    """脚注处理器类"""
    
    def __init__(self, config: FootnoteConfig = None):
        """
        初始化脚注处理器
        
        Args:
            config: 脚注配置对象
        """
        self.config = config if config else FootnoteConfig()
        self.errors = []
        
    def process_document(self, file_path: str, output_path: str = None) -> str:
        """
        处理文档
        
        Args:
            file_path: 输入文档路径
            output_path: 输出文档路径（可选）
            
        Returns:
            处理后的文档内容
        """
        # 读取文档
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割文档为各个部分
        sections = self._split_sections(content)
        
        # 处理每个部分
        processed_sections = []
        for section_id, section_content in sections:
            processed_section = self._process_section(section_id, section_content)
            if processed_section:
                processed_sections.append(f"{self.config.section_delimiter}{section_id}\n{processed_section}")
        
        # 组合处理后的内容
        result = '\n\n'.join(processed_sections)
        
        # 输出错误信息
        if self.errors:
            print("处理过程中发现以下错误：")
            for error in self.errors:
                print(f"  - {error}")
        # 如果指定了输出路径，写入文件
        elif output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
        
        
        return result
    
    def _split_sections(self, content: str) -> List[Tuple[str, str]]:
        """
        将文档分割为各个部分
        
        Args:
            content: 文档内容
            
        Returns:
            (部分ID, 部分内容) 的列表
        """
        sections = []
        # pattern = f"{re.escape(self.config.section_delimiter)}([^\n]+)"
        pattern = f"^{re.escape(self.config.section_delimiter)}(.+)"
        # pattern = r"^###\s(.+)"
        
        matches = list(re.finditer(pattern, content, re.MULTILINE))
        
        for i, match in enumerate(matches):
            section_id = match.group(1).strip()
            start = match.end()
            
            # 找到下一个部分的开始或文档结尾
            if i < len(matches) - 1:
                end = matches[i + 1].start()
            else:
                end = len(content)
            
            section_content = content[start:end].strip()
            sections.append((section_id, section_content))
        
        return sections
    
    def _process_section(self, section_id: str, content: str) -> str:
        """
        处理单个部分
        
        Args:
            section_id: 部分ID
            content: 部分内容
            
        Returns:
            处理后的部分内容
        """
        # 分离正文和脚注
        main_text, footnotes_text = self._separate_main_and_footnotes(content)
        
        if not main_text:
            self.errors.append(f"部分 {section_id}：未找到正文内容")
            return content
        
        # 提取正文中的脚注符号
        try:
            text_footnotes = self._extract_text_footnotes(main_text)
        except ValueError as exc:
            self.errors.append(f"{section_id}：正文脚注符号解析失败 - {exc}")
            return content
        
        # 提取脚注内容
        footnote_mapping = {}
        if footnotes_text:
            try:
                footnote_mapping = self._extract_footnote_content(footnotes_text)
            except ValueError as exc:
                self.errors.append(f"{section_id}：脚注内容解析失败 - {exc}")
                return content
        
        # 验证脚注
        is_valid = self._validate_footnotes(section_id, text_footnotes, footnote_mapping)
        
        if not is_valid:
            return content  # 验证失败，返回原内容
        
        # 插入脚注内容到正文
        result = self._insert_footnotes(main_text, footnote_mapping)
        
        return result
    
    def _separate_main_and_footnotes(self, content: str) -> Tuple[str, str]:
        """
        分离正文和脚注部分
        通过检测脚注开始的模式来判断
        
        Args:
            content: 部分内容
            
        Returns:
            (正文内容, 脚注内容)
        """
        lines = content.split('\n')
        footnote_pattern = re.compile(f'^{self.config.footnote_footnote_pattern}')
        
        # 查找连续的脚注区域
        # 策略：找到第一个以脚注符号开头的行，检查后续是否都是脚注格式
        footnote_start_idx = -1
        
        for i in range(len(lines)):
            line = lines[i].strip()
            if not line:
                continue
                
            # 如果这一行以脚注符号开头
            if footnote_pattern.match(line):
                # 假设从这里开始是脚注部分
                # 验证后续的非空行是否都符合脚注格式（脚注符号开头或者是脚注内容的延续）
                is_footnote_section = True
                has_content_after = False
                
                for j in range(i+1, len(lines)):
                    check_line = lines[j].strip()
                    if check_line:
                        has_content_after = True
                        # 如果是脚注符号开头，继续
                        if footnote_pattern.match(check_line):
                            continue
                        # 如果不是脚注符号开头，检查是否可能是脚注内容的延续
                        # 脚注内容延续的特征：不以脚注符号开头，且前面有脚注
                        # 这里我们假设如果不是脚注符号开头，就是内容延续
                        # 但要确保不是新的正文段落
                        # 简单判断：如果包含正文的脚注符号模式，则不是脚注部分
                        text_pattern = re.compile(self.config.text_footnote_pattern)
                        if text_pattern.search(check_line):
                            is_footnote_section = False
                            break
                
                # 如果确认是脚注部分，并且后面有内容或者这是最后的内容
                if is_footnote_section:
                    footnote_start_idx = i
                    break
        
        if footnote_start_idx == -1:
            # 没有找到脚注部分
            return content, ""
        
        main_text = '\n'.join(lines[:footnote_start_idx]).strip()
        footnotes_text = '\n'.join(lines[footnote_start_idx:]).strip()
        
        return main_text, footnotes_text
    
    def _extract_text_footnotes(self, text: str) -> List[int]:
        """
        提取正文中的脚注符号
        
        Args:
            text: 正文内容
            
        Returns:
            脚注编号列表
        """
        pattern = re.compile(self.config.text_footnote_pattern)
        numbers = []
        for match in pattern.finditer(text):
            raw = match.group(1)
            try:
                numbers.append(self._normalize_footnote_number(raw))
            except ValueError as exc:
                raise ValueError(f"无法解析正文脚注编号 '{raw}': {exc}")
        return numbers
    
    def _extract_footnote_content(self, footnotes_text: str) -> Dict[int, str]:
        """
        提取脚注内容
        
        Args:
            footnotes_text: 脚注部分文本
            
        Returns:
            {脚注编号: 脚注内容} 的映射
        """
        mapping = {}
        lines = footnotes_text.split('\n')
        pattern = re.compile(f'^{self.config.footnote_footnote_pattern}')
        
        current_nums = []
        current_content = []
        
        for line in lines:
            stripped = line.strip()
            match = pattern.match(stripped)
            
            if match:
                # 保存之前的脚注内容
                if current_nums and current_content:
                    content = '<br/>'.join(current_content)
                    for num in current_nums:
                        mapping[num] = content
                
                # 开始新的脚注
                # 提取所有连续的脚注符号
                line_remainder = stripped
                nums = []
                while True:
                    m = pattern.match(line_remainder)
                    if m:
                        raw = m.group(1)
                        try:
                            nums.append(self._normalize_footnote_number(raw))
                        except ValueError as exc:
                            raise ValueError(f"无法解析脚注编号 '{raw}': {exc}")
                        line_remainder = line_remainder[m.end():].strip()
                    else:
                        break
                
                current_nums = nums
                current_content = [line_remainder] if line_remainder else []
            else:
                # 脚注内容的延续
                if current_nums:
                    current_content.append(line.strip())
        
        # 保存最后一个脚注
        if current_nums and current_content:
            content = '<br/>'.join(current_content)
            for num in current_nums:
                mapping[num] = content
        
        return mapping
    
    def _validate_footnotes(self, section_id: str, text_footnotes: List[int], 
                          footnote_mapping: Dict[int, str]) -> bool:
        """
        验证脚注的正确性
        
        Args:
            section_id: 部分ID
            text_footnotes: 正文中的脚注编号列表
            footnote_mapping: 脚注映射
            
        Returns:
            是否验证通过
        """
        is_valid = True
        
        # 验证正文中的脚注编号
        text_nums_set = set(text_footnotes)
        if text_footnotes:
            max_num = max(text_footnotes)
            min_num = min(text_footnotes)
            expected = set(range(min_num, max_num + 1))
            
            missing = expected - text_nums_set
            if missing:
                self.errors.append(f"{section_id}：正文中缺少脚注编号 {sorted(missing)}")
                is_valid = False
            
            # 检查重复
            if len(text_footnotes) != len(text_nums_set):
                duplicates = [n for n in text_nums_set if text_footnotes.count(n) > 1]
                self.errors.append(f"{section_id}：正文中重复的脚注编号 {sorted(duplicates)}")
                is_valid = False
        
        # 验证脚注中的编号
        footnote_nums = set(footnote_mapping.keys())
        if footnote_nums:
            max_num = max(footnote_nums)
            min_num = min(footnote_nums)
            expected = set(range(min_num, max_num + 1))
            
            missing = expected - footnote_nums
            if missing:
                self.errors.append(f"{section_id}：脚注中缺少编号 {sorted(missing)}")
                is_valid = False
        
        # 验证正文和脚注的对应关系
        if text_nums_set != footnote_nums:
            only_in_text = text_nums_set - footnote_nums
            only_in_footnotes = footnote_nums - text_nums_set
            
            if only_in_text:
                self.errors.append(f"{section_id}：只在正文中出现的脚注编号 {sorted(only_in_text)}")
                is_valid = False
            
            if only_in_footnotes:
                self.errors.append(f"{section_id}：只在脚注中出现的编号 {sorted(only_in_footnotes)}")
                is_valid = False
        
        return is_valid
    
    def _insert_footnotes(self, text: str, footnote_mapping: Dict[int, str]) -> str:
        """
        将脚注内容插入到正文中
        
        Args:
            text: 正文内容
            footnote_mapping: 脚注映射
            
        Returns:
            处理后的文本
        """
        pattern = re.compile(self.config.text_footnote_pattern)
        
        def replace_footnote(match):
            try:
                num = self._normalize_footnote_number(match.group(1))
            except ValueError:
                return match.group(0)
            content = footnote_mapping.get(num, "")
            return self.config.output_footnote_format.format(content=content)
        
        result = pattern.sub(replace_footnote, text)
        return result

    def _normalize_footnote_number(self, value: str) -> int:
        """将各种数字符号转换为整数，支持①②③等形式"""
        if value is None:
            raise ValueError("编号为空")
        raw = value.strip()
        if not raw:
            raise ValueError("编号为空")
        try:
            return int(raw)
        except ValueError:
            pass
        if len(raw) == 1:
            try:
                numeric_value = unicodedata.numeric(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"无法识别的编号 {raw}") from exc
            if float(numeric_value).is_integer():
                return int(numeric_value)
            raise ValueError(f"编号 {raw} 不是整数")
        raise ValueError(f"无法识别的编号 {raw}")


def main():
    """主函数，用于命令行调用"""
    import argparse
    
    parser = argparse.ArgumentParser(description='通用脚注处理程序')
    parser.add_argument('input', help='输入文档路径')
    parser.add_argument('-o', '--output', help='输出文档路径')
    parser.add_argument('-c', '--config', help='配置文件路径（JSON格式）')
    
    args = parser.parse_args()
    
    # 加载配置
    config = FootnoteConfig()
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            config = FootnoteConfig(**config_data)
    
    # 处理文档
    processor = FootnoteProcessor(config)
    result = processor.process_document(args.input, args.output)
    
    if not args.output:
        print("\n处理后的文档内容：")
        print("=" * 50)
        print(result)


if __name__ == '__main__':
    main()
