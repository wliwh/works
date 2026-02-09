import os
import re

def is_cjk(char):
    """检查一个字符是否是中日韩（CJK）统一表意文字或中文标点。"""
    if not char: return False
    # 汉字范围
    if '\u4e00' <= char <= '\u9fa5': return True
    # 中文标点及符号范围 (常见如 。，、？！：；（）“”‘’【】——)
    if '\u3000' <= char <= '\u303f' or '\uff00' <= char <= '\uffef': return True
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
            closing_puncts = ['。', '？', '！', '.', '?', '!', ':', '：']
            if not line1_stripped.startswith('#') and last_char not in closing_puncts:
                # 必须是 CJK 字符或逗号/顿号等非结束标点
                if is_cjk(last_char) or last_char in [',', '，', '、']:
                    cond1 = True

        cond2 = (line2 == '\n')
        cond3 = line3_stripped and not line3_stripped.startswith('#')

        if cond1 and cond2 and cond3:
            lines[i] = line1.rstrip('\r\n') + lines[i+2]
            del lines[i+2]
            del lines[i+1]
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
        if idx <= beg:
            processed_lines.append(line)
            continue
        
        if line.strip().startswith('![]('):
            processed_lines.append(line)
            continue

        # 检查是否包含中文。如果不含中文，视作英文行，不处理（满足要求2）
        if not any(is_cjk(c) for c in line):
            processed_lines.append(line)
            continue

        # 定义 CJK 字符类（含汉字和中文标点）
        cjk_class = r'[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]'

        # 任务2: 智能删除空格 (仅删除汉字之间的空格)
        line = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', line)

        # 任务2: 智能删除空格 (仅删除汉字之间的空格)
        line = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', line)

        # 任务4: 智能处理引号 (初次处理，基于上下文识别开关引号)
        line = replace_quotes_smartly(line)

        # 任务3: 智能转换标点 (满足要求1 & 2 & 3)
        # 多次循环以处理由于标点转换后产生的新 CJK 邻接关系（如 “你好”. -> “你好”。）
        cjk_class = r'[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]'
        for _ in range(2): 
            for eng_punc, chn_punc in punctuation_map.items():
                if eng_punc in '[]' and ('[' + eng_punc in line or eng_punc + '](' in line):
                    continue
                # 任务3.1: 转换英文标点为中文标点
                esc = re.escape(eng_punc)
                line = re.sub(f'({cjk_class})\\s*{esc}\\s*', f'\\1{chn_punc}', line)
                line = re.sub(f'{esc}\\s*({cjk_class})', f'{chn_punc}\\1', line)
                
            # 任务3.2: 额外处理已转换的引号与剩余英文标点的关系
            # 例如处理这种情况: "你好", -> “你好”，
            line = re.sub(f'([“”‘’])\\s*([,.?!:;])\\s*', 
                          lambda m: m.group(1) + punctuation_map.get(m.group(2), m.group(2)), line)
            line = re.sub(f'([,.?!:;])\\s*([“”‘’])', 
                          lambda m: punctuation_map.get(m.group(1), m.group(1)) + m.group(2), line)
        
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
    process_file(r"/home/hh01/Downloads/MinerU2.md", 41)
    pass