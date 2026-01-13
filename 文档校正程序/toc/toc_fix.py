import re
import os

def toc_file_corr(file_pth:str, add_num:int = 0):
    toc_lst = list()
    with open(file_pth,'r',encoding='utf-8') as f:
        lines = f.readlines()
    for l in lines:
        l = l.strip()
        # lr = re.match(r'^(\d+)\s+[\(\)\-p\d:]+\s+(.+)',l)
        lr = re.match(r'[\(\)\.p\d]+\s+\(p(\d+)\)\s+(.+)',l)
        if lr:
            num = l.count(r'.')
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
    toc_file_corr(r"/home/hh01/Downloads/L/1引言.txt", 1)