"""Validate deep survey artifacts and immutable source, not runtime behavior."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import json,hashlib,struct,collections
from PIL import Image
from survey_translation_scope import ROOT
def read(n):return json.loads((ROOT/'metadata'/n).read_text(encoding='utf-8-sig'))
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,attrs):
  for k,v in attrs:
   if k in ['href','src'] and v:self.links.append(v)
def main():
 errors=[];original=read('originals.json')['roms'][0];sha=hashlib.sha256((ROOT/original['file']).read_bytes()).hexdigest();assert sha==original['sha256']
 summary=read('scope_deep_summary.json');d=read('scope_deep.json');c=read('deep_2d_review.json');ev=read('deep_cell_visual_evidence.json');a=read('deep_animation_links.json');cu=read('deep_custom_textures.json');inferred=read('deep_inferred_textures.json');code=read('deep_code_string_review.json')
 assert len(c['cells'])==1803 and len(d['textures'])==2020 and len(a['files'])==176 and len(cu['textures'])==118 and len(inferred)==8
 assert not d['rendering_errors'] and not d['animation_parse_errors'] and not a['errors'] and not cu['errors']
 assert ev['reviewed_small']==list(range(32)) and ev['reviewed_large']==list(range(20)) and ev['reviewed_screens']==list(range(9))
 assert set(ev['japanese_cells'])<=set(r['id'] for r in c['cells'])
 assert sum(summary['stats']['two_d_classification'].values())==305
 assert code['priorities']['direct_message_or_choice']==7 and len(code['candidates'])==741
 assert summary['scope_finalized'] is False and summary['rom_modified'] is False
 # Verify decoded file integrity, dimensions and image-key hashes where stored.
 imagechecks=0
 for r in d['textures']+c['cells']+cu['textures']+cu['cmcode']+inferred:
  p=ROOT/'work/scope-deep'/r['image']
  with Image.open(p) as im:
   im.load()
   if 'width' in r:assert im.size==(r['width'],r['height']),(r.get('id'),im.size)
   if 'rgba_sha256' in r:assert hashlib.sha256(struct.pack('<II',*im.size)+im.convert('RGBA').tobytes()).hexdigest()==r['rgba_sha256'],r['id']
  imagechecks+=1
 # All Japanese evidence rows identify existing source cells/groups.
 groups=read('translation_scope_graphics.json')['groups'];groupsbyid={r['id']:r for r in groups}
 for row in c['cells']:
  for o in row['occurrences']:assert o['cell'] in {x['index'] for x in groupsbyid[o['group']]['cells']}
 # Full model parser coverage count is an additional check beyond absence of errors.
 inventory=read('filesystem_inventory.json');nmd=sum(r['path'].endswith('.nsbmd') for r in inventory['entries']);npat=sum(r['path'].endswith('.nsbtp') for r in inventory['entries']);assert (nmd,npat)==(1082,47)
 pages=[ROOT/'work/scope-deep/index.html',ROOT/'work/scope-deep/code-strings.html'];links=0
 for p in pages:
  parser=Links();parser.feed(p.read_text(encoding='utf-8'))
  for href in parser.links:
   u=urlsplit(href)
   if u.scheme or not u.path:continue
   target=(p.parent/unquote(u.path)).resolve()
   if target.name=='scope_deep_validation.json':continue
   if not target.exists():errors.append({'page':str(p),'missing':href})
   links+=1
 assert not errors,errors[:10]
 result={'passed':True,'source_sha256':sha,'rom_unchanged':True,'image_files_checked':imagechecks,'local_links_checked':links,'nanr_files':176,'pat0_files':47,'model_files_considered':1082,'errors':errors,'limitations':['No emulator runtime reachability or screenshot verification in this survey','Visual evidence records distinguish contact-sheet review, inferred palettes and unresolved tiny marks','741 strings are heuristic candidates, not complete proof of all encoded or assembled text']}
 (ROOT/'metadata/scope_deep_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
