import random
import time
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import csv

Headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

def fetch_titles_from_dili360(url, year, append_url:bool = False):
    """
    爬取中国国家地理网往期回顾页面的标题列表
    
    Args:
        url: 目标网页URL，例如 https://www.dili360.com/ch/mag/0/2011.htm
    
    Returns:
        list: 包含所有标题的列表
    """
    try:
        # 设置请求头，模拟浏览器访问

        
        # 获取网页内容
        print(f"正在访问: {url}")
        response = requests.get(url, headers=Headers, timeout=30)
        response.raise_for_status()  # 检查请求是否成功
        
        # 根据网页实际编码设置编码格式
        response.encoding = response.apparent_encoding
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        titles = []
        
        # 方式1：查找class为thumb-img的div中的标题（常见于列表页）
        # 根据搜索结果[^2^]，文章链接通常包含在thumb-img类的div中
        article_divs = soup.find_all('div', class_='detail')
        
        if article_divs:
            print(f"找到 {len(article_divs)} 个文章区块")
            for div in article_divs:
                # 在每个thumb-img div中查找a标签和可能的标题
                a_tag = div.find('a')
                if a_tag:
                    # 尝试从a标签的title属性获取标题
                    title = a_tag.get('title', '')
                    
                    # 如果title属性不存在，尝试从img的alt属性获取
                    if not title:
                        img_tag = a_tag.find('img')
                        if img_tag:
                            title = img_tag.get('alt', '')
                    
                    # 如果还是为空，尝试从链接文本获取
                    if not title:
                        title = a_tag.get_text(strip=True)
                    
                    if title:
                        qs = div.find('p').string.split()[0]
                        href = a_tag.get('href', '')
                        if qs.startswith('第'):
                            tit = f"{year}年{qs}@{title}"
                            titles.append(f"{tit}@{href}" if append_url else tit)
                            print(f"找到标题: {title}, 链接: {href}")
        
        # 方式2：如果方式1没有找到，尝试查找article中的h1标签（常见于详情页）
        # 根据搜索结果[^2^]，文章标题通常在article标签内的h1中
        if not titles:
            article_tag = soup.find('article')
            if article_tag:
                h1_tag = article_tag.find('h1')
                if h1_tag:
                    title = h1_tag.get_text(strip=True)
                    if title:
                        titles.append(title)
                        print(f"找到主标题: {title}")
        
        # 方式3：查找class为article-left的区域中的h1标签
        # 根据搜索结果[^2^]，某些页面使用article-left类
        if not titles:
            article_left = soup.find(class_='article-left')
            if article_left:
                h1_tag = article_left.find('h1')
                if h1_tag:
                    title = h1_tag.get_text(strip=True)
                    if title:
                        titles.append(title)
                        print(f"找到标题: {title}")
        
        # 方式4：通用方式 - 查找所有h1标签
        if not titles:
            h1_tags = soup.find_all('h1')
            for h1 in h1_tags:
                title = h1.get_text(strip=True)
                if title and len(title) > 10:  # 过滤掉过短的标题
                    titles.append(title)
                    print(f"找到h1标题: {title}")
        
        # 方式5：查找meta标签中的标题
        if not titles:
            meta_title = soup.find('meta', property='og:title')
            if not meta_title:
                meta_title = soup.find('meta', attrs={'name': 'title'})
            if meta_title:
                title = meta_title.get('content', '')
                if title:
                    titles.append(title)
                    print(f"找到meta标题: {title}")
        
        return titles
        
    except requests.RequestException as e:
        print(f"请求错误: {e}")
        return []
    except Exception as e:
        print(f"解析错误: {e}")
        return []


def extract_articles(url, base_url):
    """从列表页HTML中提取文章基本信息"""

    print(f"正在访问: {url}")
    response = requests.get(url, headers=Headers, timeout=30)
    response.raise_for_status()  # 检查请求是否成功
    
    # 根据网页实际编码设置编码格式
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = []
    # 查找所有文章项
    for item in soup.find_all('li'):
        try:
            article = {}
            
            # 提取图片区域的链接
            img_div = item.find('div', class_='detail')
            # print(img_div)
            if img_div:
                a_tag = img_div.find('a')
                if a_tag:
                    article['url'] = urljoin(base_url, a_tag['href'])
                    article['title'] = a_tag.get('title', '').strip()
                    
                    img_tag = a_tag.find('img')
                    if img_tag:
                        article['image_url'] = img_tag.get('src', '')
            
            # 提取详情区域
            detail_div = item.find('div', class_='detail')
            if detail_div:
                # 分类
                category_span = detail_div.find('span')
                if category_span:
                    article['category'] = category_span.get_text(strip=True)
                
                # 备用标题提取
                if not article.get('title'):
                    h3_tag = detail_div.find('h3')
                    if h3_tag:
                        title_a = h3_tag.find('a')
                        if title_a:
                            article['title'] = title_a.get_text(strip=True)
                
                # 摘要
                p_tags = detail_div.find_all('p')
                for p in p_tags:
                    if 'class' not in p.attrs:
                        article['summary'] = p.get_text(strip=True)
                        break
                
                # 作者
                tips_p = detail_div.find('p', class_='tips')
                if tips_p:
                    author_a = tips_p.find('a', class_='author')
                    if author_a:
                        article['author'] = author_a.get_text(strip=True)
                        article['author_url'] = urljoin(base_url, author_a['href'])
            
            # 只保留有效的文章数据
            if article.get('title') and article.get('url'):
                articles.append(article)
                print(f"提取: {article['title']}")
                
        except Exception as e:
            print(f"解析文章时出错: {e}")
            continue
    
    return articles

def fetch_all_titles():
    base_url = "https://www.dili360.com/"
    atits = []
    for y in range(2008, 2014):
        print(f"=== {y}年往期回顾 标题爬取 ===\n")
        target_url = f"https://www.dili360.com/ch/mag/0/{y}.htm"
        titles = fetch_titles_from_dili360(target_url, y, True)
        titles = titles[::-1]
        for title in titles:
            tjc, tnm, tref = title.split('@')
            tref = urljoin(base_url, tref)
            # tjc, tnm = t1.split('，')
            # tname = f"{t1}，[link]({tref})"
            adic = extract_articles(tref, base_url)
            for d in adic:
                d['volume'] = tjc
                d['main_title'] = tnm
                d['main_url'] = tref
            atits.extend(adic)
            time.sleep(random.random()*2+1)
    save_to_csv(atits, 'yc_articles1.csv')

def save_to_csv(data, filename):
    """保存数据到CSV文件"""
    if not data:
        return
    
    try:
        fields = ['volume', 'main_title', 'main_url', 'title', 'url', 'category', 'author', 'summary', 'image_url', 'author_url']
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for article in data:
                writer.writerow({field: article.get(field, '') for field in fields})
        print(f"CSV文件已保存: {filename}")
    except Exception as e:
        print(f"保存CSV失败: {e}")

def main():
    # 目标URL
    all_titles = []
    for y in range(2008, 2025):
        print(f"=== {y}年往期回顾 标题爬取 ===\n")
        target_url = f"https://www.dili360.com/ch/mag/0/{y}.htm"
        
        
        # 获取标题
        titles = fetch_titles_from_dili360(target_url, y)
        
        # 显示结果
        print(f"\n总共找到 {len(titles)} 个标题:")
        print("=" * 50)
        
        # for idx, title in enumerate(titles, 1):
        #     print(f"{idx}. {title}")
        all_titles.extend(titles)
        
    # 保存到文件
    # if all_titles:
    #     filename = "dili360_titles.txt"
    #     try:
    #         with open(filename, 'w', encoding='utf-8') as f:
    #             for title in all_titles:
    #                 f.write(f"{title}\n")
            
    #         print(f"\n标题已保存到文件: {filename}")
    #     except Exception as e:
    #         print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    turl = f"https://www.dili360.com/ch/mag/0/2020.htm"
    url1 = "https://www.dili360.com/ch/mag/detail/468.htm"
    base_url = "https://www.dili360.com/"
    # print(extract_articles(url1, base_url)[0])
    fetch_all_titles()
    # print(fetch_titles_from_dili360(turl, 2014, True))