from pathlib import Path
import json,hashlib
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from prepare_terminology_review import ROOT,OUT,clean
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k=='id':self.ids.append(v)
   if k=='href':self.links.append(v)
def main():
 j=json.loads((ROOT/'metadata/terminology_proposals.json').read_text(encoding='utf-8'));es=json.loads((ROOT/'metadata/text_entries.json').read_text(encoding='utf-8'));by={(r['file'],r['index']):r for r in es};n=0
 assert j['approved'] is False
 assert len({r['id'] for r in j['terms']})==len(j['terms'])==117
 assert len(j['voice_proposals'])==14
 for r in j['terms']:
  assert r['entry_hit_count']==sum(r['source'] in clean(x['text']) for x in es)
  assert r['evidence'] and r['status']=='proposed'
  for v in r['evidence']:
   assert v['source_text']==by[v['file'],v['index']]['text']
   assert v['visible_text']==clean(v['source_text']) and r['source'] in v['visible_text'];n+=1
 for v in j['voice_proposals']:assert v['source_text']==by[v['file'],v['index']]['text']
 p=Page();p.feed((OUT/'index.html').read_text(encoding='utf-8'));assert len(p.ids)==len(set(p.ids))
 for href in p.links:
  u=urlsplit(href)
  if not u.path and u.fragment:assert u.fragment in p.ids,href
  elif not u.scheme:
   path=OUT/unquote(u.path)
   if path.name!='terminology_review_validation.json':assert path.exists(),href
 original=json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0];sha=hashlib.sha256((ROOT/original['file']).read_bytes()).hexdigest();assert sha==original['sha256']
 result={'passed':True,'terms':117,'voice_examples':14,'source_evidence_checked':n,'voice_sources_checked':14,'html_ids_unique':True,'local_links_and_anchors_checked':len(p.links),'rom_sha256':sha,'rom_unchanged':True,'notes':['Translation proposals are unapproved. Source evidence is verbatim; visible examples omit control bytes for readability.','HTML content and links validated; browser screenshot and in-game typography not verified.']}
 (ROOT/'metadata/terminology_review_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
