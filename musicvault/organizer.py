"""Safe local iPod backup and metadata-based library organisation."""
from pathlib import Path
import os,sys,string,shutil,hashlib,re,json
from mutagen import File as AudioFile

EXTS={'.mp3','.m4a','.aac','.flac','.wav','.ogg','.aif','.aiff'}
def devices():
    if sys.platform=='darwin': roots=[Path('/Volumes')]
    elif os.name=='nt': roots=[Path(f'{x}:/') for x in string.ascii_uppercase if Path(f'{x}:/').exists()]
    else: roots=[Path('/media')/os.environ.get('USER',''),Path('/run/media')/os.environ.get('USER',''),Path('/mnt')]
    result=[]
    for root in roots:
        if not root.exists(): continue
        try: dirs=[root]+[d for d in root.iterdir() if d.is_dir()]
        except OSError: continue
        for d in dirs:
            folder=d/'iPod_Control'/'Music'
            if folder.is_dir() and not any(str(folder)==item['music'] for item in result):
                result.append({'name':d.name,'music':str(folder)})
    return result

def scan(folder):
    p=Path(folder).expanduser().resolve(strict=True)
    if not p.is_dir(): raise ValueError('Select a music folder.')
    return sorted(x for x in p.rglob('*') if x.is_file() and x.suffix.lower() in EXTS)

def validate(source,destination):
    src=Path(source).expanduser().resolve(strict=True)
    dst=Path(destination).expanduser().resolve()
    if dst==src or src in dst.parents or dst in src.parents: raise ValueError('Use a separate destination, not inside the source.')
    if dst.exists() and any(dst.iterdir()): raise ValueError('Destination must be empty.')
    if not destination.strip(): raise ValueError('Enter a destination folder.')
    return src,dst

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def backup(source,destination):
    src,dst=validate(source,destination)
    paths=scan(src)
    if not paths:raise ValueError('No audio found.')
    dst.mkdir(parents=True,exist_ok=True)
    report=[]
    for p in paths:
        rel=p.relative_to(src);target=dst/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)
        if sha(p)!=sha(target):raise IOError('Verification failed: '+str(rel))
        report.append({'file':str(rel),'sha256':sha(target)})
    (dst/'backup_manifest.json').write_text(json.dumps(report,indent=2))
    return len(report)

def organise(source,destination):
    src,dst=validate(source,destination)
    paths=scan(src)
    if not paths:raise ValueError('No audio found.')
    dst.mkdir(parents=True,exist_ok=True)
    def safe(s):
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(s or 'Unknown')).strip(' .')[:100] or 'Unknown'
    report=[]; hashes={}
    for p in paths:
        try:
            tags=AudioFile(p,easy=True)
            def first(k):return (tags.get(k) or [''])[0] if tags else ''
            artist=safe(first('albumartist') or first('artist') or 'Unknown Artist')
            album=safe(first('album') or 'Unknown Album')
            title=safe(first('title') or p.stem)
        except Exception:
            artist,album,title='Unknown Artist','Unknown Album',safe(p.stem)
        target_dir=dst/artist/album;target_dir.mkdir(parents=True,exist_ok=True)
        target=target_dir/(title+p.suffix.lower());i=2
        while target.exists():
            target=target_dir/f'{title} ({i}){p.suffix.lower()}';i+=1
        shutil.copy2(p,target)
        digest=sha(p);duplicate=hashes.get(digest)
        hashes.setdefault(digest,str(p))
        report.append({'old':str(p),'new':str(target),'exact_duplicate_of':duplicate})
    (dst/'organisation_report.json').write_text(json.dumps(report,indent=2))
    return len(report),sum(bool(x['exact_duplicate_of']) for x in report)
