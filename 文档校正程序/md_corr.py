import os
import re

def is_cjk(char):
    """检查一个字符是否是中日韩（CJK）统一表意文字（即汉字）。"""
    return '\u4e00' <= char <= '\u9fa5'

def replace_quotes_smartly(text):
    """
    智能地替换英文单双引号为中文对应引号。
    通过状态跟踪来判断是开引号还是闭引号。
    """
    in_single_quotes = False
    in_double_quotes = False
    result_chars = []

    for char in text:
        if char == "'":
            if not in_single_quotes:
                result_chars.append('‘')
                in_single_quotes = True
            else:
                result_chars.append('’')
                in_single_quotes = False
        elif char == '"':
            if not in_double_quotes:
                result_chars.append('“')
                in_double_quotes = True
            else:
                result_chars.append('”')
                in_double_quotes = False
        else:
            result_chars.append(char)
            
    return "".join(result_chars)


def process_text(lines, beg:int=0):
    """
    处理文本，执行四个主要操作：
    1. 合并特定模式的相邻三段。
    2. 删除非注释段落中的空格。
    3. 将英文标点替换为中文标点（除引号外）。
    4. 智能地替换英文引号为中文引号。
    """
    # --- 任务1: 处理相邻的三段 ---
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
            if not line1_stripped.startswith('#') and (is_cjk(last_char) or last_char in [',', '，','、']):
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
    
    # 定义英文到中文的标点转换映射 (不包括引号)
    punctuation_map = {
        ",": "，",
        ".": "。",
        "?": "？",
        "!": "！",
        ":": "：",
        ";": "；",
        "(": "（",
        ")": "）",
        "[": "【",
        "]": "】",
        "”":"\"",
        "“":"\"",
        "‘":"'",
        "’":"'"
    }

    for i,line in enumerate(lines):
        if i<=beg:
            processed_lines.append(line)
        else:
            # 任务2: 删去不是以#开头的段落中的空格
            if not line.strip().startswith('#'):
                line = line.replace(' ', '')

            if not line.strip().startswith('![]('):
                # 任务3: 将简单的英文标点换成中文
                for eng_punc, chn_punc in punctuation_map.items():
                    line = line.replace(eng_punc, chn_punc)
                    
                # 任务4: 智能地处理引号
                line = replace_quotes_smartly(line)
                
            processed_lines.append(line)

    return "".join(processed_lines)

def process_file(file_pth, beg:int=200):
    output_pth = os.path.splitext(file_pth)[0] + '_corr.md'
    with open(file_pth, 'r', encoding='utf-8') as f:
        words = f.readlines()
    output_words = process_text(words, beg)
    with open(output_pth, 'w', encoding='utf-8') as wf:
        wf.write(output_words)


def toc_file_corr(file_pth:str, add_num:int = 0):
    toc_lst = list()
    with open(file_pth,'r',encoding='utf-8') as f:
        lines = f.readlines()
    for l in lines:
        l = l.strip()
        lr = re.match(r'^(\d+)\s+[\(\)\-p\d:]+\s+(.+)',l)
        if lr:
            num = l.count('-')
            lr = lr.groups()
            nline = ' '*(4*num) + lr[1] + f' {(int(lr[0])+add_num)}'
            toc_lst.append(nline)
        else:
            toc_lst.append(l)
    out_pth = os.path.splitext(file_pth)[0] + '_corr.txt'
    with open(out_pth,'w',encoding='utf-8') as wf:
        wf.write('\n'.join(toc_lst))


if __name__ == '__main__':
    # process_file(r'/home/hh01/Downloads/works/文档校正/hrlA.md', 220)
    toc_file_corr(r"/home/hh01/Downloads/L/1引言.txt",6)