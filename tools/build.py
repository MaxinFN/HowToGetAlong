#!/usr/bin/env python3
"""Validate canonical Markdown; build an offline searchable page and Skill snapshot."""
from pathlib import Path
import json
import re
import shutil
import html
from sources import load_sources

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['判断关键', '行动前准备', '何时换办法', '遇到的情况', '先做什么', '可以怎么说', '分情境处理', '花掉什么', '可能换回什么', '例外与代价', '依据', '相关条目']

def read_entries():
    entries, chapters = [], []
    for file in sorted((ROOT / 'book').glob('[0-9][0-9]-*.md')):
        source = file.read_text(encoding='utf-8')
        chapter = int(file.name[:2])
        chapter_title = source.splitlines()[0].removeprefix('# ')
        chapters.append({'number': chapter, 'title': chapter_title, 'file': file.name})
        parts = re.split(r'^### (\d+)\. (.+)$', source, flags=re.M)
        numbers = []
        for i in range(1, len(parts), 3):
            number, title, body = int(parts[i]), parts[i + 1], parts[i + 2]
            numbers.append(number)
            pairs = re.findall(r'^- ([^：\n]+)：(.+)$', body, re.M)
            fields = dict(pairs)
            if len(pairs) != len(fields):
                raise ValueError(f'{file.name} 第{number}条字段重复')
            missing = set(REQUIRED) - fields.keys()
            if missing or not any(key.startswith('如果') for key in fields):
                raise ValueError(f'{file.name} 第{number}条字段不完整：{missing}')
            tag_match = re.search(r'<!-- 标签: (.+?) -->', body)
            if not tag_match:
                raise ValueError(f'{file.name} 第{number}条缺少标签')
            tags = {}
            for pair in tag_match[1].split():
                key, value = pair.split('=', 1)
                tags[key] = re.split('[,，]', value)
            if set(tags) != {'场景', '对象', '主题'}:
                raise ValueError(f'{file.name} 第{number}条标签不完整')
            for key, values in tags.items():
                if any(not value.strip() for value in values) or len(values) != len(set(values)):
                    raise ValueError(f'{file.name} 第{number}条{key}标签为空或重复')
            entries.append({'id': f'{chapter}.{number}', 'chapter': chapter,
                'chapterTitle': chapter_title, 'title': title, 'fields': fields,
                'tags': tags, 'source': f'book/{file.name}'})
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f'{file.name} 条号不连续')
    if [c['number'] for c in chapters] != list(range(1, len(chapters) + 1)):
        raise ValueError('章节编号不连续')
    if not entries:
        raise ValueError('没有正文')
    ids = {entry['id'] for entry in entries}
    if len(ids) != len(entries):
        raise ValueError('条目编号重复')
    for entry in entries:
        if not entry['fields']['依据'].startswith('经验建议。'):
            raise ValueError(f'{entry["id"]} 增加新依据类型后须更新页面依据展示')
        for target in re.findall(r'\b\d+\.\d+\b', entry['fields']['相关条目']):
            if target not in ids:
                raise ValueError(f'{entry["id"]} 引用了不存在的条目 {target}')
    return entries, chapters

PAGE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAME__</title>
<meta name="description" content="校园、实习与日常交往的相处指南。每条写清做法、示例表达、可能代价与例外。">
<style>
:root{--ink:#20382f;--muted:#64736b;--green:#225a43;--paper:#f7f5ee;--line:#dce1d7}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.8}a{color:var(--green);text-underline-offset:4px}button,input,select{font:inherit}button,select{cursor:pointer}header,main,footer{max-width:1120px;margin:auto;padding:0 28px}.top{display:flex;justify-content:space-between;gap:20px;padding:24px 0;border-bottom:1px solid var(--line);font-size:13px;letter-spacing:.06em}.brand{font-weight:700}.top{flex-wrap:wrap}.navlinks{display:flex;gap:8px 16px;flex-wrap:wrap;align-items:center}.top a{text-decoration:none}.hero{padding:60px 0 36px;max-width:900px}.eyebrow{font-size:12px;letter-spacing:.16em;color:var(--green);font-weight:700}h1{font-family:"Songti SC","Noto Serif CJK SC",serif;font-size:clamp(32px,5vw,54px);line-height:1.3;letter-spacing:-.025em;margin:16px 0 20px}h1 span{display:block}.lead{font-size:18px;max-width:680px;margin:0}.note{font-size:13px;color:var(--muted);max-width:750px;margin-top:22px}.toolbar{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:22px}.search{display:block;font-weight:600;font-size:13px;margin-bottom:8px}input{width:100%;padding:13px 15px;border:1px solid #b8c8bc;border-radius:8px;background:#fcfdfb;color:var(--ink)}input:focus,select:focus,button:focus-visible,summary:focus-visible{outline:3px solid #9fc6af;outline-offset:3px}.filters{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:14px}.filters label{font-size:13px;color:var(--muted)}select{margin-left:7px;padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:white;color:var(--ink);max-width:100%}button{border:0;background:#eaf0e9;color:var(--green);border-radius:6px;padding:8px 12px;font-size:13px}.search-actions{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-top:18px}#search-submit{background:var(--green);color:white;min-width:84px;padding:9px 18px}.resultline{display:flex;align-items:center;justify-content:space-between;gap:12px;color:var(--muted);font-size:13px;margin:20px 0}#list{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start}.card{background:white;border:1px solid var(--line);border-radius:12px;padding:23px;scroll-margin-top:24px}.cardhead{font-size:12px;color:var(--muted);display:flex;justify-content:space-between;gap:8px}.card h2{font-size:20px;line-height:1.55;margin:12px 0}.card .scene{color:var(--muted);font-size:14px;margin:0 0 16px}.judgment{font-size:14px;padding:0;background:transparent;margin:0 0 18px}.judgment strong{display:block;font-size:16px;color:var(--green);margin-bottom:3px}.action{font-size:14px;margin:0 0 14px}.action strong{color:var(--green);display:block;font-size:16px;margin-bottom:3px}.example-label{font-size:16px;color:var(--green);font-weight:650;margin:0 0 8px}blockquote{background:#f0f5ee;border:1px solid #d2dfce;border-radius:6px;margin:0 0 14px;padding:8px 12px;font-size:14px;width:fit-content;max-width:100%}.chips{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}.chip{font-size:11px;background:#f4f4ef;color:var(--muted);padding:2px 8px;border-radius:20px}summary{font-size:13px;color:var(--green);cursor:pointer;padding:8px 0}dl{font-size:13px;margin:10px 0}dt{font-size:16px;color:var(--green);font-weight:650;margin-top:20px}dd{margin:3px 0;color:#53645a;overflow-wrap:anywhere}.refs{margin-top:16px;padding-top:12px;border-top:1px solid var(--line);font-size:12px}.refs a{display:inline-block;margin-right:12px}.source{font-size:12px;color:var(--muted);margin-top:10px}.empty{grid-column:1/-1;padding:48px;text-align:center;border:1px dashed #b9c9bb;border-radius:12px}.guide{margin-top:46px;padding:26px 0;border-top:1px solid var(--line);max-width:800px}.guide h2{font-size:19px}.guide p{font-size:14px;color:var(--muted)}footer{padding-top:22px;padding-bottom:35px;font-size:12px;color:var(--muted)}.card:target{outline:2px solid #588b68}noscript{display:block;padding:20px;background:#fff1db}@media(max-width:700px){header,main,footer{padding-left:18px;padding-right:18px}.hero{padding-top:36px}.lead{font-size:16px}#list{grid-template-columns:1fr}.card{padding:20px}.filters{align-items:stretch}.filters label{width:100%;display:flex;align-items:center;justify-content:space-between}.filters select{width:78%}.top{font-size:11px}.resultline{align-items:flex-start}}@media print{.toolbar,.top,#expand{display:none}#list{display:block}.card{break-inside:avoid;margin-bottom:18px}details{display:block}h1{font-size:30px}}
</style></head><body>
<header><div class="top"><span class="brand">__NAME__ · FIRST EDITION</span><a href="README.md">项目说明 ↗</a></div><div class="hero"><div class="eyebrow">校园 / 实习 / 日常交往</div><h1>__NAME__</h1><p class="lead">遇到难开口的事，先看清情况，<br>再决定怎么说、怎么做。</p><p class="note">__COUNT__ 个场景 · 每条都有判断、准备、做法、示例、代价与调整信号。<br>这是经验建议初稿，没有验证成功率；示例可以调整，对方也有拒绝的空间。</p></div></header>
<main><section class="toolbar" aria-label="查找场景"><label class="search" for="query">你遇到了什么？</label><input id="query" type="search" placeholder="试试：改作业、借钱、没回复、不喝酒……" autocomplete="off"><div class="filters"><label for="chapter">章节<select id="chapter"><option value="">全部章节</option></select></label><label for="topic">主题<select id="topic"><option value="">全部主题</option></select></label><label for="person">对象<select id="person"><option value="">全部对象</option></select></label></div><div class="search-actions"><button id="search-submit" type="button">搜索</button><button id="reset" type="button">清除筛选</button></div></section><div class="resultline"><span id="count" role="status" aria-live="polite"></span><button id="expand" type="button">展开全部细节</button></div><noscript>阅读页需要启用 JavaScript。也可以直接打开 <a href="阅读全文.html">连续阅读版</a> 阅读全部正文。</noscript><section id="list" aria-label="建议条目"></section><section class="guide"><h2>怎么用这份指南</h2><p>想练习一次交流？<a href="阅读全文.html#practice">打开复盘卡与场景练习</a>。</p><p>先找相近场景，回答“判断关键”，再看“先做什么”与示例表达。展开细节后，检查行动前准备、不同情境、代价与“何时换办法”。一个办法可能让关系更清楚，也可能引起不满，没有保证双方都满意的万能话术。</p><p>本版所有条目均为经验建议。涉及学校、单位、合同和法律的实际要求，需核对适用规则。<a href="docs/editorial-guide.html">编写与纠错规范</a> · <a href="docs/sources.html">选题来源与限制</a> · <a href="docs/Morris账号整理/阅读笔记.html">Morris 来源笔记</a> · <a href="docs/interview-notes.html">访谈与博客笔记</a> · <a href="docs/research-notes.html">论文与文章资料</a></p></section></main><footer>v0.1 · 2026-10-02 · 初版 __CHAPTERS__ 章 __COUNT__ 条 · 根据自己的情况选择，不用全部做到。</footer>
<script id="entries" type="application/json">__DATA__</script>
<script>__SEARCH_SCRIPT__
</script></body></html>'''

def main():
    entries, chapters = read_entries()
    meta = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    data = json.dumps(entries, ensure_ascii=False).replace('<', '\\u003c')
    page = PAGE.replace('__DATA__', data).replace('__COUNT__', str(len(entries))).replace('__CHAPTERS__', str(len(chapters)))
    page = page.replace('__NAME__', html.escape(meta['name']))
    page = page.replace('__SEARCH_SCRIPT__', (ROOT / 'tools/search.js').read_text(encoding='utf-8'))
    page = page.replace('<a href="docs/research-notes.html">论文与文章资料</a>', '<a href="docs/research-notes.html">论文与文章资料</a> · <a href="docs/platform-notes.html">短视频与网络素材</a>')
    page = page.replace('FIRST EDITION', 'PRACTICAL GUIDE')
    page = page.replace('<a href="README.md">项目说明 ↗</a>', '<span class="navlinks"><a href="阅读全文.html">阅读全文 ↗</a><a href="downloads/人情世故指南.pdf" download>下载 PDF</a><a href="docs/practice.html">场景练习</a><a href="about.html">项目说明 ↗</a></span>')
    page = page.replace('这是经验建议初稿，没有验证成功率', '本版全部为经验建议，未验证成功率')
    page = page.replace('校园 / 实习 / 日常交往', '校园 / 求职 / 职场 / 日常交往')
    page = page.replace('试试：改作业、借钱、没回复、不喝酒……', '试试：内推、借钱、送礼、被批评、离职……')
    page = page.replace('阅读五章 Markdown', '阅读分章正文')
    page = page.replace('查看代价、后续做法与例外', '查看准备、不同情境与调整信号')
    page = page.replace('v0.1 · 2026-10-02 · 初版', f'v{meta["version"]} · {meta["date"]} ·')
    disclaimer_html = '<p class="note"><strong>免责声明：仅供参考。</strong> ' + html.escape(meta['disclaimer']) + '</p>'
    page = page.replace('</div></header>', disclaimer_html + '</div></header>', 1)
    (ROOT / 'index.html').write_text(page, encoding='utf-8')
    download_page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>下载 HTML · 人情世故指南</title><style>body{max-width:700px;margin:64px auto;padding:0 24px;background:#f7f5ee;color:#20382f;font:16px/1.9 -apple-system,"PingFang SC",sans-serif}a{color:#225a43}.download{display:inline-block;padding:12px 20px;background:#225a43;color:white;border-radius:8px;text-decoration:none}</style></head><body><h1>下载 HTML 检索页</h1><p>下载的是项目 ZIP 里的 index.html。保存后，用浏览器打开即可离线搜索和查看全部条目。</p><p><a id="download" class="download" href="../index.html" download="index.html">下载 index.html</a></p><p>正在开始下载。如果浏览器没有自动下载，请点击上面的按钮。</p><p>其他阅读页和资料需要配套文件。需要完整离线使用，可 <a href="https://github.com/kkk-bot/HowToGetAlong/archive/refs/heads/main.zip">下载项目 ZIP</a>。</p><p><a href="../index.html">返回在线检索页</a></p><script>document.getElementById('download').click();</script></body></html>'''
    (ROOT / 'downloads').mkdir(exist_ok=True)
    (ROOT / 'downloads/html.html').write_text(download_page, encoding='utf-8')
    refs = ROOT / 'skills/social-situations-guide/references'
    target = refs / 'book'
    target.mkdir(parents=True, exist_ok=True)
    for old in target.glob('*.md'):
        old.unlink()
    for chapter in chapters:
        shutil.copyfile(ROOT / 'book' / chapter['file'], target / chapter['file'])
    toc = f'# 正文目录\n\n版本：v{meta["version"]}；快照日期：{meta["date"]}；全部为经验建议。\n\n'
    toc += '**免责声明：仅供参考。** ' + meta['disclaimer'] + '\n\n'
    toc += '\n'.join(f'- [{c["title"]}](book/{c["file"]})' for c in chapters) + '\n'
    practice = (ROOT / 'docs/交流复盘与场景练习.md').read_text(encoding='utf-8')
    shutil.copyfile(ROOT / 'docs/交流复盘与场景练习.md', refs / '交流复盘与场景练习.md')
    toc += '\n- [附录：交流复盘与场景练习](交流复盘与场景练习.md)\n'
    toc += '\n- [Morris 来源笔记](Morris账号公开内容学习笔记.md)\n- [v1.4 整合记录](v1.4整合记录.md)\n'
    (refs / '目录.md').write_text(toc, encoding='utf-8')
    (refs / 'Morris账号公开内容学习笔记.md').write_text((ROOT / 'docs/Morris账号整理/学习笔记.md').read_text(encoding='utf-8'), encoding='utf-8')
    (refs / 'v1.4整合记录.md').write_text((ROOT / 'docs/核实记录/v1.4说明.md').read_text(encoding='utf-8').replace('../Morris账号整理/学习笔记.md', 'Morris账号公开内容学习笔记.md'), encoding='utf-8')
    shutil.copyfile(ROOT / 'docs/访谈与博客学习笔记.md', refs / '访谈与博客学习笔记.md')
    (refs / '访谈与博客学习笔记.md').write_text((refs / '访谈与博客学习笔记.md').read_text(encoding='utf-8').replace('核实记录/v1.6说明.md', 'v1.6整合记录.md'), encoding='utf-8')
    (refs / 'v1.6整合记录.md').write_text((ROOT / 'docs/核实记录/v1.6说明.md').read_text(encoding='utf-8').replace('../访谈与博客学习笔记.md', '访谈与博客学习笔记.md'), encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [访谈与博客学习笔记](访谈与博客学习笔记.md)\n- [v1.6 整合记录](v1.6整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.7说明.md', refs / 'v1.7整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.7 敬酒表达整合记录](v1.7整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.8说明.md', refs / 'v1.8整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.8 场面话整合记录](v1.8整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.9说明.md', refs / 'v1.9整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.9 表达顺序整合记录](v1.9整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.10说明.md', refs / 'v1.10整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.10 社交摘要整合记录](v1.10整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.11说明.md', refs / 'v1.11整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.11 识人技巧整合记录](v1.11整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.12说明.md', refs / 'v1.12整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.12 平和回应整合记录](v1.12整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.13说明.md', refs / 'v1.13整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.13 回应夸奖新增记录](v1.13整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.14说明.md', refs / 'v1.14整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.14 十章情境深化记录](v1.14整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.14.1说明.md', refs / 'v1.14.1整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.14.1 检索与跳转修复记录](v1.14.1整合记录.md)\n')
    (refs / '研究资料整理.md').write_text((ROOT / 'docs/研究资料整理.md').read_text(encoding='utf-8').replace('核实记录/v1.15说明.md', 'v1.15整合记录.md').replace('](editorial-guide.md)', '](https://kkk-bot.github.io/HowToGetAlong/docs/editorial-guide.html)'), encoding='utf-8')
    (refs / 'v1.15整合记录.md').write_text((ROOT / 'docs/核实记录/v1.15说明.md').read_text(encoding='utf-8').replace('../研究资料整理.md', '研究资料整理.md'), encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [论文与文章资料笔记](研究资料整理.md)\n- [v1.15 论文与文章整合记录](v1.15整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/平台素材收集-2026-10-04.md', refs / '平台素材收集-2026-10-04.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [短视频与网络文章候选素材](平台素材收集-2026-10-04.md)\n')
    full = f'# {meta["name"]}\n\n{meta["positioning"]}\n\nv{meta["version"]} · {meta["date"]} · {len(chapters)} 章 {len(entries)} 条\n\n'
    full += '先判断目标与条件，再做准备、选择行动，最后根据反馈调整。判断框架受《孙子兵法》的权衡、准备与因情境调整思路启发，生活建议仍是本项目的经验建议，未验证效果。\n\n'
    full += '**免责声明：仅供参考。** ' + meta['disclaimer'] + '\n\n'
    full += '本版全部为经验建议。示例表达可以调整，效果取决于关系和环境；涉及具体制度请查适用规则。\n\n'
    full += '\n\n'.join((ROOT / 'book' / c['file']).read_text(encoding='utf-8') for c in chapters)
    full += '\n\n' + practice
    sources = load_sources()
    referenced = set(re.findall(r'\b[SRPA]\d{2}\b', full))
    selected_sources = [item for item in sources if item['id'] in referenced]
    if referenced - {item['id'] for item in selected_sources}:
        raise ValueError('正文来源编号缺少索引')
    source_index = '# 来源索引\n\n以下来源编号对应正文中的选题、实践借鉴与有限研究背景。S 为原帖、R 为访谈与博客、P 为论文或更正、A 为机构文章。论文的对象、结论与局限见 [资料笔记](https://kkk-bot.github.io/HowToGetAlong/docs/research-notes.html)；来源不证明整条建议或具体话术有效，取得状态与核实日期逐项记录。\n\n'
    for item in selected_sources:
        source_index += f'## {item["id"]}. {item["title"]}\n\n' + (item.get('citation', '') + '\n\n' if item.get('citation') else '') + f'来源日期：{item["date"]} · {item["status"]}。\n\n[查看来源]({item["url"]})\n\n'
    full += '\n\n' + source_index
    (refs / '来源索引.md').write_text(source_index, encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [来源索引](来源索引.md)\n')
    (ROOT / '完整指南.md').write_text(full.rstrip() + '\n', encoding='utf-8')
    body = '<h1>' + html.escape(meta['name']) + '</h1><p>' + html.escape(meta['positioning']) + '</p>'
    body += f'<p class="muted">v{meta["version"]} · {meta["date"]} · {len(chapters)} 章 {len(entries)} 条 · 全部为经验建议</p>'
    body += '<p><strong>免责声明：仅供参考。</strong> ' + html.escape(meta['disclaimer']) + '</p>'
    body += '<p>示例表达可以调整，效果取决于关系和环境。完整阅读情境、代价和例外后再决定；具体制度请查适用规则。</p>'
    body += '<p>先判断目标与条件，再做准备、选择行动，根据反馈调整。框架受《孙子兵法》启发，古文不是这些生活建议有效的证明。<a href="docs/strategy-notes.html">查看来源与转译边界</a>。</p>'
    body += '<p><a href="docs/Morris账号整理/阅读笔记.html">Morris 来源笔记</a> · <a href="docs/interview-notes.html">访谈与博客笔记</a> · <a href="docs/research-notes.html">论文与文章资料</a> · <a href="docs/verification.html">查看本次整合记录</a>；正文补充仍为经验建议。</p>'
    body += '<nav><a href="index.html">返回检索页</a> · <a href="downloads/人情世故指南.pdf" download>下载 PDF</a> · <a href="完整指南.md" download>下载完整正文</a> · <a href="docs/practice.html">场景练习</a> · <button onclick="window.print()">打印 / 保存为 PDF</button></nav><h2>目录</h2><ol>'
    body += ''.join(f'<li><a href="#chapter-{c["number"]}">{html.escape(c["title"])}</a></li>' for c in chapters) + '</ol><p><a href="#practice">附录：交流复盘与场景练习</a> · <a href="#sources">来源索引</a></p>'
    for chapter in chapters:
        body += f'<h2 class="chapter" id="chapter-{chapter["number"]}">{html.escape(chapter["title"])}</h2>'
        for entry in [e for e in entries if e['chapter'] == chapter['number']]:
            body += f'<article id="entry-{entry["id"]}"><h3>{entry["id"]} {html.escape(entry["title"])}</h3><dl>'
            for key, value in entry['fields'].items():
                escaped = html.escape(value)
                if key == '相关条目':
                    escaped = re.sub(r'(\d+\.\d+)（([^）]+)）', r'<a href="#entry-\1">\1（\2）</a>', escaped)
                elif key == '可以怎么说':
                    escaped = re.sub(r'(（示例仅供参考，请根据事实情况调整。）)(?=.)', r'\1<br><br>', escaped)
                elif key == '依据':
                    escaped = re.sub(r'\b([SRPA]\d{2})\b', r'<a href="#source-\1">\1</a>', escaped)
                body += '<dt>' + html.escape(key) + '</dt><dd' + (' class="example"' if key == '可以怎么说' else '') + '>' + escaped + '</dd>'
            body += '</dl></article>'
    body += '<section id="practice" class="chapter">'
    for block in practice.strip().split('\n\n'):
        block = block.strip()
        if block.startswith('# '):
            body += '<h2>' + html.escape(block[2:]) + '</h2>'
        elif block.startswith('## '):
            body += '<h3>' + html.escape(block[3:]) + '</h3>'
        elif all(line.startswith('- ') for line in block.splitlines()):
            body += '<ul>' + ''.join('<li>' + html.escape(line[2:]) + '</li>' for line in block.splitlines()) + '</ul>'
        elif block.startswith('原创示例：'):
            body += '<h4>表达示例</h4><p class="example">' + html.escape(block.removeprefix('原创示例：')) + '</p>'
        else:
            body += '<p>' + html.escape(block).replace('\n', '<br>') + '</p>'
    body += '</section><section id="sources" class="chapter"><h2>来源索引</h2><p>S 为原帖，R 为访谈与博客，P 为论文、评论或更正，A 为机构文章。来源提供选题、实践借鉴或限定范围的研究背景，不验证整条建议或具体话术。</p>'
    for item in selected_sources:
        body += '<h3 id="source-' + item['id'] + '">' + html.escape(item['id'] + ' ' + item['title']) + '</h3><p>' + html.escape((item.get('citation', '') + ' · ' if item.get('citation') else '') + item['date'] + ' · ' + item['status']) + ' · <a href="' + html.escape(item['url'], quote=True) + '">查看来源</a></p>'
    body += '</section>'
    css = 'body{max-width:850px;margin:40px auto;padding:0 22px;background:#faf9f4;color:#23392f;font:16px/1.85 -apple-system,"PingFang SC",sans-serif}h1{font-size:34px;line-height:1.4}h2{margin-top:48px}h3{font-size:22px;line-height:1.5}a{color:#225a43}nav,button{font:inherit}button{cursor:pointer}article{border-top:1px solid #dce1d7;padding-top:20px;margin:30px 0;scroll-margin-top:20px}dt{font-size:16px;color:#355d43;font-weight:650;margin-top:22px}dd{margin:8px 0 0;overflow-wrap:anywhere}.example{background:#f0f5ee;border:1px solid #d2dfce;border-radius:6px;padding:8px 12px;width:fit-content;max-width:100%}h4{font-size:16px;color:#355d43;margin:20px 0 8px}#practice p,#practice ul{margin:12px 0}#practice .example{margin-top:8px}@media(max-width:600px){body{margin:24px auto;padding:0 16px}h1{font-size:28px}h3{font-size:21px}.example{padding:8px 10px}}.muted{color:#64736b}@media print{body{background:white;margin:0;font-size:11pt}nav{display:none}.chapter{break-before:page}h3,dt{break-after:avoid}dd{orphans:3;widows:3}a{color:inherit;text-decoration:none}}'
    (ROOT / '阅读全文.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(meta['name']) + ' · 完整阅读</title><style>' + css + '</style><body>' + body + '</body></html>', encoding='utf-8')
    # ASCII-path copies keep GitHub entry points accessible; Chinese files remain the source.
    for source, destination in {
        '交流复盘与场景练习.md': 'practice.md',
        '编写规范.md': 'editorial-guide.md',
        '核实记录/v1.15说明.md': 'verification.md',
    }.items():
        text = (ROOT / 'docs' / source).read_text(encoding='utf-8')
        if '/' in source:
            text = text.replace('](../', '](./')
        (ROOT / 'docs' / destination).write_text(text, encoding='utf-8')
    print(f'已检查 {len(chapters)} 章 {len(entries)} 条及交叉引用；生成检索页、连续阅读页、完整正文，同步 Skill 正文快照。')

if __name__ == '__main__':
    main()
