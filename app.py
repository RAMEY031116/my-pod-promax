"""my Pod promax: key-free iPod-ready music organiser."""
from __future__ import annotations
import base64
import re
import urllib.error
import pandas as pd
import shutil
import tempfile
import uuid
from pathlib import Path
import streamlit as st
from musicvault.catalog import search_albums, search_artists, artist_albums, album_tracks, album_cover, backup_albums, backup_artists, backup_artist_albums, backup_album_tracks
from musicvault.core import (write_tags, as_jpeg, ffmpeg_available, import_upload, import_youtube, import_upload_as_track,
    import_youtube_as_track, parse_links, zip_library, download_cover, finalize_art, inspect_mp3, embed_custom_metadata, get_embedded_art)

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='my Pod promax', page_icon='🎵', layout='wide', initial_sidebar_state='collapsed')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
:root {color-scheme:light!important;}
html, body, .stApp {font-family:'DM Sans',sans-serif!important;}
.stApp {background:#fbf9fb!important;color:#302333!important;}
.block-container {max-width:1120px;padding-top:1.3rem;padding-bottom:4rem;}
h1,h2,h3 {color:#302333!important;letter-spacing:-.04em;}
[data-testid="stHeader"] {background:transparent!important;}
[data-testid="stMetric"] {background:white;border:1px solid #f1e4ec;border-radius:16px;padding:12px 15px;}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {color:#302333!important;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:18px!important;}
[data-testid="stImage"] img {border-radius:13px;}
.stTabs [data-baseweb="tab-list"] {gap:8px;border-bottom:1px solid #eee1e9;}
.stTabs [data-baseweb="tab"] {color:#594357!important;font-weight:700!important;}
.stTabs [aria-selected="true"] {color:#ac296b!important;}
/* Make all clickable buttons readable, including Streamlit 1.6x and file upload controls. */
.stApp button, .stApp [role="button"] {color:#45243b!important;-webkit-text-fill-color:#45243b!important;background:#ffffff!important;border:1px solid #d6a8be!important;border-radius:11px!important;opacity:1;}
.stApp button :is(p,span,div,small), .stApp [role="button"] :is(p,span,div,small) {color:inherit!important;-webkit-text-fill-color:inherit!important;}
.stApp button svg,.stApp [role="button"] svg {color:inherit!important;stroke:currentColor!important;}
.stApp button:hover, .stApp [role="button"]:hover {background:#fff0f7!important;border-color:#c13b7b!important;color:#912c61!important;}
.stApp button[kind="primary"],.stApp button[data-testid="stBaseButton-primary"],.stApp button[data-testid="baseButton-primary"] {background:#bf3279!important;border-color:#bf3279!important;color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;}
.stApp button[kind="primary"] :is(p,span,div,small), .stApp button[data-testid="stBaseButton-primary"] :is(p,span,div,small) {color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;}
.stApp button[kind="primary"]:hover, .stApp button[data-testid="stBaseButton-primary"]:hover {background:#a62665!important;border-color:#a62665!important;}
.stApp button:disabled {opacity:.52!important;cursor:not-allowed!important;}
[data-testid="stFileUploader"] section {background:#fff8fc!important;border:1px dashed #d9acc1!important;border-radius:12px!important;}
[data-testid="stFileUploader"] button {background:#ffffff!important;color:#45243b!important;-webkit-text-fill-color:#45243b!important;}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-baseweb="select"]>div {background:#ffffff!important;color:#302333!important;-webkit-text-fill-color:#302333!important;border-color:#e8d5e0!important;}
[data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder {color:#847487!important;opacity:1;}
[data-testid="stAlert"] p {color:inherit!important;}
 /* Consistent readable text for Streamlit Cloud light UI; preserve alert colours and pink primary controls. */
 [data-testid="stAppViewContainer"] {background:#fbf9fb!important;color:#302333!important;}
 [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
 [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
 [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
 [data-testid="stExpander"] summary, [data-testid="stExpander"] summary p,
 [data-testid="stDataFrame"] {color:#302333!important;}
 [data-testid="stFileUploader"] small, [data-testid="stFileUploader"] span {color:#45243b!important;}
 [data-testid="stTabs"] [role="tab"] {color:#594357!important;}
 [data-testid="stTabs"] [role="tab"][aria-selected="true"] {color:#a62665!important;}
 .stApp button[kind="primary"], .stApp button[data-testid="stBaseButton-primary"] {background:#bf3279!important;color:#fff!important;-webkit-text-fill-color:#fff!important;}
 .stApp button[kind="primary"] *, .stApp button[data-testid="stBaseButton-primary"] * {color:#fff!important;-webkit-text-fill-color:#fff!important;}

.mypod-head{display:flex;align-items:center;justify-content:space-between;padding:8px 0 18px;border-bottom:1px solid #f0e4ec;margin-bottom:20px}
.mypod-brand{font-weight:800;font-size:1.35rem;letter-spacing:-.045em;color:#302333}
.mypod-brand span{color:#d84e92}.mypod-meta{font-size:.85rem;color:#8b7b8b}
.mypod-hero{display:flex;align-items:center;justify-content:space-between;background:linear-gradient(120deg,#fff4fa,#ffedf5);border:1px solid #f6dce9;border-radius:24px;padding:22px 32px;min-height:180px;margin-bottom:18px}
.mypod-hero h1{margin:3px 0 10px;font-weight:800}.mypod-hero p{max-width:550px;color:#786477;margin:0;font-size:1rem}
.mypod-kicker{color:#a9306c;font-weight:800;font-size:.76rem;letter-spacing:.13em}
.mypod-note{border:1px solid #f1e1e9;background:white;padding:14px 16px;border-radius:14px;color:#6e6070;font-size:.90rem;margin:10px 0 16px}
.mypod-pill{display:inline-block;padding:5px 10px;border-radius:20px;background:#fae3ee;color:#a6336a;font-weight:700;font-size:.74rem;margin-top:10px}
@media(max-width:650px){.mypod-hero{padding:18px;gap:10px}.mypod-hero h1{font-size:2rem!important}.mypod-meta{display:none}.block-container{padding-left:1rem;padding-right:1rem}}
</style>''', unsafe_allow_html=True)

DEFAULTS={'preview_links':[], 'batch_id':None,'album':None,'tracks':[],'album_results':[],'artist_results':[],
          'artist_releases':[],'results':[],'zip_path':None,'search_term':'','link_text':'','query_type':'Album', 'source_urls':{}}
for key,val in DEFAULTS.items():
    if key not in st.session_state: st.session_state[key]=val
if st.session_state.batch_id is None: st.session_state.batch_id=uuid.uuid4().hex
if 'workspace' not in st.session_state:
    st.session_state.workspace=str(Path(tempfile.gettempdir())/('mypod_'+uuid.uuid4().hex))
work=Path(st.session_state.workspace)
songs=work/'songs'
songs.mkdir(parents=True,exist_ok=True)

def reset_batch():
    """Start a new queue while preserving successfully processed library tracks."""
    st.session_state.batch_id=uuid.uuid4().hex
    for key in ['album','tracks','album_results','artist_results','artist_releases','results','zip_path','preview_links']:
        st.session_state[key]=DEFAULTS[key].copy() if isinstance(DEFAULTS[key],list) else DEFAULTS[key]
    for key in list(st.session_state.keys()):
        if key.startswith(('album_file_', 'include_', 'source_', 'track_link_', 'source_files_', 'bulk_files_', 'txt_file_', 'links_text_', 'editor_', 'preview_')):
            del st.session_state[key]

def record(label, path=None, error=None, cover_hint=''):
    if error:
        st.session_state.results.append({'name':label,'status':'Failed','detail':friendly_error(error),'path':None})
        return
    try:
        enriched=finalize_art(path)
        detail='Artwork embedded' if enriched['cover'] else enriched['warning']
    except Exception:
        enriched={'cover':False}
        detail='MP3 created; metadata verification could not complete.'
    st.session_state.results.append({'name':label,'status':'Ready' if enriched.get('cover', False) else 'Ready · no cover', 'detail':detail,'path':str(path)})

def friendly_error(e):
    """Explain root causes without mislabelling a provider/network failure as a bad URL."""
    import requests
    value=str(e).strip().replace('\\n',' ')
    low=value.lower()
    if isinstance(e, requests.exceptions.SSLError) or any(t in low for t in ('certificate verify', 'ssl certificate', 'tls handshake')):
        return 'TLS certificate verification failed. Check network and hosting logs; this is not evidence of an invalid video link.'
    if isinstance(e, requests.exceptions.Timeout) or any(t in low for t in ('timed out', 'timeout')):
        return 'The source did not respond before the timeout. Retry later; this does not mean the URL is invalid.'
    if isinstance(e, requests.exceptions.ConnectionError) or any(t in low for t in ('name resolution', 'failed to establish', 'network is unreachable', 'connection refused')):
        return 'The server could not reach the source. Check hosting-network access and DNS before retrying.'
    if 'no space left' in low or 'errno 28' in low:
        return 'Temporary storage is full. Export saved tracks, free space, and use a smaller batch.'
    if '429' in low or 'too many requests' in low or 'rate limit' in low:
        return 'The provider is rate-limiting requests (HTTP 429). Retry after the requested interval, if provided.'
    if '403' in low or 'forbidden' in low:
        return 'Source returned HTTP 403. The hosting server may be blocked or the video may require authorisation. A delay will not necessarily help.'
    if 'sign in' in low or 'private video' in low or 'members-only' in low or 'login required' in low:
        return 'This video requires a signed-in or authorised account. Use an accessible source you have permission to download.'
    if '404' in low or 'video unavailable' in low or 'not available' in low:
        return 'Video unavailable or removed from the source. Check it in your browser.'
    if 'ffmpeg' in low or 'postprocessing' in low: return 'Audio conversion failed. Check FFmpeg, temporary disk space and the source audio; see Cloud logs for details.'
    if 'unsupported' in low: return 'Unsupported media format or link. Try an authorised compatible source.'
    if 'musicbrainz' in low or 'catalogue' in low or 'itunes' in low: return value[:260]
    if 'youtube' in low or 'url' in low:
        return 'YouTube could not serve this video to the app. If many valid links fail on Streamlit Cloud, the hosting IP or extractor may be restricted. Check server logs; do not assume the URLs are wrong.'
    return ('Could not process this item: '+value[:240]) if value else 'Unknown processing error. Inspect server logs.'



def search_with_backup(mode, query):
    """Fallback on both failure and empty results, recording which provider succeeded."""
    errors=[]
    for label, func in [('MusicBrainz', search_albums if mode=='Album' else search_artists),
                        ('Backup catalogue', backup_albums if mode=='Album' else backup_artists)]:
        try:
            found=func(query)
            if found:
                return found,label,errors
            errors.append(f'{label}: no matches')
        except Exception as exc:
            errors.append(f'{label}: {friendly_error(exc)}')
    return [],None,errors


def browse_releases(artist):
    """If MusicBrainz artist releases fail or are empty, find backup artist by name."""
    messages=[]
    if artist['id'].startswith('itunes:'):
        try:
            return backup_artist_albums(artist['id']),['Using backup catalogue']
        except Exception as exc:
            messages.append('Backup catalogue: '+friendly_error(exc))
    else:
        try:
            releases=artist_albums(artist['id'])
            if releases: return releases,['Using MusicBrainz']
            messages.append('MusicBrainz: no releases returned')
        except Exception as exc:
            messages.append('MusicBrainz: '+friendly_error(exc))
        try:
            options=backup_artists(artist['name'])
            choice=next((x for x in options if x['name'].casefold()==artist['name'].casefold()), None)
            if choice:
                releases=backup_artist_albums(choice['id'])
                if releases: return releases,messages+['Switched to backup catalogue']
            messages.append('Backup catalogue: no matching artist releases')
        except Exception as exc:
            messages.append('Backup catalogue: '+friendly_error(exc))
    return [],messages

def run_tasks(tasks):
    st.session_state.results=[]
    progress=st.progress(0)
    status=st.empty()
    for idx,(label,fn) in enumerate(tasks,1):
        status.caption(f'Processing {idx} of {len(tasks)} · {label}')
        try:
            path=fn()
            record(label,path=path)
        except Exception as exc:
            record(label,error=exc)
        progress.progress(idx/len(tasks))
    status.empty()
    ready=sum(r['status'].startswith('Ready') for r in st.session_state.results)
    failed=len(tasks)-ready
    if ready: st.success(f'{ready} track(s) ready. Open Your Library to export.'+ (f' {failed} item(s) need attention.' if failed else ''))
    else:
        st.error('No tracks were produced. Review the per-track errors below.')
        if len(tasks) >= 3:
            st.warning('Every item in this batch failed. On Streamlit Cloud, this can indicate an IP/network restriction or an upstream extractor problem, not  necessarily bad links. Try one authorised source on your Mac to compare. Check Streamlit Cloud logs before retrying a large batch. Adding a fixed delay will not fix HTTP 403.')

def show_results():
    if not st.session_state.results: return
    st.markdown('#### Latest batch')
    for item in st.session_state.results:
        prefix='✅' if item['status'].startswith('Ready') else '⚠️'
        with st.expander(f"{prefix} {item['name']}  ·  {item['status']}",expanded=item['status']=='Failed'):
            st.write(item['detail'])

@st.cache_data(ttl=3600, show_spinner=False)
def cached_cover(group_id: str) -> bytes | None:
    return album_cover(group_id)

raw= (ROOT/'assets/ipod.svg').read_bytes()
svg64=base64.b64encode(raw).decode('ascii')
st.markdown('<div class="mypod-head"><div class="mypod-brand">♫ my <span>Pod</span> promax</div><div class="mypod-meta">curated for your pocket · by Bipzilla</div></div>',unsafe_allow_html=True)
st.markdown(f'''<div class="mypod-hero"><div><div class="mypod-kicker">YOUR POCKET MUSIC COLLECTION</div><h1>Make music yours.</h1><p>Find an album. Choose your tracks. Prepare clean MP3s with proper tags and cover artwork, ready for your iPod.</p><span class="mypod-pill">Made for your music library</span></div><img alt="Pink pocket music player" src="data:image/svg+xml;base64,{svg64}" style="height:176px;max-width:37%;object-fit:contain"/></div>''',unsafe_allow_html=True)

head_left,head_mid,head_right=st.columns([1,1,2])
head_left.metric('Saved MP3s',len(list(songs.glob('*.mp3'))))
head_mid.metric('Last batch',len(st.session_state.results))
with head_right:
    st.write('')
    if st.button('↻ New batch · keep saved songs',key='new_batch',width='stretch'):
        reset_batch();st.rerun()
if not ffmpeg_available(): st.error('FFmpeg not found. Install FFmpeg, restart your terminal, and refresh the page.')

find_tab, import_tab, library_tab=st.tabs(['⌕  Discover music','↥  Import audio / links','♫  Your library'])
with find_tab:
    st.subheader('Find your next record')
    st.caption('Search albums and artists. MusicBrainz is preferred; an Apple catalogue backup supplies track listings if it is offline. Audio is imported separately.')
    c1,c2=st.columns([1,3])
    with c1: mode=st.selectbox('Find by',['Album','Artist'],key='query_type')
    with c2: query=st.text_input('Album or artist name',key='search_term',placeholder='Try: Discovery or Daft Punk')
    if st.button('Search catalogue',type='primary',disabled=not query.strip()):
        with st.spinner('Searching music catalogues…'):
            found,provider,details=search_with_backup(mode,query.strip())
        st.session_state.album_results=found if mode=='Album' else []
        st.session_state.artist_results=found if mode=='Artist' else []
        st.session_state.artist_releases=[]; st.session_state.album=None;st.session_state.tracks=[]
        if provider:
            st.success(f'{len(found)} result(s) from {provider}.')
            if details:
                with st.expander('Other catalogue attempts'):
                    for note in details: st.caption(note)
        else:
            st.warning('No results could be loaded. Your search was not necessarily invalid.')
            for note in details: st.caption('• '+note)
            st.info('Try a shorter artist name, check Connection diagnostics near the bottom, or import a song using a link or file.')
    if mode=='Artist' and st.session_state.artist_results:
        artists=st.session_state.artist_results
        pick=st.selectbox('Choose artist',range(len(artists)),format_func=lambda i:f"{artists[i]['name']} · {artists[i]['country']} {artists[i]['disambiguation']}")
        if st.button('Browse artist releases'):
            with st.spinner('Loading releases…'):
                releases_found,notes=browse_releases(artists[pick])
            st.session_state.artist_releases=releases_found
            if releases_found: st.success(f'{len(releases_found)} releases loaded.')
            else: st.warning('This artist’s releases could not be loaded. You can still import audio from the Import tab.')
            with st.expander('Search details',expanded=not bool(releases_found)):
                for note in notes: st.write('• '+note)
    releases=st.session_state.artist_releases if mode=='Artist' else st.session_state.album_results
    if releases:
        st.markdown('#### Pick a release')
        pick=st.selectbox('Album / EP / single',range(len(releases)),format_func=lambda i:f"{releases[i]['title']} · {releases[i]['artist']} · {releases[i]['year']} · {releases[i]['kind']}")
        selection=releases[pick]
        left,right=st.columns([1,4],vertical_alignment='center')
        with left:
            # Missing covers can be frequent. Do not expose remote image errors to the user.
            art=cached_cover(selection['id'])
            if art: st.image(art,width='stretch')
            else: st.caption('No embeddable catalogue cover available — video thumbnails are tried when processing.')
        with right:
            st.markdown('### '+selection['title'])
            st.caption(f"{selection['artist']} · {selection['year']}")
            if st.button('Show album tracklist',type='primary'):
                try:
                    with st.spinner('Loading tracks…'):
                        details,tracks=(backup_album_tracks(selection['id']) if selection['id'].startswith('itunes:') else album_tracks(selection['id']))
                    st.session_state.album={**selection,'title':details.get('title',selection['title'])}
                    st.session_state.tracks=tracks
                    if not tracks: st.warning('No tracklist was available for this edition. You can still import individual songs.')
                except Exception as e: st.error('Tracklist unavailable: '+friendly_error(e))
    album=st.session_state.album
    if album and st.session_state.tracks:
        tracks=st.session_state.tracks
        bid=st.session_state.batch_id
        st.divider()
        st.markdown('### '+album['title'])
        st.caption('Tick the songs you want and attach your own audio or an authorised link. Unassigned tracks will be skipped.')
        files=st.file_uploader('Upload audio to match to tracks',type=['mp3','m4a','wav','flac','ogg','opus','aac'],accept_multiple_files=True,key='source_files_'+bid) or []
        assignments=[]
        for index,track in enumerate(tracks):
            key=f"{bid}_{album['id']}_{index}"
            with st.expander(f"{track['disc']}.{track['number']:02d}  {track['title']}   ·   {track['artist']}"):
                included=st.checkbox('Include this track',key='include_'+key,value=True)
                method=st.selectbox('Audio source',['Not assigned','Uploaded audio','Authorised YouTube link'],key='source_'+key)
                selected_file=None;link=''
                if method=='Uploaded audio':
                    if files:
                        fileno=st.selectbox('Match a file',list(range(len(files))),format_func=lambda n:files[n].name,key='album_file_'+key)
                        selected_file=files[fileno]
                    else: st.info('Upload files above to match this song.')
                if method=='Authorised YouTube link': link=st.text_input('Video link',key='track_link_'+key)
                if included and (selected_file is not None or method=='Authorised YouTube link' and link.strip()):
                    assignments.append((track,selected_file,link))
        st.caption(f'{len(assignments)} track(s) with assigned audio')
        if st.button('Process selected tracks',type='primary',disabled=not assignments or not ffmpeg_available()):
            cover=cached_cover(album['id'])
            if not cover: st.info('Album cover not found. I will still process every assigned track and try individual artwork matches.')
            tasks=[]
            for track,file,link in assignments:
                common=dict(title=track['title'],artist=track['artist'],album=album['title'],track=track['number'],disc=track['disc'],cover=cover)
                if file is not None:
                    data=file.getvalue();name=file.name
                    tasks.append((track['title'],lambda data=data,name=name,common=common: import_upload_as_track(data,name,songs,192,**common)))
                else:
                    urls,invalid=parse_links(link)
                    def download(urls=urls,invalid=invalid,common=common):
                        if len(urls)!=1 or invalid: raise ValueError('Provide one valid authorised YouTube video link.')
                        return import_youtube_as_track(urls[0],songs,192,**common)
                    tasks.append((track['title'],download))
            run_tasks(tasks)
        show_results()

with import_tab:
    st.subheader('Import your music')
    st.caption('Paste one or many video links, import a TXT list, or upload audio. Preview and choose which tracks to process.')
    bid=st.session_state.batch_id
    left,right=st.columns([1.2,1])
    with left:
        links=st.text_area('Paste YouTube song links',height=180,placeholder='Paste links, one per line\nhttps://www.youtube.com/watch?v=...',key='links_text_'+bid)
        txt=st.file_uploader('Upload a TXT list of links',type=['txt'],key='txt_file_'+bid)
    with right:
        uploads=st.file_uploader('Or upload your audio files',type=['mp3','m4a','wav','flac','ogg','opus','aac'],accept_multiple_files=True,key='bulk_files_'+bid) or []
        bitrate=st.select_slider('Output quality',options=[128,192,256,320],value=192,format_func=lambda x:f'{x} kbps',key='quality_'+bid)
        st.caption('Choose your original source quality carefully. Higher encoding bitrates cannot restore lost detail.')
    if txt:
        try: links+='\n'+txt.getvalue().decode('utf-8-sig')
        except UnicodeDecodeError: st.warning('TXT file must be UTF-8 encoded. Save it as UTF-8 and try again.')
    urls,invalid=parse_links(links)
    st.caption(f'{len(urls)} unique video links · {len(uploads)} audio uploads · {len(invalid)} invalid entries')
    if invalid:
        with st.expander(f'Review {len(invalid)} unsupported / invalid link(s)'):
            for bad in invalid[:40]: st.code(bad)
    if st.button('Preview video information',disabled=not urls,key='preview_'+bid):
        from yt_dlp import YoutubeDL
        previews=[]
        with st.spinner('Reading available song information…'):
            for url in urls:
                try:
                    with YoutubeDL({'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True,'socket_timeout':15,'retries':1}) as dl:
                        info=dl.extract_info(url,download=False)
                    title=str(info.get('track') or info.get('title') or 'Untitled')
                    artist=str(info.get('artist') or info.get('creator') or info.get('uploader') or 'Unknown Artist')
                    if not info.get('artist') and ' - ' in title:
                        artist,title=title.split(' - ',1)
                    previews.append({'url':url,'title':title,'artist':artist,'album':str(info.get('album') or ''),'error':''})
                except Exception as exc:
                    previews.append({'url':url,'title':'Unknown song','artist':'Unknown Artist','album':'','error':friendly_error(exc)})
        st.session_state.preview_links=previews
    previous={item['url']:item for item in st.session_state.preview_links}
    rows=[]
    for url in urls:
        prior=previous.get(url,{})
        rows.append({'Include':True,'Source':url,'Title':prior.get('title',''),'Artist':prior.get('artist',''),'Album':prior.get('album',''),'Preview issue':prior.get('error','')})
    for upload in uploads:
        rows.append({'Include':True,'Source':'FILE: '+upload.name,'Title':'','Artist':'','Album':'','Preview issue':''})
    if rows:
        st.markdown('#### Choose your tracks')
        st.caption('Uncheck items to skip them. Optionally edit Title, Artist and Album; blank fields use detected information. Preview problems do not stop processing.')
        edited=st.data_editor(pd.DataFrame(rows),hide_index=True,width='stretch',num_rows='fixed',key='editor_'+bid,
            column_config={'Include':st.column_config.CheckboxColumn('Select',width='small'),
                           'Source':st.column_config.TextColumn('Source',disabled=True,width='large'),
                           'Preview issue':st.column_config.TextColumn('Preview issue',disabled=True)},
            disabled=['Source','Preview issue'])
        selected=edited[edited['Include']==True].to_dict('records')
        st.caption(f'{len(selected)} selected · {len(rows)-len(selected)} skipped')
    else:
        selected=[]
        st.info('Add a YouTube URL, TXT file or audio upload to begin.')
    if st.button('Process selected songs',type='primary',disabled=not ffmpeg_available() or not selected,key='process_'+bid):
        tasks=[]
        upload_map={f.name:f for f in uploads}
        for row in selected:
            source=row['Source']
            title=str(row.get('Title') or '').strip() if pd.notna(row.get('Title')) else ''
            artist=str(row.get('Artist') or '').strip() if pd.notna(row.get('Artist')) else ''
            album_name=str(row.get('Album') or '').strip() if pd.notna(row.get('Album')) else ''
            def task(source=source,title=title,artist=artist,album_name=album_name):
                if source.startswith('FILE: '):
                    fname=source[6:]
                    upload=upload_map[fname]
                    result=import_upload(upload.getvalue(),fname,songs,bitrate)
                else:
                    result=import_youtube(source,songs,bitrate)
                if title or artist or album_name:
                    known=inspect_mp3(result)
                    embed_custom_metadata(result,title=title or known['title'],artist=artist or known['artist'],album=album_name or known['album'])
                if not source.startswith('FILE: '):
                    st.session_state.source_urls[str(result)]=source
                return result
            tasks.append((source,task))
        run_tasks(tasks)
    show_results()

with library_tab:
    st.subheader('Your iPod-ready music')
    available=sorted(songs.glob('*.mp3'),key=lambda p:p.name.lower())
    st.caption(f'{len(available)} MP3 file(s) · Stored in a temporary local workspace until you close or clear the environment. Export your ZIP to keep them.')
    if not available: st.info('Nothing here yet. Discover an album or import your first song.')
    st.caption('Cover art is embedded directly into each MP3. Missing artwork? Repair a track below without downloading its audio again.')
    for idx,path in enumerate(available):
        try: tags=inspect_mp3(path)
        except Exception: tags={'artist':'Unknown Artist','title':path.stem,'album':'','cover':False}
        art=get_embedded_art(path)
        iconcol,a,b=st.columns([0.65,5,1.2],vertical_alignment='center')
        with iconcol:
            if art: st.image(art,width=56)
            else: st.markdown('🎵')
        with a:
            st.markdown(f"**{tags['title']}**")
            st.caption(tags['artist']+((' · '+tags['album']) if tags['album'] else '')+(' · Artwork ✓' if tags['cover'] else ' · Cover unavailable'))
        with b:
            with open(path,'rb') as handle:
                st.download_button('Download',handle,file_name=path.name,mime='audio/mpeg',key='dl_'+str(idx))
        if True:
            with st.expander(('Fix missing artwork · ' if not tags['cover'] else 'Replace artwork · ')+tags['title']):
                st.caption('Retry album artwork, use a YouTube video thumbnail, or upload a cover. Changes are embedded in the MP3; download the updated file afterwards.')
                custom_title=st.text_input('Track title',value=tags['title'],key=f'art_title_{idx}')
                custom_artist=st.text_input('Artist',value=tags['artist'],key=f'art_artist_{idx}')
                art_file=st.file_uploader('Upload cover image',type=['jpg','jpeg','png','webp'],key=f'art_file_{idx}')
                art_video=st.text_input('YouTube video URL for thumbnail (optional)',placeholder='https://www.youtube.com/watch?v=...',key=f'art_video_{idx}')
                remembered=st.session_state.source_urls.get(str(path))
                if remembered and not tags['cover'] and st.button('Retry source thumbnail automatically',key=f'auto_art_{idx}'):
                    from musicvault.core import best_youtube_art
                    with st.spinner('Checking direct YouTube thumbnail URLs…'):
                        cover=best_youtube_art({},remembered)
                    if cover:
                        write_tags(path,custom_title,custom_artist,cover,tags['album'])
                        st.success('Thumbnail embedded in MP3. Download the refreshed file.');st.rerun()
                    else:
                        st.warning('Direct thumbnails were unavailable. Check whether your Mac can access i.ytimg.com, or upload an image.')
                a1,a2=st.columns(2)
                with a1:
                    if st.button('Search for artwork',key=f'retry_art_{idx}'):
                        try:
                            from musicvault.catalog import find_track_art
                            with st.spinner('Looking for a matching album cover…'):
                                found, reason=find_track_art(custom_title,custom_artist)
                            if found:
                                write_tags(path,custom_title,custom_artist,found,tags['album'])
                                st.success('Cover embedded in MP3.');st.rerun()
                            else: st.warning(reason+' You can still export the MP3.')
                        except Exception as exc: st.warning('Could not search for artwork: '+friendly_error(exc))
                if st.button('Use video thumbnail',key=f'thumbnail_fix_{idx}',disabled=not art_video.strip()):
                    try:
                        from yt_dlp import YoutubeDL
                        from musicvault.core import best_youtube_art
                        urls, bad=parse_links(art_video.strip())
                        if not urls: st.warning('Enter one valid YouTube video URL.')
                        else:
                            with st.spinner('Checking video artwork…'):
                                cover=best_youtube_art({},urls[0])
                            if cover:
                                write_tags(path,custom_title,custom_artist,cover,tags['album'])
                                st.success('Video artwork embedded into MP3.');st.rerun()
                            else: st.warning('YouTube did not supply a usable thumbnail. Try uploading a JPG or PNG.')
                    except Exception as exc: st.warning('Thumbnail lookup failed: '+friendly_error(exc))
                with a2:
                    if st.button('Save artwork & details',key=f'save_art_{idx}',disabled=not art_file):
                        art=as_jpeg(art_file.getvalue()) if art_file else None
                        if art:
                            write_tags(path,custom_title,custom_artist,art,tags['album'])
                            st.success('Artwork embedded in MP3.');st.rerun()
                        else: st.error('This image could not be read. Try JPG or PNG.')
        st.divider()
    if available:
        if st.button('Prepare ZIP of all saved tracks'):
            st.session_state.zip_path=str(zip_library(available,work/'my_Pod_promax_library.zip'))
        if st.session_state.zip_path and Path(st.session_state.zip_path).exists():
            with open(st.session_state.zip_path,'rb') as handle:
                st.download_button('Download full MP3 library (ZIP)',handle,file_name='my_Pod_promax_library.zip',mime='application/zip',type='primary')
    if st.button('Delete all saved tracks',disabled=not available):
        shutil.rmtree(songs,ignore_errors=True);songs.mkdir(parents=True,exist_ok=True)
        st.session_state.zip_path=None
        st.rerun()

st.markdown('<div class="mypod-note"><b>About audio:</b> Album/artist discovery supplies track names and cover art, not the recordings themselves. Import audio you own or have permission to download. Missing cover art will never prevent the MP3 from being exported.</div>',unsafe_allow_html=True)

st.caption('my Pod promax · by Bipzilla · Personal music organiser')

with st.expander('Connection diagnostics · search or covers not loading?'):
    st.caption('Checks are optional and report the actual host and error rather than hiding network failures.')
    if st.button('Test catalogue and thumbnail connections'):
        import requests
        endpoints={'MusicBrainz':'https://musicbrainz.org/ws/2/artist/?query=Central%20Cee&fmt=json&limit=1',
                   'Backup catalogue':'https://itunes.apple.com/search?term=Central+Cee&entity=musicArtist&limit=1',
                   'YouTube thumbnails':'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg',
                   'Cover Art Archive':'https://coverartarchive.org/release-group/0b213a5a-4c75-35c3-a60b-8ac16319acfc/front-500'}
        for label,url in endpoints.items():
            try:
                r=requests.get(url,timeout=10,headers={'User-Agent':'myPodPromax/0.8 (personal music metadata)'},stream=True)
                st.write(f'{label}: HTTP {r.status_code} · '+('reachable' if r.ok else 'not available (some covers legitimately return 404)'))
                r.close()
            except Exception as exc: st.error(f'{label}: {type(exc).__name__}: {str(exc)[:220]}')
