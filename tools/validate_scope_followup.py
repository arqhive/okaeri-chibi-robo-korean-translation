from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import json,hashlib,subprocess,py_compile
ROOT=Path(__file__).resolve().parents[1]

class Page(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.scripts=[];self.current=None
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  for k in ('src','href'):
   if k in d:self.links.append(d[k])
  if tag=='script' and 'src' not in d:self.current=[]
 def handle_data(self,data):
  if self.current is not None:self.current.append(data)
 def handle_endtag(self,tag):
  if tag=='script' and self.current is not None:self.scripts.append(''.join(self.current));self.current=None

def main():
 pages=list((ROOT/'work/scope-review').rglob('*.html'))+[ROOT/'work/scope-followup/index.html']
 missing=[];scripts=[];nlinks=0
 for p in pages:
  obj=Page();obj.feed(p.read_text(encoding='utf-8'))
  for link in obj.links:
   u=urlsplit(link)
   if u.scheme or not u.path:continue
   nlinks+=1
   if not (p.parent/unquote(u.path)).exists():missing.append({'page':str(p.relative_to(ROOT)),'link':link})
  scripts.extend(obj.scripts)
 assert not missing,missing
 js=ROOT/'work/scope-followup/check-inline-scripts.cjs'
 js.write_text('const scripts='+json.dumps(scripts)+';for(const s of scripts)new Function(s);console.log(scripts.length);',encoding='utf-8')
 run=subprocess.run(['C:/Program Files/nodejs/node.exe',str(js)],text=True,capture_output=True,check=True)
 for p in ['survey_scope_followup.py','trace_scope_links.py','render_scope_review.py','render_scope_followup.py']:py_compile.compile(str(ROOT/'tools'/p),doraise=True)
 o=json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))['roms'][0]
 sha=hashlib.sha256((ROOT/o['file']).read_bytes()).hexdigest();assert sha==o['sha256']
 g=json.loads((ROOT/'metadata/translation_scope_graphics.json').read_text(encoding='utf-8'))
 f=json.loads((ROOT/'metadata/scope_followup.json').read_text(encoding='utf-8'))
 c=json.loads((ROOT/'metadata/scope_code_links.json').read_text(encoding='utf-8'))
 assert sum(g['classification_counts'].values())==305
 assert sum(f['visual_review_counts'].values())==1913
 assert len(c['connections'])==124
 for t in f['textures']:
  from PIL import Image
  with Image.open(ROOT/'work/scope-followup'/t['image']) as im:
   import struct
   assert hashlib.sha256(struct.pack('<II',*im.size)+im.convert('RGBA').tobytes()).hexdigest()==t['rgba_sha256']
 result={'html_pages':len(pages),'local_links_checked':nlinks,'missing_links':missing,'inline_scripts_syntax_valid':len(scripts),
 'python_scripts_compile':True,'texture_image_hashes_verified':1913,'original_rom_unchanged':True,'source_sha256':sha,
 'browser_layout_verified':False,'runtime_background_links_verified':False,'scope_finalized':False}
 (ROOT/'metadata/scope_followup_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
