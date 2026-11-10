"""Validate translation data against extracted native BMG, without building a ROM."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from collections import Counter
import hashlib, json, re
from ndspy.bmg import BMG

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))
def sha(data):
    return hashlib.sha256(data).hexdigest()
def controls(parts):
    return [p['control_hex'] for p in parts if 'control_hex' in p]
def joined(parts):
    return ''.join(p['text'] if 'text' in p else '<'+p['control_hex']+'>' for p in parts)
FORMAT = re.compile(r'%(?:\d+\$)?[-+# 0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlL]*[diuoxXfFeEgGcs%]')
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]; self.links=[]; self.articles=0
    def handle_starttag(self, tag, attrs):
        self.articles += tag=='article'
        for key, val in attrs:
            if key=='id': self.ids.append(val)
            if key=='href': self.links.append(val)
def main():
    source = read('metadata/text_entries.json')
    tracker = read('translations/entries.json')
    batch = read('translations/batch01.json')
    progress = read('metadata/translation_progress.json')
    assert tracker['source_entries_sha256']==sha((ROOT/'metadata/text_entries.json').read_bytes())
    rows=tracker['entries']; assert len(rows)==len(source)==7659
    assert len({r['id'] for r in rows})==len(rows)
    native={}; checked=0; control_count=0; placeholder_count=0
    for original, row in zip(source, rows):
        assert row['id']==f"{original['file']}#{original['index']}"
        assert row['source']==original['text'] and row['source_parts']==original['parts']
        assert row['source_sha256']==sha(original['text'].encode())
        if row['status']!='draft':
            assert row['translation'] is None and row['translation_parts'] is None
            continue
        filename=row['file']
        if filename not in native:
            native[filename]=BMG((ROOT/'work/extracted'/filename).read_bytes())
        parts=[]
        for p in native[filename].messages[row['index']].stringParts:
            if isinstance(p,str): parts.append({'text':p})
            else: parts.append({'control_hex':(bytes([0x1a,len(p.data)+3,p.type])+p.data).hex()})
        assert joined(parts)==row['source'],row['id']
        assert controls(parts)==controls(row['translation_parts']),row['id']
        assert joined(row['translation_parts'])==row['translation']
        assert FORMAT.findall(row['source'])==FORMAT.findall(row['translation']),row['id']
        text=''.join(p['text'] for p in row['translation_parts'] if 'text' in p)
        assert text.strip() and not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]',text),row['id']
        assert row['runtime_verified'] is False
        checked+=1; control_count+=len(controls(parts)); placeholder_count+=len(FORMAT.findall(text))
    assert batch['entries']==[r for r in rows if r['status']=='draft']
    assert batch['manifest']==progress
    assert dict(Counter(r['status'] for r in rows))==progress['counts']
    assert checked==progress['batch_count']==368
    assert progress['counts']['draft']+progress['counts']['pending']==7208
    proposal=read('metadata/terminology_proposals.json'); adopted=read('metadata/terminology_approved.json')
    assert adopted['approved'] is True and len(adopted['terms'])==117
    for before, after in zip(proposal['terms'],adopted['terms']):
        assert before['source']==after['source'] and before['proposed_ko']==after['proposed_ko']
        assert before['evidence']==after['evidence']
    page=Page(); pagepath=ROOT/'work/translation-review/index.html'
    page.feed(pagepath.read_text(encoding='utf-8'))
    assert len(page.ids)==len(set(page.ids)) and page.articles==checked
    for link in page.links:
        u=urlsplit(link)
        if not u.path and u.fragment: assert u.fragment in page.ids
        elif not u.scheme:
            target=pagepath.parent/unquote(u.path)
            if target.name!='translation_batch01_validation.json': assert target.exists(),link
    original=read('metadata/originals.json')['roms'][0]
    digest=sha((ROOT/original['file']).read_bytes()); assert digest==original['sha256']
    result={'passed':True,'draft_entries':checked,'pending_entries':6840,'source_bmg_files_checked':len(native),
            'native_bmg_control_tokens_preserved':control_count,'format_placeholders_preserved':placeholder_count,
            'html_articles':page.articles,'html_links_checked':len(page.links),'rom_sha256':digest,'rom_unchanged':True,
            'limitations':['No ROM built; Korean encoding, font widths, message box heights, speaker assignments and runtime branches remain unverified.','HTML structure and links checked; no browser screenshot verification.']}
    (ROOT/'metadata/translation_batch01_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
