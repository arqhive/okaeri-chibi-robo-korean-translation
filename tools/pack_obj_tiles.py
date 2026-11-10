"""Aligned shortest-superstring packing of sprite tile sequences."""
import numpy as np

def pack(unique):
    symbols={}; arrays=[]
    def symbol(t):
        k=t.tobytes()
        if k not in symbols:
            symbols[k]=len(arrays);arrays.append(t)
        return symbols[k]
    seqs={k:tuple(symbol(t) for t in tt) for k,tt in unique.items()}
    def find(a,b):
        return next((p for p in range(0,len(a)-len(b)+1,2) if a[p:p+len(b)]==b),None)
    chunks=[]
    for s in sorted(set(seqs.values()),key=len,reverse=True):
        if not any(find(c,s) is not None for c in chunks):chunks.append(s)
    # Merge any pair with the largest aligned suffix/prefix overlap.
    while True:
        best=None;score=0
        for i,a in enumerate(chunks):
            for j,b in enumerate(chunks):
                if i==j:continue
                for overlap in range(min(len(a),len(b)),0,-1):
                    if (len(a)-overlap)%2:continue
                    if overlap<=score:break
                    if a[-overlap:]==b[:overlap]:
                        best=(i,j,overlap);score=overlap;break
        if best is None:break
        i,j,n=best;merged=chunks[i]+chunks[j][n:]
        chunks=[c for z,c in enumerate(chunks) if z not in (i,j) and find(merged,c) is None]+[merged]
    result=[]
    zero=symbol(np.zeros((8,8),np.uint8))
    for c in sorted(chunks,key=len,reverse=True):
        if len(result)%2:result.append(zero)
        result.extend(c)
    result=tuple(result);positions={k:find(result,s) for k,s in seqs.items()}
    assert all(p is not None for p in positions.values())
    return [arrays[i] for i in result],positions
