import os
import re
from api_handler import create_api_handler
from tqdm import tqdm


POUNCT_MAPS = {
    ',': '，', '.': '。', ';': '；', ':': '：', '?': '？', '!': '！',
    '(': '（', ')': '）',
    # '[': '【', ']': '】', '{': '｛', '}': '｝',
    '<': '《', '>': '》',
    '-': '—', '_': '——',
    # '@': '＠', '#': '＃', '$': '￥', '%': '％', '^': '＾', '&': '＆', '*': '＊',
    # '+': '＋', '=': '＝', '|': '｜', '\\': '＼', '/': '／', '`': '｀', '~': '～'
}

Arange_Rules = """你是一个专业的文本编辑。你的任务是接收OCR识别后的文本，并严格按照以下要求进行处理和输出。请将下方“【待处理文本】”中的内容进行整理。

**任务要求:**

1.  **标点符号规范化:** 将文档中出现的所有标点符号都转换为中文标点符号。例如，将","替换为“，”，将"?"替换为“？”，将":"替换为“：”等。包括后面提到的注释。
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

Arange_Block_Rules = """你是一个专业的文本编辑。你的任务是接收OCR识别后的文本，并严格按照以下要求进行处理和输出。请将下方“【待处理文本】”中的内容进行整理。

**任务要求:**
1.  **错别字修正:** 识别并修正OCR过程中可能出现的常见错别字。
2.  **引文校订：** 文中`> `开头的文字表示引用文献，你要仔细核对校订，输出仍然用`> `开头，不要删去这一符号。
3.  **输出要求:** 你的最终输出应该是经过上述所有步骤处理后的完整文本，不要进行任何概括或总结，也不要添加额外内容。"""

# 创建API处理器实例
ark_handler = create_api_handler('ark')
ollama_handler = create_api_handler('ollama')

# ARK API基本参数
Ark_Basic_Args = dict(
    extra_headers={'x-is-encrypted': 'true'},
    temperature=1,
    max_tokens=8192,
    frequency_penalty=0,
    model='kimi-k2-250711',
    # model = 'doubao-1-5-pro-32k-250115',
)

# Ollama API基本参数
Oll_Basic_Args = dict(
    temperature=1,
    max_tokens=8192,
    frequency_penalty=0)

def get_page_with_number(fpth, beg=None, note:str='========='):
    res = list()
    work = False
    start = 1 if beg is None else beg
    n1, n2 = f"{note}{start}", f"{note}{start+1}"
    with open(fpth, 'r') as f:
        for l in f.readlines():
            if l.startswith(n1+'\n'):
                work = True
            elif l.startswith(n2+'\n'):
                work = False
            if work:
                res.append(l)
    return ''.join(res[1:]) if len(res)>2 else ''

def ai_correct_page(plain_text:str, agent_rule:str = Arange_Rules):
    messages = [
        {"role": "system", "content": agent_rule},
        {"role": "user", "content": plain_text}
    ]
    
    # 合并参数
    kwargs = Ark_Basic_Args.copy()
    kwargs['top_p'] = 0.97
    
    result = ark_handler.chat_completion(messages=messages, **kwargs)
    
    if result: return result
    else: return None

def write_correct_works(fpth, beg, end):
    note = '========='
    works = list()
    output_dir = os.path.splitext(fpth)[0]+'_correct4'+os.path.splitext(fpth)[1]
    for i in tqdm(range(beg, end)):
        page = get_page_with_number(fpth, i, note)
        res = ai_correct_page(page)
        first_line = f"{note}{i}"
        if res and len(res)>4:
            if "】" in res[-3:] or (len(res)<20 and len(page)>80):
                first_line += '*****'
            first_line += '\n'
        else:
            first_line += '=====\n'
            res = ''
        works.append(first_line+res+'\n')
    with open(output_dir,'w') as f:
        f.writelines(works)


def correct_with_blocks(fpth, beg:int=0, end:int=0):

    def is2correct(l, i, beg, end):
        if l.startswith(('#','**')):
            return False
        elif i<=beg:
            return False
        elif i>=end:
            return False
        elif l.strip()=='':
            return False
        return True
    
    res = list()
    opth = os.path.splitext(fpth)[0]+'_ai'+os.path.splitext(fpth)[1]
    with open(fpth,'r',encoding='utf-8') as f:
        fls = f.readlines()
        pbar = tqdm(total=len(fls))
        for i,l in enumerate(fls,1):
            if is2correct(l,i,beg,end):
                corr = ai_correct_page(l, Arange_Block_Rules)
                if corr:
                    if not corr.endswith('\n'): corr += '\n'
                    res.append(corr)
                else:
                    res.append(l)
            else:
                res.append(l)
            pbar.update(1)
    with open(opth, 'w', encoding='utf-8') as f:
        f.writelines(res)


if __name__ == '__main__':

    # write_correct_works("/home/hh01/Downloads/winfiles/通俗讲义/秦汉史讲义_已识别.txt",403,510)
    correct_with_blocks('/home/hh01/Downloads/winfiles/地方史/贵州通史简编_corr.md', 285, 1889)
    pass
