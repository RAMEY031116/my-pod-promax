"""My pod promax — by Bipzilla. Run: python -m streamlit run app.py."""
import io
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK
from PIL import Image
import yt_dlp

st.set_page_config(page_title="My pod promax", page_icon="🎵", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
:root {color-scheme:light}
html,body,[data-testid="stAppViewContainer"]{background:#fbf9fb!important;color:#302333!important}
[data-testid="stHeader"]{background:#fbf9fb!important}
.block-container{max-width:1120px;padding:1.3rem 1.3rem 4rem!important}
h1,h2,h3,p,label,small,[data-testid="stMarkdownContainer"]{color:#302333!important}
div.stButton>button[kind="primary"],div.stDownloadButton>button[kind="primary"],button[kind="primary"]{background:#d84e92!important;color:#fff!important;border:1px solid #d84e92!important}
div.stButton>button[kind="primary"] *,div.stDownloadButton>button[kind="primary"] *{color:#fff!important}
div.stButton>button[kind="primary"]:hover,div.stDownloadButton>button[kind="primary"]:hover{background:#b93274!important;color:#fff!important}
div.stButton>button:not([kind="primary"]),div.stDownloadButton>button:not([kind="primary"]){background:#fff!important;color:#41283e!important;border:1px solid #e9cfdf!important}
div.stButton>button:not([kind="primary"]) *,div.stDownloadButton>button:not([kind="primary"]) *{color:#41283e!important}
div.stButton>button,div.stDownloadButton>button{min-height:2.8rem;border-radius:12px!important;font-weight:700!important}
.stTextInput input,.stTextArea textarea{background:#fff!important;color:#302333!important;border:1px solid #dec9d5!important}
[data-testid="stFileUploader"]{background:#fff;border-radius:14px;padding:.3rem}
[data-testid="stTabs"] button{color:#422b3f!important}
[data-testid="stTabs"] button[aria-selected="true"]{color:#bc377e!important;border-bottom-color:#d84e92!important}
@media(max-width:640px){
.block-container{padding:.8rem .7rem 2.5rem!important}
h1{font-size:1.8rem!important}
div.stButton>button,div.stDownloadButton>button{width:100%!important}
[data-testid="stHorizontalBlock"]{gap:.65rem}
[data-testid="stTabs"] [data-baseweb="tab-list"]{overflow-x:auto}
}
</style>""",unsafe_allow_html=True)

UA={"User-Agent":"MyPodPromax/0.9 (personal library tool; contact via github.com/RAMEY031116/my-pod-promax)"}
TIMEOUT=12
if "queue" not in st.session_state: st.session_state.queue=[]
if "library" not in st.session_state: st.session_state.library=[]
if "previewed" not in st.session_state: st.session_state.previewed=False

def clean(s):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]+',' ',str(s or '')).strip(' .')[:120] or "Unknown"

def links_from_text(t):
    seen=set(); out=[]
    for line in t.splitlines():
        for candidate in re.findall(r'https?://[^\s<>]+',line):
            u=candidate.strip("),.;]")
            p=urlparse(u)
            if p.scheme=="https" and p.netloc.lower() in ("youtube.com","www.youtube.com","m.youtube.com","youtu.be","music.youtube.com") and u not in seen:
                out.append(u);seen.add(u)
    return out

def fetch_details(url):
    try:
        with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"noplaylist":True,"skip_download":True,"socket_timeout":14}) as y:
            data=y.extract_info(url,download=False) or {}
        return {"url":url,"title":clean(data.get("track") or data.get("title") or "Untitled"),"artist":clean(data.get("artist") or data.get("uploader") or "Unknown Artist"),"album":clean(data.get("album") or ""),"thumb":data.get("thumbnail") or "","selected":True}
    except Exception as exc:
        return {"url":url,"title":"Unavailable","artist":"","album":"","thumb":"","selected":False,"error":str(exc)[:240]}

def jpeg_bytes(raw):
    with Image.open(io.BytesIO(raw)) as im:
        im=im.convert("RGB")
        im.thumbnail((1000,1000))
        out=io.BytesIO();im.save(out,format="JPEG",quality=90)
        return out.getvalue()

def thumbnail(url):
    if not url or not url.startswith("https://"): return None
    host=urlparse(url).hostname or ""
    if not (host.endswith(".ytimg.com") or host=="i.ytimg.com" or host.endswith(".googleusercontent.com")): return None
    try:
        r=requests.get(url,timeout=TIMEOUT,headers=UA)
        r.raise_for_status()
        if len(r.content)>8_000_000: return None
        return jpeg_bytes(r.content)
    except Exception: return None

def tag_mp3(path,title,artist,album="",cover=None,track=None):
    try: tags=ID3(str(path))
    except ID3NoHeaderError: tags=ID3()
    tags.delall("TIT2");tags.add(TIT2(encoding=3,text=title))
    tags.delall("TPE1");tags.add(TPE1(encoding=3,text=artist))
    if album:
        tags.delall("TALB");tags.add(TALB(encoding=3,text=album))
    if track:
        tags.delall("TRCK");tags.add(TRCK(encoding=3,text=str(track)))
    if cover:
        tags.delall("APIC");tags.add(APIC(encoding=3,mime="image/jpeg",type=3,desc="Cover",data=cover))
    tags.save(str(path),v2_version=3)

def process_url(item, folder):
    if not shutil.which("ffmpeg"): raise RuntimeError("FFmpeg is not installed. Install it and restart the app.")
    base=clean(item["artist"]+" - "+item["title"])
    out=folder/(base+".mp3")
    with yt_dlp.YoutubeDL({"format":"bestaudio/best","quiet":True,"no_warnings":True,"noplaylist":True,"outtmpl":str(folder/(base+".%(ext)s")),"postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]}) as y:
        info=y.extract_info(item["url"],download=True) or {}
    if not out.exists(): raise RuntimeError("Conversion completed without producing an MP3")
    art=thumbnail(info.get("thumbnail") or item.get("thumb"))
    tag_mp3(out,item["title"],item["artist"],item.get("album",""),art)
    return out.read_bytes(),bool(art)

def process_upload(file,title,artist,album,cover=None):
    if not shutil.which("ffmpeg"): raise RuntimeError("FFmpeg is not installed.")
    with tempfile.TemporaryDirectory() as t:
        folder=Path(t);name=clean(Path(file.name).stem)
        src=folder/("source"+Path(file.name).suffix.lower())
        src.write_bytes(file.getvalue())
        output=folder/"output.mp3"
        import subprocess
        result=subprocess.run(["ffmpeg","-nostdin","-y","-loglevel","error","-i",str(src),"-vn","-codec:a","libmp3lame","-b:a","192k",str(output)],capture_output=True,text=True,timeout=240)
        if result.returncode or not output.exists(): raise RuntimeError((result.stderr or "FFmpeg conversion failed")[-400:])
        art=jpeg_bytes(cover.getvalue()) if cover else None
        tag_mp3(output,title or name,artist or "Unknown Artist",album,art)
        return output.read_bytes(),bool(art)

def search_music(query,entity):
    if not query.strip(): return [],"Enter a search term."
    try:
        r=requests.get("https://musicbrainz.org/ws/2/"+entity,params={"query":query,"fmt":"json","limit":20},headers=UA,timeout=TIMEOUT)
        if r.status_code==429: return [],"Catalogue is busy. Wait a moment and retry."
        r.raise_for_status()
        return r.json().get({"artist":"artists","release-group":"release-groups"}[entity],[]),""
    except requests.Timeout: return [],"The music catalogue timed out. Your internet connection may be slow."
    except requests.RequestException as exc: return [],"Catalogue unavailable: "+str(exc)[:140]

st.markdown("### 🎵 My pod promax  ·  by Bipzilla")
st.caption("Discover music, prepare metadata, and export MP3s for your iPod.")
discover,import_tab,library=st.tabs(["🔎 Discover","🔗 Import links & audio","💿 My library"])

with discover:
    st.subheader("Find artists and albums")
    query=st.text_input("Artist or album",placeholder="e.g. Nujabes or Modal Soul",key="search")
    kind=st.radio("Search for",["Albums","Artists"],horizontal=True)
    if st.button("Search catalogue",type="primary"):
        rows,error=search_music(query,"artist" if kind=="Artists" else "release-group")
        st.session_state.results=rows;st.session_state.search_error=error
    if st.session_state.get("search_error"): st.warning(st.session_state.search_error)
    for item in st.session_state.get("results",[])[:20]:
        title=item.get("title") or item.get("name","Unknown")
        artist=", ".join(x.get("name","") for x in item.get("artist-credit",[]) if isinstance(x,dict))
        st.write("**"+title+"**"+(" — "+artist if artist else "")+"  ·  "+str(item.get("first-release-date","")))
    st.info("Catalogue results identify music; they do not provide downloadable commercial recordings. Use the Import tab for audio you have permission to save.")

with import_tab:
    st.subheader("Import your audio")
    paste=st.text_area("Paste YouTube links (one per line)",height=120,placeholder="https://www.youtube.com/watch?v=...")
    txt=st.file_uploader("Or upload a TXT list of links",type=["txt"])
    all_text=paste+"\n"+(txt.getvalue().decode("utf-8-sig",errors="replace") if txt else "")
    urls=links_from_text(all_text)
    st.caption(f"{len(urls)} unique supported links")
    if st.button("Preview links",type="primary"):
        st.session_state.queue=[]
        for url in urls[:100]:
            st.session_state.queue.append(fetch_details(url))
    if st.session_state.queue:
        st.subheader("Select tracks")
        for n,item in enumerate(st.session_state.queue):
            if item.get("error"): st.warning(f"Track {n+1}: {item['error']}")
            item["selected"]=st.checkbox(item["title"],item.get("selected",True),key=f"select-{n}")
        if st.button("Process selected links",type="primary"):
            selected=[x for x in st.session_state.queue if x.get("selected") and not x.get("error")]
            if not selected: st.warning("Select at least one available track.")
            else:
                progress=st.progress(0)
                with tempfile.TemporaryDirectory() as tmp:
                    for i,item in enumerate(selected):
                        try:
                            data,has_art=process_url(item,Path(tmp))
                            st.session_state.library.append({"name":clean(item["artist"]+" - "+item["title"])+".mp3","data":data,"art":has_art})
                            st.success(item["title"]+" — ready"+("" if has_art else " (cover unavailable)"))
                        except Exception as exc: st.error(item["title"]+" — "+str(exc)[:300])
                        progress.progress((i+1)/len(selected))
    st.divider()
    st.subheader("Upload an audio file")
    upload=st.file_uploader("Choose audio",type=["mp3","wav","m4a","flac","ogg","aac"])
    col1,col2=st.columns(2)
    with col1: title=st.text_input("Song title",key="songtitle"); album=st.text_input("Album (optional)",key="album")
    with col2: artist=st.text_input("Artist",key="songartist"); cover=st.file_uploader("Cover art (optional)",type=["jpg","jpeg","png","webp"])
    if st.button("Convert and embed metadata",type="primary",disabled=upload is None):
        try:
            data,has_art=process_upload(upload,title,artist,album,cover)
            st.session_state.library.append({"name":clean((artist or "Unknown Artist")+" - "+(title or Path(upload.name).stem))+".mp3","data":data,"art":has_art})
            st.success("MP3 ready for export.")
        except Exception as exc: st.error(str(exc)[:300])
    if st.button("New batch — clear inputs and selections"):
        st.session_state.queue=[]
        st.session_state.previewed=False
        st.rerun()

with library:
    st.subheader("Ready to download")
    if not st.session_state.library: st.info("Your processed tracks will appear here.")
    else:
        for i,item in enumerate(st.session_state.library):
            st.write(("🖼️" if item["art"] else "🎵")+" "+item["name"]+("" if item["art"] else " · no cover"))
            st.download_button("Download MP3",item["data"],file_name=item["name"],mime="audio/mpeg",key=f"download-{i}")
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
            used=set()
            for i,item in enumerate(st.session_state.library):
                name=item["name"]
                if name in used: name=f"{i+1:03d} - "+name
                used.add(name);z.writestr(name,item["data"])
        st.download_button("Download entire library as ZIP",archive.getvalue(),file_name="my-pod-promax.zip",mime="application/zip",type="primary")
        if st.button("Clear exported library"):
            st.session_state.library=[];st.rerun()
