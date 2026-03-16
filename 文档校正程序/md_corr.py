import re
from pathlib import Path

Closing_Punts = ['。', '.', '？', '！', '?', '!', ':', '：']
NoClosing_Punts = [',', '，', '、']
CJK_Range = (r'\u4e00', r'\u9fa5')
CJK_Punct_Range = (r'\u3000', r'\u303f', r'\uff01', r'\uff5e')


_RE_MD_LINK = re.compile(r'(!?\[[^\]]*\]\([^)]*\))')
_RE_SPACE_BETWEEN_CJK = re.compile(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])')

_PUNCTUATION_MAP = {
    ",": "，", ".": "。", "?": "？", "!": "！",
    ":": "：", ";": "；", "(": "（", ")": "）",
    "[": "【", "]": "】", "{": "｛", "}": "｝"
}
_CJK_CLASS = r'[\u4e00-\u9fa5\u3000-\u303f\uff01-\uff5e]'
_RE_QUOTE_PUNC = re.compile(f'([""''])\\s*([,.?!:;])\\s*')
_RE_PUNC_QUOTE = re.compile(f'([,.?!:;])\\s*([""''])')

CJK_EXTRA_PUNCT = '\u2014\u2026\u201c\u201d\u2018\u2019\u3008\u3009\u300a\u300b\u300c\u300d\u300e\u300f\u3010\u3011\u3014\u3015'


def is_cjk(char):
    """检查一个字符是否是中日韩（CJK）统一表意文字或中文标点。"""
    if not char:
        return False
    code = ord(char)
    if 0x4e00 <= code <= 0x9fa5:
        return True
    if 0x3000 <= code <= 0x303f or 0xff01 <= code <= 0xff5e:
        return True
    if char in CJK_EXTRA_PUNCT:
        return True
    return False

def is_near_chinese(text, pos):
    """检查文本指定位置附近是否有汉字或中文标点（跳过空格）。"""
    # 向前检查
    j = pos - 1
    while j >= 0 and text[j] in (' ', '\t'): j -= 1
    if j >= 0 and is_cjk(text[j]): return True
    # 向后检查
    j = pos + 1
    while j < len(text) and text[j] in (' ', '\t'): j += 1
    if j < len(text) and is_cjk(text[j]): return True
    return False

def protect_markdown(text):
    """
    保护markdown语法中的图片和链接，返回保护后的文本和位置映射。
    使用特殊标记替换markdown语法，处理完后再恢复。
    """
    parts = []
    last_end = 0
    protected_parts = []
    
    for match in _RE_MD_LINK.finditer(text):
        if match.start() > last_end:
            protected_parts.append(text[last_end:match.start()])
        protected_parts.append(f'\x00MD{len(parts)}\x00')
        parts.append(match.group(0))
        last_end = match.end()
    
    if last_end < len(text):
        protected_parts.append(text[last_end:])
    
    return ''.join(protected_parts), parts


def restore_markdown(text, parts):
    """恢复被保护的markdown语法"""
    for i, part in enumerate(parts):
        text = text.replace(f'\x00MD{i}\x00', part)
    return text


def replace_quotes_smartly(text):
    """
    智能地替换英文单双引号为中文对应引号。
    仅当引号靠近中文字符时才进行转换，以保护英文短语或句子。
    """
    in_single_quotes = False
    in_double_quotes = False
    result_chars = []

    for i, char in enumerate(text):
        if char == "'":
            if is_near_chinese(text, i):
                if not in_single_quotes:
                    result_chars.append('‘')
                    in_single_quotes = True
                else:
                    result_chars.append('’')
                    in_single_quotes = False
            else:
                result_chars.append(char)
        elif char == '"':
            if is_near_chinese(text, i):
                if not in_double_quotes:
                    result_chars.append('“')
                    in_double_quotes = True
                else:
                    result_chars.append('”')
                    in_double_quotes = False
            else:
                result_chars.append(char)
        else:
            result_chars.append(char)
            
    return "".join(result_chars)


def process_text(lines, beg:int=0):
    """
    处理文本，执行以下主要操作：
    1. 合并由于OCR识别导致的断行（任务1）。
    2. 智能清理空格：仅删除汉字之间的空格。
    3. 智能标点转换：仅在汉字相邻（含空格）时转换英文标点为中文标点，并清理随后的空格。
    4. 智能引号转换：仅在汉字相邻时转换。
    """
    # --- 任务1: 处理相邻的三段 (合并OCR断行) ---
    i = beg
    while i < len(lines) - 2:
        line1 = lines[i]
        line2 = lines[i+1]
        line3 = lines[i+2]

        line1_stripped = line1.strip()
        line3_stripped = line3.strip()

        cond1 = False
        if line1_stripped:
            last_char = line1_stripped[-1]
            # 只有当行尾不是结束标点（句号、问号、感叹号）时，才考虑合并
            if not line1_stripped.startswith('#') and last_char not in Closing_Punts:
                # 必须是 CJK 字符或逗号/顿号等非结束标点
                if is_cjk(last_char) or last_char in NoClosing_Punts:
                    cond1 = True

        cond2 = (line2.strip() == '')
        cond3 = line3_stripped and not line3_stripped.startswith('#')

        if cond1 and cond2 and cond3:
            # 合并行：将line1和line3合并，删除中间的空行
            lines[i] = line1.rstrip('\r\n') + lines[i+2]
            del lines[i+2]
            del lines[i+1]
            # 注意：合并后不增加索引i，以便检查合并后的行是否还能继续合并
            # 例如：三行合并后，新行可能还能与下一行合并
        else:
            i += 1
            
    # --- 任务2, 3, 4: 处理剩余的行 ---
    processed_lines = []
    
    punctuation_map = {
        ",": "，", ".": "。", "?": "？", "!": "！",
        ":": "：", ";": "；", "(": "（", ")": "）",
        "[": "【", "]": "】", "{": "｛", "}": "｝"
    }

    for idx, line in enumerate(lines):
        if idx < beg:
            processed_lines.append(line)
            continue

        if not any(is_cjk(c) for c in line):
            processed_lines.append(line)
            continue

        is_heading = line.strip().startswith('#')
        
        protected_line, md_parts = protect_markdown(line)

        if not is_heading:
            protected_line = _RE_SPACE_BETWEEN_CJK.sub('', protected_line)

        protected_line = replace_quotes_smartly(protected_line)

        for _ in range(2):
            for eng_punc, chn_punc in _PUNCTUATION_MAP.items():
                if eng_punc in '[]()':
                    continue
                esc = re.escape(eng_punc)
                protected_line = re.sub(f'({_CJK_CLASS})\\s*{esc}\\s*', f'\\1{chn_punc}', protected_line)
                protected_line = re.sub(f'{esc}\\s*({_CJK_CLASS})', f'{chn_punc}\\1', protected_line)
            
            protected_line = _RE_QUOTE_PUNC.sub(
                lambda m: m.group(1) + _PUNCTUATION_MAP.get(m.group(2), m.group(2)), protected_line)
            protected_line = _RE_PUNC_QUOTE.sub(
                lambda m: _PUNCTUATION_MAP.get(m.group(1), m.group(1)) + m.group(2), protected_line)
        
        line = restore_markdown(protected_line, md_parts)
        
        processed_lines.append(line)

    return "".join(processed_lines)


def process_file(file_pth, beg: int = 200):
    file_pth = Path(file_pth)
    output_pth = file_pth.with_stem(file_pth.stem + '_corr')
    with open(file_pth, 'r', encoding='utf-8') as f:
        words = f.readlines()
    output_words = process_text(words, beg)
    with open(output_pth, 'w', encoding='utf-8') as wf:
        wf.write(output_words)


if __name__ == '__main__':
    input_file = Path(__file__).parent.parent / '文档校正' / '未央河月：最终的编曲 虎山.md'
    process_file(input_file, 1)