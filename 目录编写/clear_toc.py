from collections import defaultdict
import csv
import hashlib
import os
import re
import shutil
from pathlib import Path
import pandas as pd
from typing import Iterable, List, Set, Union

os.chdir(os.path.dirname(__file__))
Base_Dir = os.path.dirname(__file__)
Path_Name = '.toc'
Toc_Name = 'name.txt'

def compare_txt_csv(name):
    txt_file = f'{name}.txt'
    csv_file = f'{name}.csv'
    csv = dict()
    with open(txt_file, 'r', encoding='utf-8') as f:
        txt = [l.strip() for l in f.readlines()]
    with open(csv_file,'r',encoding='utf-8') as f:
        for l in f.readlines():
            n,p = l.split('||')
            csv[n.strip()] = p.strip()
    return set(txt) - set(csv.keys()), set(csv.keys()) - set(txt)


def move_to_dir(name):
    csv = dict()
    pname = os.path.join(Base_Dir, name)
    if not os.path.exists(pname):
        raise FileNotFoundError("Not Found {pname}")
    with open(os.path.join(Base_Dir,f'{name}.csv'),'r',encoding='utf-8') as f:
        for l in f.readlines():
            n,p = l.split('||')
            csv[n.strip()] = p.strip()
    for p in csv.values():
        os.makedirs(os.path.join(pname, *p.split('-')), exist_ok=True)
    for n,p in csv.items():
        try:
            shutil.move(os.path.join(pname,n), os.path.join(pname, *p.split('-')))
        except FileNotFoundError as e:
            print(os.path.join(pname,n), p)
        except shutil.Error as e:
            print(e)

def extra_toc_from_note(file:str, spref:str='@', note:bool = False):
    title_name_pat = re.compile(r'^##\s([^#]+)$')
    l_name_pat = re.compile(r'(\s*)\*(\s+)([^\s]+)$')
    title_names, word_names = [], []
    with open(file,'r',encoding='utf-8') as f:
        for l in f.readlines():
            l = l.rstrip()
            t1 = title_name_pat.match(l)
            t2 = l_name_pat.match(l)
            if t1:
                tname = t1.group(1)
                if not tname.startswith(('修订','历史与地理')):
                    title_names.append(tname)
            elif t2:
                blk,lname = t2.group(1),t2.group(3)
                N1 = len(blk)//4 + 1
                N2 = lname.count(spref)
                if not lname.split('【')[0].strip():
                    continue
                if note is False:
                    lname = lname.split('【')[0]
                if N1!=N2:
                    print(t1,N1,N2, lname)
                    raise f"Find Class Error in {t1} {t2}."
                if lname.split('@')[0].startswith('历史与地理'):
                    continue
                else:
                    word_names.append(lname)
    wname = set([w.split(spref)[0] for w in word_names])
    assert set(title_names)==wname, "Find Title Error. " +str(wname-set(title_names))
    for t in title_names:
        for i,k in enumerate(word_names):
            if t==k.split(spref)[0]:
                word_names.insert(i, t)
                break
    with open('toc-list.txt','w',encoding='utf-8') as f:
        f.write('\n'.join(word_names))


def list_files_recursive(directory, extensions=None, exclude_dirs=None):
    """
    递归列出目录下的所有文件，支持扩展名过滤和目录排除
    
    Args:
        directory (str): 要遍历的根目录
        extensions (list): 要包含的文件扩展名列表（如 ['.txt', '.py']），None表示包含所有文件
        exclude_dirs (list): 要排除的目录名列表（如 ['__pycache__', '.git']），None表示不排除任何目录
    
    Returns:
        list: 匹配的文件路径列表
    """
    # 如果没有提供扩展名列表，则包含所有文件
    if extensions is None:
        extensions = []
    
    # 如果没有提供排除目录列表，则不排除任何目录
    if exclude_dirs is None:
        exclude_dirs = []
    
    # 将扩展名列表转换为小写，以便不区分大小写比较
    extensions = [ext.lower() for ext in extensions]
    
    # 将排除目录列表转换为集合，提高查找效率
    exclude_dirs = set(exclude_dirs)
    
    matched_files = []
    
    for root, dirs, files in os.walk(directory, topdown=True):
        # 排除指定目录：修改dirs列表，阻止os.walk递归进入这些目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            # 如果没有指定扩展名过滤，或者文件扩展名在允许列表中
            if not extensions or any(file.lower().endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                matched_files.append(file_path)    
    return matched_files

def iter_files(root: Union[str, Path], *,
               ext_list: Iterable[str] = (),
               exclude_dirs: Iterable[str] = ()) -> Iterable[Path]:
    """
    迭代返回 root 下所有常规文件（递归）。

    参数
    ----
    root : 起始目录
    ext_list : 需要的扩展名，可带或不含前导点，空序列表示“全部接受”
    exclude_dirs : 需要跳过的目录名（或绝对路径）集合/列表

    返回
    ----
    生成器，逐个 yield pathlib.Path 对象
    """
    root = Path(root).expanduser().resolve()
    ex_set: Set[str] = {d.lower() for d in exclude_dirs}

    # 预处理扩展名：统一成小写并带点
    if ext_list:
        want_exts = {e.lower() if e.startswith(".") else f".{e.lower()}"
                     for e in ext_list}
    else:
        want_exts = set()

    for p in root.rglob("*"):
        if p.is_file():
            # 目录排除：可按名或绝对路径
            if any(part.lower() in ex_set for part in p.parts):
                continue
            # 扩展名过滤
            if want_exts and p.suffix.lower() not in want_exts:
                continue
            yield p

def write_toc_file(pth, exclude_pth):
    file_toc = list()
    name_toc = list()
    if isinstance(exclude_pth, str): exclude_pth = tuple(exclude_pth)
    if isinstance(pth, str) or isinstance(pth, Path):
        pth = [pth]
    pth1 = pth[0]
    toc_file = Path(pth1) / Path_Name
    name_file = Path(pth1) / Toc_Name
    for p in pth:
        for f in iter_files(p, exclude_dirs=exclude_pth):
            if f.name in (Path_Name, Toc_Name): continue
            file_toc.append(str(f))
            name_toc.append(f.name)
    with open(toc_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(file_toc))
    with open(name_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(name_toc))

def get_file_md5(file_path, chunk_size=8192):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def compare_with_md5(origin_dst, comp_dst, *, ext_list=()):
    md1, md2 = dict(), dict()
    for p in iter_files(origin_dst, ext_list=ext_list):
        try:
            md5 = get_file_md5(p)
            md1[md5] = p
        except PermissionError as e:
            print(f'  @ {p}')
    for p in iter_files(comp_dst, ext_list=ext_list):
        try:
            md5 = get_file_md5(p)
            md2[md5] = p
        except PermissionError as e:
            print(f'  # {p}')
    add_mds = set(md2.keys()) - set(md1.keys())
    for a in add_mds:
        print('  *', md2[a])

def find_same_md5(dst, *, ext_list=()):
    md1 = defaultdict(list)
    cnt = 0
    for p in iter_files(dst, ext_list=ext_list):
        try:
            md5 = get_file_md5(p)
            md1[md5].append(p)
        except PermissionError as e:
            print(f'  @ {p}')
        cnt += 1
        print(str(cnt)+'\r')
    for k,v in md1.items():
        if len(v)>1:
            print(v)

def move_to_dir(base_dir, map_dir:dict, sign:str='@'):
    for k,v in map_dir.items():
        npth = Path(base_dir, *v.split(sign))
        os.makedirs(npth,exist_ok=True)
        try:
            shutil.move(k, npth)
        except shutil.Error as e:
            print(e)

def compare_with_names(pth, cls_pth = None):
    tname, pname = Path(pth) / Toc_Name, Path(pth) / Path_Name
    if not (tname.is_file() and pname.is_file()):
        print(tname.is_file())
        print('没有找到相应文件')
        return
    p2 = pd.read_csv(pname, sep=r'\|\|', encoding='utf-8', names=['name'], engine='python',quoting=csv.QUOTE_NONE)
    try:
        p1 = pd.read_csv(tname,sep=r'\|\|',encoding='utf-8',names=['name','class','desp'],engine='python',quoting=csv.QUOTE_NONE)
        if any(p1['class'].isna()):
            print('请进行分类 {}'.format(str(pth)))
            return
    except Exception as e:
        print('无法检查目录 {} [{}]'.format(str(pth), e))
        return
    p1_name = set(p1['name'])
    p2_name = set([Path(p).name for p in p2['name']])
    p1_cls = set(p1['class'])
    print('---------- 比较文件异同 ----------')
    print('  -- {}'.format(','.join(p1_name-p2_name)))
    print('  ++ {}'.format(','.join(p2_name-p1_name)))
    print('---------- 分类情况简报 ----------')
    print('  文件数: {}\t分类数: {}'.format(p1.shape[0], len(p1_cls)))
    if cls_pth:
        cname = pd.read_csv(cls_pth, encoding='utf-8', names=['class'])
        nclass = p1_cls-set(cname['class'])
        if nclass: print('  ++ {}'.format(','.join(list(nclass))))
    pth2class = dict()
    for p in p2.iterrows():
        k = p[1]['name']
        v = p1.loc[p1['name']==Path(k).name,'class']
        pth2class[k] = v.values[0]
    return pth2class


if __name__ == '__main__':
    bdir = r'/media/hh01/Elements SE/图书馆'
    allclasspth = r'/home/hh01/Documents/works/目录编写/toc-list.txt'
    tmp = r'/media/hh01/Elements SE/阿里/先秦史古籍/难解'
    # extra_toc_from_note('toc-mod.md',note=False)
    write_toc_file(tmp,())
    # gg = compare_with_names(tmp,allclasspth)
    # move_to_dir(bdir, gg)
    # compare_with_md5(bdir, r"e:\阿里\先秦史古籍")
    # find_same_md5(r'D:\Read\数学综合汇总')
    pass