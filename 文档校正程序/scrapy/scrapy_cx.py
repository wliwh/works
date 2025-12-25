import os
import time
import uuid
import requests
import unicodedata as ucd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re


Headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/114.0.0.0 Safari/537.36'
}
Base_Dir = os.path.dirname(__file__)
SAVE_DIR = os.path.join(Base_Dir, '..', '文档校正', 'jbzqh', 'assert')
Cata_Pth = os.path.join(Base_Dir, '..', '文档校正', 'jbzqh', 'catalog.txt')
Main_Url = "https://mooc1.chaoxing.com/mooc-ans/zt/242543846.html?_from_=&_fromV2_=&rtag=&nohead=1"
Page_Url = "https://mooc1.chaoxing.com/mooc-ans/ztnodedetailcontroller/visitnodedetail?courseId=242543846&knowledgeId={}&_from_=&_fromV2_=&rtag=&nohead=1"

def fetch_catalog(url, headers=Headers):
    """
    爬取超星学习通专题页面的目录结构
    """

    pat_name = re.compile(
        r'<div\b[^>]*?\bclass="[^"]*?\bf\d+\b[^"]*?\bpct70\b[^"]*?\bpr10\b[^"]*?\bl\b[^"]*?\bml10\b[^"]*?\bchapterText\b[^"]*"[^>]*>(.*?)</div>',
        re.S | re.I
    )
    pat_href = re.compile(r'<a\b[^>]*?\bclass="[^"]*?\bwh\b[^"]*?\bwh3\b[^"]*"[^>]+\bknowledgeId=(\d+)&[^>]+>', re.S | re.I)
    pat_index = re.compile(r'<div\b[^>]*?\bclass="[^"]*?\bf\d+\b[^"]*?\bchapter_index\b[^"]*?\bl">(.*?)</div>',re.S | re.I)
    # <a class="wh wh3" href="/mooc-ans/ztnodedetailcontroller/visitnodedetail?courseId=242543846&amp;knowledgeId=850487034&amp;_from_=&amp;_fromV2_=&amp;rtag=&amp;nohead=1">
	# 	<div class="f14 chapter_index l">1.2.1.3</div>
	# 	<div class="f14 pct70 pr10 l ml10 chapterText" style="word-wrap:break-word;word-break:break-word;">第三节　秦代的世界形势</div>
    try:
        html = requests.get(url, headers=headers, timeout=15).text
        if html:
            # 查找可能的目录结构
            catalog = []
            # 3. 提取并清洗
            item_name = pat_name.findall(html)
            item_href = pat_href.findall(html)
            item_index = pat_index.findall(html)
            catalog_name = [re.sub(r'<.*?>', '', txt).strip() for txt in item_name if txt.strip()]
            catalog_href = [re.sub(r'<.*?>', '', txt).strip() for txt in item_href if txt.strip()]
            catalog_index = [re.sub(r'<.*?>', '', txt).strip() for txt in item_index if txt.strip()]
            assert len(catalog_name) == len(catalog_href) and len(catalog_href) == len(catalog_index), "number wrong."
            # 4. 输出
            for idx, title in enumerate(catalog_name, 1):
                ci, chref = catalog_index[idx-1], catalog_href[idx-1]
                cline = '@@'.join([ci, title, chref])
                catalog.append(cline)
                # print(f'{idx:02d}. {cline}')
            return catalog
        else:
            print(f"请求失败")
            return None
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return None
    
def read_tocs(pth=Cata_Pth,index_node='.',start_index=1):
    if not os.path.exists(pth):
        return "请爬取目录 ..."
    names = list()
    with open(pth) as f:
        for l in f:
            names.append(l.strip().split('@@'))
    indexs = [list(map(int, n[0].split(index_node)[start_index:])) for n in names]
    max_depth = max([len(l) for l in indexs])
    indexs = [ i+([0]*(max_depth-len(i))) for i in indexs]
    indexs_len = [max([i[k] for i in indexs])//10 for k in range(max_depth)]
    indexs_str = dict()
    for i,name in zip(indexs,names):
        level_str = '_'.join('0'*l+str(num) for num,l in zip(i, indexs_len))
        level, nm, ref = name[0].count(index_node)-start_index+1, ucd.normalize('NFKC', name[1].strip()), Page_Url.format(name[2])
        indexs_str[level_str] = [level,nm,ref]
    return indexs_str
    
    
def get_html(url,headers=Headers):
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def download_img(src_url, save_dir, level_str, headders=Headers):
    """下载单张图片，返回相对路径（用于 MD）"""
    os.makedirs(save_dir, exist_ok=True)
    src_url = urljoin('', src_url)
    ext = os.path.splitext(urlparse(src_url).path)[1] or '.jpg'
    local_name = f"{level_str}@{uuid.uuid4().hex}{ext}"
    local_path = os.path.join(save_dir, local_name)
    try:
        pic = requests.get(src_url, headers=headders, timeout=15)
        pic.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(pic.content)
        print(f"[OK]  {src_url}  ->  {local_path}")
    except Exception as e:
        print(f"[ERR] {src_url} 下载失败: {e}")
        # 下载失败时返回原 url，避免断链
        return src_url
    # Markdown 用相对路径
    return os.path.join('.', save_dir, local_name).replace('\\', '/')


def html_to_md(soup_nodes,index_str):
    """
    递归把 BeautifulSoup 节点转成简单 Markdown
    支持 h1-h6、p、img、br，其余标签丢弃仅保留文本
    """
    md_lines = []
    for elem in soup_nodes:
        name = getattr(elem, 'name', None)
        if name is None:          # NavigableString
            text = str(elem).strip()
            if text:
                md_lines.append(text)
        elif name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(name[1])
            md_lines.append('\n' + '#' * level + ' ' + elem.get_text().strip() + '\n')
        elif name == 'p':
            md_lines.append('\n' + elem.get_text().strip() + '\n')
        elif name == 'img':
            src = elem.get('src') or elem.get('data-src')
            if src:
                local_src = download_img(src, SAVE_DIR, index_str)
                alt = elem.get('alt', '')
                md_lines.append(f'\n![{alt}]({local_src})\n')
        elif name == 'br':
            md_lines.append('\n')
    return ''.join(md_lines)


def extract_content_md(info,idx_str):
    """提取正文并转为 Markdown"""
    level, name, ref = info
    print(f"提取网页信息 {name}")
    html = get_html(ref)
    soup = BeautifulSoup(html, 'lxml')
    nodes = soup.select('img.picture_figure, p.content, p.footnote_content, img.picture_character, p.picture_figure_title')
    # md_sent = html_to_md(nodes)
    # print(md_sent)
    if nodes == []:
        md_sent = ''
    else:
        md_sent = html_to_md(nodes, idx_str)
    md_sent = '#'*(level+1)+f' {name}\n' + md_sent
    idx_pth = os.path.join(os.path.abspath(SAVE_DIR),'..',idx_str+'.md')
    with open(idx_pth,'w', encoding='utf-8') as f:
        f.write(''.join(md_sent))


def main():
    gg = read_tocs()
    for p,t in gg.items():
        if 33<int(p[:3].replace('_','')):
            # print(p, t)
            extract_content_md(t,p)
            time.sleep(1)

if __name__ == "__main__":
    # main()
    pass