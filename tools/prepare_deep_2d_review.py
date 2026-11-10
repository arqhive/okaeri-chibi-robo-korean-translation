from pathlib import Path
from PIL import Image
import json,hashlib,struct
from survey_translation_scope import ROOT
from survey_scope_followup import grid
OUT=ROOT/'work/scope-deep'

def main():
 g=json.loads((ROOT/'metadata/translation_scope_graphics.json').read_text(encoding='utf-8'))
 unique={};blank=0
 for r in g['groups']:
  for c in r.get('cells',[]):
   im=Image.open(ROOT/'work/scope-review'/c['image']).convert('RGBA')
   if not im.getchannel('A').getbbox():blank+=1;continue
   key=hashlib.sha256(struct.pack('<II',*im.size)+im.tobytes()).hexdigest()
   if key not in unique:unique[key]={'id':f'C{len(unique)+1:04d}','image':'../scope-review/'+c['image'],'width':im.width,'height':im.height,'rgba_sha256':key,'occurrences':[]}
   unique[key]['occurrences'].append({'group':r['id'],'stem':r['stem'],'cell':c['index']})
 rows=list(unique.values());pageinfo=[]
 for kind,subset,cols,box,count in [('small',[r for r in rows if r['height']<=48 and r['width']<=200],5,(240,110),50),('large',[r for r in rows if r['height']>48 or r['width']>200],4,(280,280),12)]:
  for i in range(0,len(subset),count):
   chunk=subset[i:i+count];items=[]
   for r in chunk:
    im=Image.open(OUT/r['image']);scale=2 if im.width*2<=box[0]-10 and im.height*2<=box[1]-32 else 1
    if scale==2:im=im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST)
    o=r['occurrences'][0];items.append((r['id']+' '+Path(o['stem']).name+'/'+str(o['cell']),im))
   p=f'boards/cells-{kind}-{i//count:02d}.png';grid(items,OUT/p,cols=cols,box=box);pageinfo.append({'image':p,'ids':[r['id'] for r in chunk]})
 screens=[r for r in g['groups'] if r.get('screen_image')]
 for i in range(0,len(screens),12):
  chunk=screens[i:i+12];p=f'boards/screens-{i//12:02d}.png'
  grid([(r['id']+' '+Path(r['stem']).name,Image.open(ROOT/'work/scope-review'/r['screen_image'])) for r in chunk],OUT/p,cols=4,box=(280,300));pageinfo.append({'image':p,'groups':[r['id'] for r in chunk]})
 j={'unique_nonempty_cells':len(rows),'transparent_cells_skipped':blank,'cells':rows,'boards':pageinfo,'screens':screens}
 (ROOT/'metadata/deep_2d_review.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('cells',len(rows),'blank',blank,'boards',len(pageinfo));print([r['image'] for r in pageinfo])

if __name__=='__main__':main()
