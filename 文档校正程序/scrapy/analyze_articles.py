import os
import re
from datetime import datetime

def analyze_md_files(directory):
    date_pattern = re.compile(r'^\d{4}/\d{2}(/\d{2})?$')
    results = []
    total_md_files = 0
    matched_count = 0

    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return

    for filename in sorted(os.listdir(directory)):
        if filename.endswith('.md'):
            total_md_files += 1
            filepath = os.path.join(directory, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                continue

            # Find the first title
            title = None
            for line in lines:
                clean_line = line.strip()
                if clean_line.startswith('#'):
                    title = clean_line.lstrip('#').strip()
                    break
            
            # Find the last non-empty line
            last_line = ""
            for line in reversed(lines):
                if line.strip():
                    last_line = line.strip()
                    break
            
            # Check for date format
            if date_pattern.match(last_line):
                matched_count += 1
                results.append({
                    'title': title or filename,
                    'date_str': last_line,
                    'file_name': filename,
                    # For sorting, normalize YYYY/MM to YYYY/MM/99 to put it at the end of month
                    'sort_key': last_line if len(last_line) > 7 else f"{last_line}/99"
                })
            elif int(filename.split('[')[0]) < 70000:
                print(f"No date found in {filename}")
                pass

    # Sort results by date
    results.sort(key=lambda x: x['sort_key'])

    # Output stats
    print(f"Total Markdown files: {total_md_files}")
    print(f"Matched files (with date at end): {matched_count}")
    if total_md_files > 0:
        percentage = (matched_count / total_md_files) * 100
        print(f"Percentage: {percentage:.2f}%")
    print("-" * 40)
    
    # Output list
    for entry in results:
        date = entry['date_str']
        tab_str = "\t" if len(date) > 7 else "\t\t"
        # print(f"{date}{tab_str}{entry['file_name']}\t{entry['title']}")
        pass

if __name__ == "__main__":
    target_dir = "/home/hh01/Documents/works/文档校正程序/scrapy/articles_md"
    analyze_md_files(target_dir)
