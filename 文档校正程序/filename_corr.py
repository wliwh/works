import json
import os
from pathlib import Path
import shutil
from handle.api_handler import create_api_handler
os.chdir(Path(__file__).parent)

Rename_Prompt = """书名提取工具，从若干书名中提取信息，输出要求为json格式。
输入信息为编号和待处理书名，一行一个，格式为'编号====待处理书名'

提取出的信息包括
1. 原文件名（包括扩展名）[filename]
2. 编号[id]，参看输入格式
2. 书名[title]，如果书名为主标题+副标题的格式，需输出为‘主标题：副标题’，注意不要将版本号、系列号等放在这里
3. 作者名（或者编者）[author]，取一个即可，如果原书名标识该人为外国人或古代人，则使用‘[国名/朝代]+人名’
4. 版本号、系列号等[series]，例如中国思想史-第2卷、修订版
5. 是否能够修改原名[modify]
注意，输出的json中的项需用上面[]中的英文命名

下面是待处理书名列表"""


ollama_handle = create_api_handler('ollama')
Oll_Basic_Args = dict(model='qwen3:8b', top_p=0.97, temperature=1, max_tokens=8192, frequency_penalty=0)
ark_handler = create_api_handler('ark')
Ark_Basic_Args = dict(
    extra_headers={'x-is-encrypted': 'true'},
    # top_p=0.97,
    temperature=1,
    max_tokens=8192,
    frequency_penalty=0,
    model='kimi-k2-250711',
    # model = 'doubao-1-5-pro-32k-250115',
)
Basic_EXTs = 'txt pdf epub mobi azw3 djvu md zip rar uvz'.split()
Corr_Name_Path = 'filename_corr_tmp'
Corr_Name_Json = 'filename_corr.json'
Corr_Name_Plain = 'filename_corr.txt'


def find_files_by_extensions_pathlib(directory, extensions=Basic_EXTs, case_sensitive=False):
    """
    使用pathlib递归查找匹配扩展名的文件
    """
    # 处理扩展名
    normalized_extensions = []
    for ext in extensions:
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized_extensions.append(ext)
    
    if not case_sensitive:
        normalized_extensions = [ext.lower() for ext in normalized_extensions]
    
    path = Path(directory)
    matched_files = []
    
    # 递归遍历目录
    for file_path in path.rglob('*'):
        if file_path.is_file():
            file_ext = file_path.suffix
            if not case_sensitive:
                file_ext = file_ext.lower()
            
            if file_ext in normalized_extensions:
                matched_files.append(str(file_path))
    
    with open(Corr_Name_Path,'w', encoding='utf-8') as f:
        f.write('\n'.join(matched_files))

def ai_correct_name(plain_text:str, model:str='qwen3:8b', agent_rule:str = Rename_Prompt):
    messages = [
        {"role": "system", "content": agent_rule},
        {"role": "user", "content": plain_text}
    ]
    
    # 合并参数
    kwargs = Ark_Basic_Args.copy()
    # kwargs.update(model = model)
    result = ark_handler.chat_completion(messages=messages, **kwargs)
    return result


def filename_corr(chunk_size:int = 10, model:str='gpt-oss:latest'):
    names = list()
    with open(Corr_Name_Path, 'r', encoding='utf-8') as f:
        for i,l in enumerate(f):
            bnm = str(Path(l.strip()).name)
            names.append(str(i)+'===='+bnm)
    assert len(names)>=2, 'names wrong.'

    if not os.path.isfile(Corr_Name_Json):
        Path(Corr_Name_Json).touch()
    else:
        os.remove(Corr_Name_Json)
        Path(Corr_Name_Json).touch()
    
    N = (len(names)-1)//chunk_size + 1
    with open(Corr_Name_Json,'r+',encoding='utf-8') as f:
        for i in range(N):
            name_str = '\n'.join(names[i*chunk_size:i*chunk_size+chunk_size])
            js = ai_correct_name(name_str)
            f.write(js+'\n')
            print(f'\r进度: {i*chunk_size}-{i*chunk_size+chunk_size}', flush=True)

def gene_dir_filename(dir):
    find_files_by_extensions_pathlib(dir)
    names = list()
    with open(Corr_Name_Path, 'r', encoding='utf-8') as f:
        for l in f:
            bnm = str(Path(l.strip()).name)
            names.append(bnm)
    with open(Corr_Name_Plain, 'w', encoding='utf-8') as f:
        f.write('\n'.join(names))

def rename_file():
    lnames = dict()
    with open(Corr_Name_Path, 'r', encoding='utf-8') as f:
        for i,l in enumerate(f):
            bnm = str(Path(l.strip()))
            lnames[i] = bnm
    with open(Corr_Name_Json, 'r', encoding='utf-8') as jf:
        js = json.load(jf)
    for j in js:
        if j.get('id') and int(j['id']) in lnames:
            id = int(j['id'])
            title = j['title']
            author = j['author'].strip()
            series = j['series'].strip()
            suf = Path(lnames[id]).suffix
            if j['modify']:
                all_name = title
                if author: all_name += (' '+author)
                if series: all_name += f'【{series}】'
                all_name += suf
                ndir = Path(lnames[id]).parent / all_name
                try:
                    shutil.move(str(lnames[id]), str(ndir))
                except FileNotFoundError as e:
                    print(j)
            else:
                print(j)
        else:
            print(j)

if __name__ == '__main__':
    # aa = find_files_by_extensions_pathlib('/home/hh01/Downloads/winfiles/历史文化/古籍')
    gene_dir_filename(r"/home/hh01/Downloads/winfiles/花钱买的书")
    # filename_corr(20)
    # rename_file()
    # filename_corr()
    pass