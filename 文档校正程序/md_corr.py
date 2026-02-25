import os
import re

Closing_Punts = ['。', '.', '？', '！', '?', '!', ':', '：']
CJK_Range = (r'\u4e00', r'\u9fa5')
CJK_Punct_Range = (r'\u3000', r'\u303f', r'\uff01', r'\uff5e')

def is_cjk(char):
    """检查一个字符是否是中日韩（CJK）统一表意文字或中文标点。"""
    if not char: return False
    uchar = char.encode('unicode_escape').decode('ascii').lower()
    # 汉字范围
    if CJK_Range[0] <= uchar <= CJK_Range[1]: return True
    # 中文标点及符号范围
    # CJK符号和标点：\u3000-\u303F (包括：、。〃〄々〆〇〈〉《》「」『』【】等)
    # 全角ASCII标点：\uFF01-\uFF5E (包括：！＂＃＄％＆＇（）＊＋，－．／０－９：；＜＝＞？＠Ａ－Ｚ［＼］＾＿｀ａ－ｚ｛｜｝～)
    # 但要排除 \uFF00 (半角空格) 和 \uFF5F-\uFFEF 的特殊字符
    if CJK_Punct_Range[0] <= uchar <= CJK_Punct_Range[1] or CJK_Punct_Range[2] <= uchar <= CJK_Punct_Range[3]: 
        return True
    # 额外的中文标点（不在上述范围内的）
    if char in r'—“”’‘…〈〉《》「」『』【】〔〕': 
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
    # 匹配图片 ![alt](url) 和链接 [text](url)
    pattern = r'(!?\[[^\]]*\]\([^)]*\))'
    
    # 找到所有markdown语法部分
    parts = []
    last_end = 0
    protected_parts = []
    
    for match in re.finditer(pattern, text):
        # 添加前面的普通文本
        if match.start() > last_end:
            protected_parts.append(text[last_end:match.start()])
        # 添加保护标记
        protected_parts.append(f'\x00MD{len(parts)}\x00')
        parts.append(match.group(0))
        last_end = match.end()
    
    # 添加最后的普通文本
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
                if is_cjk(last_char) or last_char in [',', '，', '、']:
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

        # 检查是否包含中文。如果不含中文，视作英文行，不处理
        if not any(is_cjk(c) for c in line):
            processed_lines.append(line)
            continue

        # 检查是否是标题行
        is_heading = line.strip().startswith('#')
        
        # 保护markdown语法（图片和链接）
        protected_line, md_parts = protect_markdown(line)
        
        # 定义 CJK 字符类（含汉字和中文标点）
        # 注意：范围与 is_cjk() 函数保持一致
        cjk_class = r'[{}-{}{}-{}{}-{}]'.format(CJK_Range[0], CJK_Range[1], CJK_Punct_Range[0], CJK_Punct_Range[1], CJK_Punct_Range[2], CJK_Punct_Range[3])

        # 任务2: 智能删除空格 (仅删除汉字之间的空格，标题行跳过)
        if not is_heading:
            protected_line = re.sub(r'(?<=[{}-{}])\s+(?=[{}-{}])'.format(CJK_Range[0], CJK_Range[1], CJK_Range[0], CJK_Range[1]), '', protected_line)

        # 任务4: 智能处理引号 (初次处理，基于上下文识别开关引号)
        protected_line = replace_quotes_smartly(protected_line)

        # 任务3: 智能转换标点 (满足要求1 & 2 & 3)
        # 多次循环以处理由于标点转换后产生的新 CJK 邻接关系（如 "你好". -> "你好"。）
        for _ in range(2):
            for eng_punc, chn_punc in punctuation_map.items():
                # 跳过方括号和圆括号，它们是markdown语法的一部分
                if eng_punc in '[]()':
                    continue
                # 任务3.1: 转换英文标点为中文标点
                esc = re.escape(eng_punc)
                protected_line = re.sub(f'({cjk_class})\\s*{esc}\\s*', f'\\1{chn_punc}', protected_line)
                protected_line = re.sub(f'{esc}\\s*({cjk_class})', f'{chn_punc}\\1', protected_line)
                
            # 任务3.2: 额外处理已转换的引号与剩余英文标点的关系
            # 例如处理这种情况: "你好", -> “你好”，
            protected_line = re.sub(f'([“”‘’])\\s*([,.?!:;])\\s*', 
                          lambda m: m.group(1) + punctuation_map.get(m.group(2), m.group(2)), protected_line)
            protected_line = re.sub(f'([,.?!:;])\\s*([“”‘’])', 
                          lambda m: punctuation_map.get(m.group(1), m.group(1)) + m.group(2), protected_line)
        
        # 恢复markdown语法
        line = restore_markdown(protected_line, md_parts)
        
        processed_lines.append(line)

    return "".join(processed_lines)

def process_file(file_pth, beg:int=200):
    output_pth = os.path.splitext(file_pth)[0] + '_corr.md'
    with open(file_pth, 'r', encoding='utf-8') as f:
        words = f.readlines()
    output_words = process_text(words, beg)
    with open(output_pth, 'w', encoding='utf-8') as wf:
        wf.write(output_words)


if __name__ == '__main__':
    process_file(r"D:\works\文档校正\未央河月：最终的编曲 虎山.md", 1)
    pass