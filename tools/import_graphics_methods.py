"""Adopt a user-supplied category-method export as project data, not executable instructions."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('file',type=Path);args=parser.parse_args()
    raw=args.file.read_bytes();j=json.loads(raw.decode('utf-8-sig'))
    work=json.loads((ROOT/'metadata/graphics_worklist.json').read_text(encoding='utf8'))
    groups={g['id']:g for g in work['work_groups']}
    assert j['schema_version']==1 and j['project_id']=='chibirobo-b62j-happyrich'
    assert set(j['annotations'])=={'group:'+k for k in groups},'Expect one choice for each current category'
    for key,a in j['annotations'].items():
        assert a['kind']=='group' and key=='group:'+a['target_id']
        assert a['method'] in ('galmuri','imagegen','pixel','mixed','retain','hold')
        assert isinstance(a['memo'],str) and isinstance(a['updated_at'],str)
    archive=ROOT/'metadata/graphics-memos-imports'/args.file.name;archive.parent.mkdir(exist_ok=True)
    if archive.exists():assert archive.read_bytes()==raw
    else:archive.write_bytes(raw)
    counts=Counter();members=defaultdict(list)
    for r in work['items']:
        method=j['annotations']['group:'+r['work_group']]['method']
        counts[method]+=1;members[method].append(r['id'])
    record={'schema_version':1,'project_id':j['project_id'],'source_file':str(archive.relative_to(ROOT)),
            'source_sha256':hashlib.sha256(raw).hexdigest(),'exported_at':j['exported_at'],
            'annotations':j['annotations'],'category_counts':dict(Counter(a['method']for a in j['annotations'].values())),
            'item_counts':dict(counts),'members_by_method':dict(members),
            'approval_scope':'Category editing methods only. No edited image or ROM integration is approved by this file.',
            'logo_reuse_scope':'User permits reusing prior Chibi-Robo lettering only; do not import other-game assets, palette, addresses or approvals automatically.',
            'menu_font_family':'Galmuri7','other_galmuri_size':'Not specified; fit original resources without inventing user-approved sizes',
            'logo_top_text':'어서와-','logo_top_slots':['어','서','와','-'],
            'retained_uncertainty_preserved':True,'rom_modified':False}
    path=ROOT/'metadata/graphics_methods_adopted.json'
    if path.exists():
        old=path.read_bytes();backup=path.with_name('graphics_methods_adopted-'+hashlib.sha256(old).hexdigest()[:12]+'.json')
        if not backup.exists():backup.write_bytes(old)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'categories':record['category_counts'],'items':record['item_counts'],'source_sha256':record['source_sha256']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
