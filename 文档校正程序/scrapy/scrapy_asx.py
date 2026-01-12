import scrapy
import os
import re
import json
from urllib.parse import urljoin

class AsxSpider(scrapy.Spider):
    name = 'asx'
    # Reference URL: https://www.aisixiang.com/thinktank/xujilin.html
    start_urls = ['https://www.aisixiang.com/thinktank/xujilin.html']

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 1,
        'FEED_EXPORT_ENCODING': 'utf-8',
    }

    def __init__(self, toc=False, stats=False, *args, **kwargs):
        super(AsxSpider, self).__init__(*args, **kwargs)
        self.toc_only = str(toc).lower() in ('true', '1', 't', 'y', 'yes')
        self.stats_mode = str(stats).lower() in ('true', '1', 't', 'y', 'yes')
        self.output_dir = '/home/hh01/Documents/works/文档校正程序/scrapy/articles_md'
        self.all_articles = []
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.toc_path = os.path.join(self.output_dir, 'toc.json')

    def start_requests(self):
        """
        Custom start_requests to support offline stats mode.
        """
        if self.stats_mode and os.path.exists(self.toc_path):
            self.logger.info(f"Offline stats mode: skipping crawl, loading TOC from {self.toc_path}")
            return # This will trigger the closed method directly

        for url in self.start_urls:
            yield scrapy.Request(url, dont_filter=True)

    def parse(self, response):
        """
        Parses the author's page to extract article links and trigger content crawl.
        """
        for album in response.css('div.ablum_list.search_list'):
            category = album.css('h3::text').get()
            if category:
                category = category.strip()
            
            articles = album.css('div.thinktank-author-article-list ul li a')
            for article in articles:
                title = article.css('::text').get()
                link = article.css('::attr(href)').get()
                
                if title and link:
                    absolute_url = response.urljoin(link)
                    article_id_match = re.search(r'/data/(\d+)\.html', absolute_url)
                    if article_id_match:
                        article_id = article_id_match.group(1)
                        
                        article_item = {
                            'id': article_id,
                            'title': title.strip(),
                            'link': absolute_url,
                            'category': category
                        }
                        self.all_articles.append(article_item)

                        if self.toc_only or self.stats_mode:
                            if self.toc_only:
                                yield article_item
                            continue

                        file_name = f"{article_id}[{category}].md"
                        file_path = os.path.join(self.output_dir, file_name)
                        
                        # Resumable crawling: check if file already exists
                        if os.path.exists(file_path):
                            self.logger.info(f"Skipping existing file: {file_name}")
                            continue

                        yield scrapy.Request(
                            absolute_url,
                            callback=self.parse_article,
                            meta={'category': category}
                        )

    def parse_article(self, response):
        """
        Parses an article page to extract full content and save as Markdown.
        """
        category = response.meta.get('category')
        
        # Extract title
        title = response.css('div.show_text h3::text').get()
        if title:
            title = title.strip()
        
        # Extract info (reading count, update time)
        info_text = response.css('div.info::text').getall()
        info_text = "".join(info_text).strip()
        
        # Extract update time using regex
        update_time = ""
        time_match = re.search(r'更新时间：([\d\-\s:]+)', info_text)
        if time_match:
            update_time = time_match.group(1).strip()

        # Extract content
        content_div = response.css('div.article-content')
        paragraphs = content_div.css('p')
        content_lines = []
        for p in paragraphs:
            # Simple HTML to text conversion for paragraphs
            p_text = p.css('::text').getall()
            p_text = "".join(p_text).strip()
            if p_text:
                content_lines.append(p_text)

        # Extract footer info
        footer_p = response.xpath('//div[contains(@style, "clear:both")]/following-sibling::p[1]')
        
        footer_info = ""
        if footer_p:
            # Get all text nodes including those in <u> tags
            footer_texts = footer_p.xpath('.//text()').getall()
            footer_info = "".join(footer_texts).strip()

        # Prepare Markdown content
        md_content = f"## {title}\n\n- {update_time}\n\n"
        md_content += "\n\n".join(content_lines)
        md_content += f"\n\n---\n{footer_info}"

        # Save to file
        article_id = re.search(r'/data/(\d+)\.html', response.url).group(1)
        file_path = os.path.join(self.output_dir, f"{article_id}[{category}].md")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        self.logger.info(f"Saved: {file_path}")

        yield {
            'id': article_id,
            'title': title,
            'category': category,
            'url': response.url,
            'file_path': file_path
        }

    def closed(self, reason):
        """
        Save TOC and optionally display progress statistics.
        """
        if self.all_articles:
            with open(self.toc_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_articles, f, ensure_ascii=False, indent=4)
            self.logger.info(f"TOC saved to: {self.toc_path}")
        elif self.stats_mode and os.path.exists(self.toc_path):
            with open(self.toc_path, 'r', encoding='utf-8') as f:
                self.all_articles = json.load(f)
            self.logger.info(f"Loaded {len(self.all_articles)} articles from local TOC.")

        if self.stats_mode and self.all_articles:
            stats = {}
            for art in self.all_articles:
                cat = art.get('category') or "未分类"
                if cat not in stats:
                    stats[cat] = {'total': 0, 'downloaded': 0}
                
                stats[cat]['total'] += 1
                file_name = f"{art['id']}[{art['category']}].md"
                if os.path.exists(os.path.join(self.output_dir, file_name)):
                    stats[cat]['downloaded'] += 1
            
            self.logger.info("\n" + "="*40 + "\n爬取进度统计 (Progress Statistics):\n" + "="*40)
            total_all = 0
            downloaded_all = 0
            for cat, data in stats.items():
                percent = (data['downloaded'] / data['total'] * 100) if data['total'] > 0 else 0
                self.logger.info(f"[{cat}]: {data['downloaded']}/{data['total']} ({percent:.1f}%)")
                total_all += data['total']
                downloaded_all += data['downloaded']
            
            total_percent = (downloaded_all / total_all * 100) if total_all > 0 else 0
            self.logger.info("-" * 40)
            self.logger.info(f"总计 (TOTAL): {downloaded_all}/{total_all} ({total_percent:.1f}%)")
            self.logger.info("=" * 40 + "\n")
