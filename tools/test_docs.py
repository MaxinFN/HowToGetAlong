"""Check that history links preserve the named source rather than the latest record."""
import hashlib
import html
import re
from urllib.parse import unquote, urlsplit

from build_docs import ROOT, PAGES, rewrite_url


def main():
    records = sorted((ROOT / 'docs/核实记录').glob('*.md'))
    for record in records:
        target = rewrite_url(f'核实记录/{record.name}', 'docs/章节扩充资料-2026-10-04.md',
                             'docs/chapter-materials.html')
        assert target != 'verification.html', f'History must not point at the latest record: {record.name}'
        output = ROOT / 'docs' / unquote(urlsplit(target).path)
        assert output == ROOT / PAGES[record.relative_to(ROOT).as_posix()], record.name
        page = output.read_text(encoding='utf-8')
        digest = hashlib.sha256(record.read_bytes()).hexdigest()
        assert f'name="source-sha256" content="{digest}"' in page, record.name
    assert rewrite_url('核实记录/v1.15说明.md#整合范围', 'docs/研究资料整理.md',
                       'docs/research-notes.html') == 'history/v1.15说明.html#整合范围'
    notes_source = ROOT / 'docs/Morris账号整理/学习笔记.md'
    notes_page = ROOT / 'docs/Morris账号整理/阅读笔记.html'
    text = notes_page.read_text(encoding='utf-8')
    note_titles = re.findall(r'^### (\d{2}\. .+)$', notes_source.read_text(encoding='utf-8'), re.M)
    assert len(note_titles) == 24
    assert text.count('<section class="note-card"') == len(note_titles), 'Keep every searchable note'
    for title in note_titles:
        assert html.escape(title) in text, title
    assert text.count('<option value=') == 7, 'Keep six categories and the all-categories option'
    assert f'name="source-sha256" content="{hashlib.sha256(notes_source.read_bytes()).hexdigest()}"' in text
    assert rewrite_url('Morris账号整理/学习笔记.md', 'docs/访谈与博客学习笔记.md',
                       'docs/interview-notes.html') == 'Morris账号整理/阅读笔记.html'
    print(f'Document regression checks passed: {len(records)} distinct history records and source fingerprints.')


if __name__ == '__main__':
    main()
