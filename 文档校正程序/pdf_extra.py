import fitz
import re


def get_pages_first(fpth:str):
    doc = fitz.open(fpth)
    result = list()
    for page_n, p in enumerate(doc, 1):
        page_res = p.get_text('blocks', sort=True)
        if page_res:
            page_res = [page_n] + list(page_res[0])
            if page_res[4]>82:
                result.append([page_res[0], page_res[5], page_res[4]])
    return result

def remove_headline(text_line):
    return text_line[4] < 82.4

def get_page_n(fpth:str, n:int):
    doc = fitz.open(fpth)
    page_n = doc[n].get_text('blocks', sort=True)
    starts_note_line = None
    page_notes = list()
    page_texts = list()
    note_num = 0
    for line_n, i in enumerate(page_n):
        text_line = (''.join(i[4].splitlines()), i[0],i[2],i[1],i[3],i[3]-i[1])
        if line_n==0 and remove_headline(text_line): continue
        if starts_note_line is None and i[4].strip().startswith(('@','＠','CD','©','(D')):
            starts_note_line = line_n
        if starts_note_line and line_n>=starts_note_line:
            page_notes.append(text_line)
        else:
            page_texts.append(text_line)
            if re.search(r'@|©|＠', text_line[0]):
                note_num +=1
    page_notes = ''.join([l[0] for l in page_notes])
    page_notes = page_notes.replace('＠','@').replace('CD','@').replace('©','@').replace('(D','@')
    return page_texts, page_notes.split('@')


if __name__ == '__main__':
    print(get_page_n('/home/hh01/Downloads/winfiles/冯天瑜著作/周制与秦制 冯天瑜.pdf', 227))