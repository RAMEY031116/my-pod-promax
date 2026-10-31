"""My pod promax — low-storage fingerprint review and in-place metadata repair.
Run: python smart_fix_music.py
Requires: mutagen, requests, Pillow, fpcalc, and your own AcoustID application key.
"""
from pathlib import Path
import io, json, re, shutil, subprocess, time
import requests
from mutagen import File
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from PIL import Image

EXTS={'.mp3','.m4a','.flac','.ogg','.opus','.aif','.aiff','.wav'}
PLAN='.mypod-smart-fix-plan.json'
HEAD={'User-Agent':'MyPodPromax-SmartFix/1.0 (music library utility)'}

def root_folder(value):
    root=Path(value).expanduser().resolve(strict=True)
    if not root.is_dir() or root==Path.home() or root==Path('/'):
        raise ValueError('Choose an existing specific music folder.')
    if 'iPod_Control' in root.parts or (root/'iPod_Control').exists():
        raise ValueError('Direct iPod modification is blocked.')
    return root

def current(p):
    a=File(p,easy=True)
    if a is None: raise ValueError('Unsupported audio')
    return {k:str(a.get(k,[''])[0]) for k in ('title','artist','album')}

def unknown(tags):
    return any(not value.strip() or value.strip().lower().startswith(('unknown','untitled','track ')) for value in tags.values())

def fingerprint(path):
    if not shutil.which('fpcalc'):
        raise RuntimeError('Install Chromaprint fpcalc (Mac: brew install chromaprint)')
    p=subprocess.run(['fpcalc','-json',str(path)],capture_output=True,text=True,check=True,timeout=90)
    f=json.loads(p.stdout)
    return int(f['duration']),f['fingerprint']

def lookup(key,duration,fp):
    r=requests.post('https://api.acoustid.org/v2/lookup',data={'client':key,'duration':duration,'fingerprint':fp,'meta':'recordings+releasegroups','format':'json'},headers=HEAD,timeout=35)
    r.raise_for_status()
    data=r.json()
    if data.get('status')!='ok': raise ValueError('AcoustID rejected request')
    results=sorted(data.get('results',[]),key=lambda x:x.get('score',0),reverse=True)
    if not results or not results[0].get('recordings'): return None
    best=results[0]; recordings=best['recordings']; rec=recordings[0]
    groups=rec.get('releasegroups') or []
    group=groups[0] if groups else {}
    artists=' & '.join(a['name'] for a in rec.get('artists',[]) if a.get('name'))
    if float(best.get('score',0))<0.85 or not rec.get('title') or not artists:return None
    return {'title':rec['title'],'artist':artists,'album':group.get('title',''),
            'group_id':group.get('id',''),'score':round(float(best['score']),3),
            'alternatives':len(recordings)}

def scan(root,key,limit,all_songs):
    if not key or len(key)<6:raise ValueError('AcoustID key required')
    candidates=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix.lower() not in EXTS:continue
        try:
            tags=current(p)
            if all_songs or unknown(tags):candidates.append((p,tags))
        except Exception:continue
    entries=[]
    for n,(p,tags) in enumerate(candidates[:limit],1):
        stat=p.stat()
        e={'path':str(p.relative_to(root)),'original':tags,'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,
           'proposed':None,'approved':False,'status':'unmatched'}
        try:
            d,f=fingerprint(p);match=lookup(key,d,f)
            if match:
                e['proposed']=match;e['status']='review'
        except Exception as exc:e['status']='error: '+str(exc)[:120]
        entries.append(e)
        if n%10==0 or n==min(limit,len(candidates)):
            print(f'Scanned {n}/{min(limit,len(candidates))} — {sum(bool(x["proposed"]) for x in entries)} matches',flush=True)
    target=root/PLAN
    target.write_text(json.dumps({'root':str(root),'entries':entries},indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Review file: {target}')
    print('Change "approved": false to "approved": true ONLY on correct matches. Nothing edited yet.')

def filename(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(value or 'Unknown')).strip(' .')[:100] or 'Unknown'

def cover(group,cache):
    if not group:return None
    if group in cache:return cache[group]
    try:
        r=requests.get(f'https://coverartarchive.org/release-group/{group}/front-500',headers=HEAD,timeout=25)
        r.raise_for_status()
        if len(r.content)>6000000:raise ValueError('Image too large')
        im=Image.open(io.BytesIO(r.content)).convert('RGB');im.thumbnail((600,600))
        buf=io.BytesIO();im.save(buf,'JPEG',quality=85);cache[group]=buf.getvalue()
    except Exception:cache[group]=None
    return cache[group]

def apply(root,rename,artwork):
    path=root/PLAN
    plan=json.loads(path.read_text(encoding='utf-8'))
    if plan['root']!=str(root):raise ValueError('Plan folder mismatch')
    cache={};done=0;failed=0
    for e in plan['entries']:
        if not e.get('approved') or not e.get('proposed'):continue
        p=root/e['path'];m=e['proposed']
        try:
            if not p.is_file() or root not in p.resolve().parents:raise ValueError('Unsafe/missing file')
            stat=p.stat()
            if stat.st_size!=e['size'] or stat.st_mtime_ns!=e['mtime_ns']:raise ValueError('File changed after scan')
            tags=File(p,easy=True)
            tags['title']=[m['title']];tags['artist']=[m['artist']]
            if m.get('album'):tags['album']=[m['album']]
            tags.save()
            if artwork and p.suffix.lower()=='.mp3':
                img=cover(m.get('group_id'),cache)
                if img:
                    try:id3=ID3(p)
                    except ID3NoHeaderError:id3=ID3()
                    if not id3.getall('APIC'):
                        id3.add(APIC(encoding=3,mime='image/jpeg',type=3,desc='Front cover',data=img))
                        id3.save(p,v2_version=3)
            if rename:
                album=m.get('album') or e['original'].get('album') or 'Unknown Album'
                dest=root/filename(m['artist'])/filename(album)/(filename(m['title'])+p.suffix.lower())
                dest.parent.mkdir(parents=True,exist_ok=True)
                if dest!=p:
                    i=2
                    while dest.exists():
                        dest=dest.with_name(filename(m['title'])+f' ({i})'+p.suffix.lower());i+=1
                    p.rename(dest)
            e['status']='applied';done+=1
        except Exception as exc:
            e['status']='apply_error: '+str(exc)[:120];failed+=1
        e['approved']=False
        path.write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Updated {done}; failed {failed}. Keep original Before-MyPod backup.')

def main():
    print('My pod promax — Smart Identify & Fix (SSD/local folder only)')
    root=root_folder(input('Music folder path: ').strip().strip('"'))
    print('1 Scan unknown songs; 2 Scan all songs; 3 Apply APPROVED suggestions')
    mode=input('Choose 1/2/3: ').strip()
    if mode in ('1','2'):
        key=input('Your AcoustID application API key: ').strip()
        limit=int(input('Batch size (recommended 50): ') or '50')
        if not 1<=limit<=500:raise ValueError('Limit must be 1–500')
        scan(root,key,limit,mode=='2')
    elif mode=='3':
        print('Make sure you have kept the Before-MyPod recovery backup.')
        if input('Type APPLY to update approved songs: ')!='APPLY':return
        ren=input('Rename and move into Artist/Album folders? (y/N): ').lower()=='y'
        art=input('Fetch missing MP3 cover art? (y/N): ').lower()=='y'
        apply(root,ren,art)
    else:print('Nothing changed.')

if __name__=='__main__':main()
