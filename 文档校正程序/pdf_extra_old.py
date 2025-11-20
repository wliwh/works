import re
import fitz

pdf_pth = "d:\Docu\史学史\史学引论【第二版】 王学典.pdf"
first_line = re.compile(r'第.章.*\d+')

def get_page(pn:int):
    doc = fitz.open(pdf_pth)
    page = doc[pn]  # 第一页

    # text:str = page.get_text("text", sort=True, flags=fitz.TEXTFLAGS_TEXT)
    d    = page.get_text("dict")
    lines = []             # 用来保存 (文字, 矩形) 的列表
    for block in d["blocks"]:
        if block["type"] != 0:        # 0 = 文字块，跳过图片
            continue
        for line in block["lines"]:
            # 把同一行内的所有 span 的文字拼起来
            text = "".join(span["text"] for span in line["spans"])
            bbox = line["bbox"]       # (x0, y0, x1, y1)
            lines.append((text, bbox))

    # 打印结果
    for txt, (x0, y0, x1, y1) in lines:
        print(f"{txt!r:<30}  y={y0:.1f}–{y1:.1f}  x={x0:.1f}–{x1:.1f}")


if __name__ == '__main__':
    get_page(26)