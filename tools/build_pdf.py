"""Generate the complete PDF from 完整指南.md (requires reportlab)."""
from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import argparse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'downloads' / '人情世故指南.pdf'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--font', default='/System/Library/Fonts/STHeiti Light.ttc',
    help='Path to a Chinese TrueType font (TTF or TTC); embedded in the PDF')
parser.add_argument('--bold-font', default='/System/Library/Fonts/STHeiti Medium.ttc',
    help='Path to the bold Chinese TrueType font; embedded in the PDF')
args = parser.parse_args()
pdfmetrics.registerFont(TTFont('GuideChinese', args.font, subfontIndex=0))
pdfmetrics.registerFont(TTFont('GuideChineseBold', args.bold_font, subfontIndex=0))
pdfmetrics.registerFontFamily('GuideChinese', normal='GuideChinese',
    bold='GuideChineseBold', italic='GuideChinese', boldItalic='GuideChineseBold')
green = colors.HexColor('#243d32')
body = ParagraphStyle('body', fontName='GuideChinese', fontSize=10.5,
    leading=17, textColor=green, spaceAfter=7, wordWrap='CJK')
chapter = ParagraphStyle('chapter', parent=body, fontName='GuideChineseBold', fontSize=20, leading=29,
    spaceAfter=18, keepWithNext=True)
heading = ParagraphStyle('heading', parent=body, fontName='GuideChineseBold', fontSize=14, leading=22,
    spaceBefore=14, spaceAfter=10, keepWithNext=True)
example = ParagraphStyle('example', parent=body, backColor=colors.HexColor('#eef4ed'),
    borderPadding=8, spaceBefore=4, spaceAfter=12)

def markup(text):
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
    return escape(text.replace('**', '').replace('`', ''))

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('GuideChinese', 9)
    canvas.setFillColor(colors.HexColor('#65756b'))
    canvas.drawString(46, 27, '人情世故指南 · 经验建议')
    canvas.drawRightString(A4[0]-46, 27, str(doc.page))
    canvas.restoreState()

class GuideDoc(SimpleDocTemplate):
    def beforeDocument(self):
        self.chapter_index = 0

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == 'chapter':
            title = flowable.getPlainText()
            if title == '目录':
                return
            key = 'chapter-%d' % self.chapter_index
            self.chapter_index += 1
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, 0)
            self.notify('TOCEntry', (0, title, self.page, key))

def build():
    OUT.parent.mkdir(exist_ok=True)
    story = [Spacer(1, 34), Image(str(ROOT/'docs/assets/cover.png'),
        width=A4[0]-92, height=(A4[0]-92)*9/16), Spacer(1, 30)]
    lines = (ROOT/'完整指南.md').read_text().splitlines()
    first_title = True
    in_body = False
    for line in lines:
        line=line.strip()
        if not line or line.startswith('<!--'):
            continue
        if line.startswith('# '):
            if first_title:
                first_title = False
                continue
            if not in_body:
                story.extend([PageBreak(), Paragraph('目录', chapter)])
                toc = TableOfContents()
                toc.levelStyles = [ParagraphStyle('toc', parent=body,
                    leading=24, spaceAfter=8)]
                toc.dotsMinLevel = 0
                story.append(toc)
            story.append(PageBreak())
            in_body = True
            story.append(Paragraph(markup(line[2:]), chapter))
        elif line.startswith(('## ', '### ')):
            story.append(Paragraph(markup(line.lstrip('# ')), heading))
        else:
            text = line[2:] if line.startswith('- ') else line
            style = example if text.startswith(('可以怎么说：','原创示例：')) else body
            rendered = markup(text)
            if in_body:
                if '：' in text and line.startswith('- '):
                    label, content = text.split('：', 1)
                    rendered = '<b>' + markup(label + '：') + '</b><u>' + markup(content) + '</u>'
                else:
                    rendered = '<u>' + rendered + '</u>'
            story.append(Paragraph(rendered, style))
    GuideDoc(str(OUT), pagesize=A4, rightMargin=46, leftMargin=46,
        topMargin=45, bottomMargin=49, title='人情世故指南', author='HowToGetAlong',
        pageCompression=1).multiBuild(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)

if __name__ == '__main__':
    build()
