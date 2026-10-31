"""My pod promax hybrid launcher: web converter or local music utilities."""
from pathlib import Path
import subprocess, sys

ROOT=Path(__file__).resolve().parent

def ask(label,default=''):
    value=input(label+(f' [{default}]' if default else '')+': ').strip().strip('"')
    return value or default

def streamlit():
    print('Opening the Streamlit website at http://localhost:8501')
    subprocess.run([sys.executable,'-m','streamlit','run',str(ROOT/'app.py')],check=False)

def from_folder():
    from musicvault.organizer import scan,organise
    print('\nOrganise existing Mac/SSD folder into a separate new, empty destination.')
    print('The original folder will NOT be replaced by this GitHub launcher.')
    source=ask('Existing music folder')
    if not source:return
    try:print(f'Found {len(scan(source))} audio files.')
    except Exception as exc:print(f'Could not scan: {exc}');return
    destination=ask('New empty destination folder')
    if not destination:return
    if ask('Type YES to copy organised files')!='YES':return
    try:
        count,duplicates=organise(source,destination)
        print(f'Done: {count} files copied; {duplicates} exact duplicate(s). Originals unchanged.')
    except Exception as exc:print(f'Error: {exc}')

def from_ipod():
    from musicvault.organizer import devices,scan,organise
    found=devices()
    if found:
        for i,item in enumerate(found,1):print(f' {i}. {item["name"]} ({item["music"]})')
        selection=ask('Choose iPod number or paste iPod_Control/Music path','1')
        try:source=found[int(selection)-1]['music']
        except (ValueError,IndexError):source=selection
    else:source=ask('Paste mounted iPod_Control/Music folder')
    if not source:return
    path=Path(source).expanduser()
    if path.name!='Music' or path.parent.name!='iPod_Control':
        print('Choose the iPod_Control/Music folder on a mounted iPod.');return
    try:print(f'Found {len(scan(str(path)))} audio files.')
    except Exception as exc:print(f'Could not scan: {exc}');return
    print('iPod remains read-only. Use a NEW EMPTY output folder on your SSD.')
    dest=ask('Destination folder')
    if dest and ask('Type YES to make organised copies')=='YES':
        try:
            count,_=organise(str(path),dest)
            print(f'Copied {count} songs. iPod unchanged.')
        except Exception as exc:print(f'Error: {exc}')

def smart_fix():
    try:
        from smart_fix_music import main
        main()
    except Exception as exc:print(f'Smart Fix: {exc}')

def main():
    while True:
        print('\n===========================================')
        print('  My pod promax  ♫  by Bipzilla')
        print('===========================================')
        print(' A) Open Streamlit — download and convert music')
        print(' B) Organise music in a local folder (safe separate copies)')
        print(' C) Organise music FROM iPod (iPod unchanged)')
        print(' D) Smart Identify & Fix existing SSD songs')
        print(' E) Exit')
        option=ask('Choose A, B, C, D or E').upper()
        if option=='A':streamlit()
        elif option=='B':from_folder()
        elif option=='C':from_ipod()
        elif option=='D':smart_fix()
        elif option=='E':break
        else:print('Choose A, B, C, D or E.')

if __name__=='__main__':main()
