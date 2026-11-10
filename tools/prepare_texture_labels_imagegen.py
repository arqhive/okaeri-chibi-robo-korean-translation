"""Import ImageGen lettering at original texture size and two-color palette."""
from pathlib import Path
import json,shutil,hashlib
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];D=R/'work/graphics-draft/texture-labels-v1/imagegen'
def main():
 specs=json.loads((D/'prompts.json').read_text('utf8'))['specs'];checks=[]
 for s in specs:
  key=s['id'];raw=D/(key+'-generated.png')
  if not raw.exists():shutil.copy2(s['generated_path'],raw)
  orig=Image.open(R/f'work/scope-deep/textures/{key}.png').convert('RGBA');a=np.array(orig)
  gen=Image.open(raw).convert('RGB');rgb=np.array(gen)
  # Only carry the generated white lettering into the original flat background.
  mask=Image.fromarray((rgb.min(axis=2)>160).astype('uint8')*255)
  mask=mask.resize(orig.size,Image.Resampling.LANCZOS);m=np.array(mask)>=(90 if key=='D0017' else 128)
  old=np.all(a==[255,255,255,255],axis=2);b=a.copy();b[old]=a[0,0];b[m]=[255,255,255,255]
  assert set(map(tuple,b.reshape(-1,4)))==set(map(tuple,a.reshape(-1,4)))
  assert not np.any(np.any(a!=b,axis=2)&~(old|m))
  rows=np.flatnonzero(m.any(axis=1));runs=np.split(rows,np.where(np.diff(rows)>1)[0]+1);assert len(runs)==3,(key,len(runs))
  Image.fromarray(b).save(D/(key+'-native.png'))
  checks.append(dict(id=key,size=list(orig.size),palette_preserved=True,background_preserved=True,rows=3,generated_source=raw.name,generated_sha256=hashlib.sha256(raw.read_bytes()).hexdigest()))
 (D/'manifest.json').write_text(json.dumps(dict(tool='built-in image_gen',entries=checks),ensure_ascii=False,indent=2)+'\n','utf8')
 print('3 ImageGen textures converted; native size, two colors, three rows verified.')
if __name__=='__main__':main()
