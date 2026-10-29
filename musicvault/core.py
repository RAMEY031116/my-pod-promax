"""Media import, MP3 conversion, ID3 tagging and packaging for MusicVault."""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import requests
import zipfile
from pathlib import Path
from typing import Callable

from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK, TPOS
from mutagen import File as AudioFile
from PIL import Image

AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.opus', '.aac'}
YOUTUBE_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be', 'www.youtu.be'}


def clean_name(value: str, fallback: str = 'Unknown') -> str:
    value = re.sub(r'(?i)\s*[\[(](?:official (?:music )?video|lyrics?|audio|hd|4k|visuali[sz]er)[\])]', '', value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value).strip(' ._')
    return (value[:140].rstrip(' ._') or fallback)


def unique_path(folder: Path, stem: str, suffix: str = '.mp3') -> Path:
    root = clean_name(stem)
    candidate = folder / (root + suffix)
    count = 2
    while candidate.exists():
        candidate = folder / f'{root} ({count}){suffix}'
        count += 1
    return candidate


def parse_links(text: str) -> tuple[list[str], list[str]]:
    valid, invalid, seen = [], [], set()
    for raw in text.splitlines():
        url = raw.strip()
        if not url or url.startswith('#'):
            continue
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or '').lower()
        if parsed.scheme not in ('http', 'https') or host not in YOUTUBE_HOSTS:
            invalid.append(url)
            continue
        # Keep the scope small and avoid accidental playlist downloads.
        query = urllib.parse.parse_qs(parsed.query)
        video_id = query.get('v', [''])[0] if 'youtu.be' not in host else parsed.path.strip('/').split('/')[0]
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            invalid.append(url)
            continue
        canonical = f'https://www.youtube.com/watch?v={video_id}'
        if canonical not in seen:
            seen.add(canonical)
            valid.append(canonical)
    return valid, invalid


def ffmpeg_available() -> bool:
    return shutil.which('ffmpeg') is not None


def get_existing_tags(source: Path) -> tuple[str | None, str | None, bytes | None]:
    title = artist = None
    cover = None
    try:
        easy = AudioFile(source, easy=True)
        if easy is not None:
            title = (easy.get('title') or [None])[0]
            artist = (easy.get('artist') or [None])[0]
        if source.suffix.lower() == '.mp3':
            id3 = ID3(source)
            covers = id3.getall('APIC')
            if covers:
                cover = covers[0].data
        elif source.suffix.lower() == '.flac':
            f = AudioFile(source)
            if f is not None and getattr(f, 'pictures', None):
                cover = f.pictures[0].data
        elif source.suffix.lower() == '.m4a':
            f = AudioFile(source)
            artwork = (f.tags or {}).get('covr', []) if f else []
            if artwork: cover = bytes(artwork[0])
    except Exception:
        pass
    return title, artist, cover


def convert_to_mp3(source: Path, target: Path, bitrate: int) -> None:
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', str(source), '-vn', '-map', '0:a:0', '-codec:a', 'libmp3lame', '-b:a', f'{bitrate}k', str(target)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    if result.returncode != 0 or not target.is_file():
        raise RuntimeError((result.stderr or 'FFmpeg could not convert this file')[-700:])


def as_jpeg(data: bytes | None) -> bytes | None:
    if not data:
        return None
    try:
        with Image.open(io.BytesIO(data)) as image:
            image = image.convert('RGB')
            image.thumbnail((800, 800))
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=88)
            return buffer.getvalue()
    except Exception:
        return None


def _art_host_allowed(host: str) -> bool:
    host = (host or '').lower()
    return (host in {'i.ytimg.com', 'img.youtube.com', 'i9.ytimg.com',
                     'i1.ytimg.com', 'i2.ytimg.com', 'i3.ytimg.com', 'i4.ytimg.com',
                     'coverartarchive.org', 'archive.org', 'www.archive.org'}
            or host.endswith('.archive.org'))


def download_cover(url: str | None) -> bytes | None:
    """Retrieve a cover with Requests/certifi and validate each redirect.

    A failed image fetch must never destroy a valid MP3.
    """
    if not url: return None
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not _art_host_allowed(parsed.hostname or ''): return None
    try:
        with requests.Session() as session:
            session.headers.update({'User-Agent':'myPodPromax/0.7 (personal music metadata)',
                                    'Accept':'image/jpeg,image/png,image/webp,image/*;q=0.8'})
            response=session.get(url, timeout=(6,15), allow_redirects=False, stream=True)
            for _ in range(6):
                if response.status_code not in (301,302,303,307,308): break
                dest=urllib.parse.urljoin(response.url, response.headers.get('Location',''))
                parsed=urllib.parse.urlsplit(dest)
                if parsed.scheme == 'http' and _art_host_allowed(parsed.hostname or ''):
                    dest=urllib.parse.urlunsplit(('https',parsed.netloc,parsed.path,parsed.query,parsed.fragment))
                    parsed=urllib.parse.urlsplit(dest)
                if parsed.scheme != 'https' or not _art_host_allowed(parsed.hostname or ''): return None
                response.close()
                response=session.get(dest, timeout=(6,15), allow_redirects=False, stream=True)
            if response.status_code!=200: return None
            if not response.headers.get('Content-Type','').lower().startswith('image/'): return None
            content=bytearray()
            for block in response.iter_content(65536):
                content.extend(block)
                if len(content)>5_000_000: return None
            return as_jpeg(bytes(content))
    except requests.RequestException:
        return None


def youtube_thumbnail_candidates(info: dict, url: str) -> list[str]:
    """Prefer known available thumbnails, then the predictable YouTube variants."""
    candidates = []
    for thumb in reversed(info.get('thumbnails') or []):
        if thumb.get('url'): candidates.append(thumb['url'])
    if info.get('thumbnail'): candidates.append(info['thumbnail'])
    links, _ = parse_links(url)
    if links:
        video_id = urllib.parse.parse_qs(urllib.parse.urlsplit(links[0]).query)['v'][0]
        for name in ('maxresdefault', 'sddefault', 'hqdefault', 'mqdefault', 'default'):
            candidates.append(f'https://i.ytimg.com/vi/{video_id}/{name}.jpg')
    return list(dict.fromkeys(candidates))


def best_youtube_art(info: dict, url: str) -> bytes | None:
    for candidate in youtube_thumbnail_candidates(info, url):
        art = download_cover(candidate)
        if art: return art
    return None


def write_tags(path: Path, title: str, artist: str, cover: bytes | None, album: str = '', track: int | None = None, disc: int | None = None) -> None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    tags.delall('TIT2')
    tags.delall('TPE1')
    tags.delall('TALB')
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    if album:
        tags.add(TALB(encoding=3, text=album))
    if track:
        tags.delall('TRCK')
        tags.add(TRCK(encoding=3, text=str(track)))
    if disc:
        tags.delall('TPOS')
        tags.add(TPOS(encoding=3, text=str(disc)))
    if cover:
        tags.delall('APIC')
        tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover))
    tags.save(path, v2_version=3)


def import_upload(content: bytes, filename: str, output: Path, bitrate: int) -> Path:
    extension = Path(filename).suffix.lower()
    if extension not in AUDIO_EXTENSIONS:
        raise ValueError(f'Unsupported file type: {extension}')
    with tempfile.TemporaryDirectory(prefix='musicvault_') as temp:
        source = Path(temp) / ('original' + extension)
        source.write_bytes(content)
        title, artist, cover = get_existing_tags(source)
        title = str(title or Path(filename).stem)
        if not artist and ' - ' in title:
            artist, title = title.split(' - ', 1)
        artist = str(artist or 'Unknown Artist')
        target = unique_path(output, f'{artist} - {title}')
        try:
            convert_to_mp3(source, target, bitrate)
            write_tags(target, title, artist, as_jpeg(cover))
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target


def import_youtube(url: str, output: Path, bitrate: int) -> Path:
    from yt_dlp import YoutubeDL
    with tempfile.TemporaryDirectory(prefix='musicvault_') as temp:
        directory = Path(temp)
        options = {
            'format': 'bestaudio/best',
            'outtmpl': str(directory / '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 25,
            'retries': 2,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': str(bitrate)}],
        }
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
        if not info or info.get('_type') == 'playlist':
            raise RuntimeError('A single video is required.')
        files = list(directory.glob('*.mp3'))
        if not files:
            raise RuntimeError('No MP3 was produced. The source may be unavailable or restricted.')
        title = str(info.get('track') or info.get('title') or info.get('id') or 'Unknown Song')
        artist = str(info.get('artist') or info.get('creator') or info.get('uploader') or 'Unknown Artist')
        # First try a verified recording match; otherwise keep the source video's artwork.
        if not info.get('artist') and ' - ' in title:
            candidate_artist, candidate_title = title.split(' - ', 1)
            if candidate_artist.strip() and candidate_title.strip():
                artist, title = candidate_artist.strip(), candidate_title.strip()
        # Always capture the source thumbnail while the source is available.
        # Catalogue artwork is preferred when a confirmed release is found;
        # the thumbnail is an independent fallback, not a catalogue dependency.
        thumb = best_youtube_art(info, url)
        try:
            from .catalog import find_track_art
            album_art, _ = find_track_art(title, artist)
            if album_art:
                thumb = album_art
        except Exception:
            pass
        album = str(info.get('album') or '')
        track_num = info.get('track_number')
        try: track_num = int(track_num) if track_num else None
        except (ValueError, TypeError): track_num = None
        target = unique_path(output, f'{artist} - {title}')
        shutil.move(str(files[0]), str(target))
        try:
            write_tags(target, title, artist, thumb, album, track_num)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target


def zip_library(files: list[Path], destination: Path) -> Path:
    """Export tracks with bounded RAM usage and atomic cleanup on disk errors.

    Stored ZIP entries avoid wasting CPU recompressing MP3s. Export still needs
    enough disk space for a second copy; warn early instead of leaving a broken ZIP.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sources = [Path(file) for file in files if Path(file).is_file()]
    if not sources:
        raise ValueError('There are no music files to export.')

    # ZIP64 metadata and filesystem headroom; never rely on exact file sizes.
    required = sum(file.stat().st_size for file in sources)
    required += max(64 * 1024 * 1024, len(sources) * 1024)
    available = shutil.disk_usage(destination.parent).free
    if available < required:
        raise OSError(
            28,
            f'Not enough disk storage for library ZIP: approximately '
            f'{required / (1024 ** 3):.2f} GB needed, '
            f'{available / (1024 ** 3):.2f} GB free. '
            'Free some drive space or export songs individually.',
            str(destination),
        )

    # Keep an existing successful export intact until replacement succeeds.
    partial = destination.with_name(destination.name + '.partial')
    try:
        with zipfile.ZipFile(partial, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for file in sources:
                archive.write(file, arcname=file.name)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return destination


def import_upload_as_track(content: bytes, filename: str, output: Path, bitrate: int, *, title: str, artist: str, album: str, track: int, disc: int, cover: bytes | None) -> Path:
    extension = Path(filename).suffix.lower()
    if extension not in AUDIO_EXTENSIONS:
        raise ValueError('Unsupported audio format')
    with tempfile.TemporaryDirectory(prefix='mypod_') as temp:
        source = Path(temp) / ('source' + extension)
        source.write_bytes(content)
        target = unique_path(output, f'{artist} - {title}')
        try:
            convert_to_mp3(source, target, bitrate)
            write_tags(target, title, artist, cover, album, track, disc)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target


def import_youtube_as_track(url: str, output: Path, bitrate: int, *, title: str, artist: str, album: str, track: int, disc: int, cover: bytes | None) -> Path:
    path = import_youtube(url, output, bitrate)
    try:
        if cover is None:
            try:
                existing = ID3(path).getall('APIC')
                cover = existing[0].data if existing else None
            except Exception:
                pass
        write_tags(path, title, artist, cover, album, track, disc)
        desired = output / (clean_name(f'{artist} - {title}') + '.mp3')
        target = path if desired == path else unique_path(output, f'{artist} - {title}')
        if target != path:
            path.rename(target)
        return target
    except Exception:
        path.unlink(missing_ok=True)
        raise



def inspect_mp3(path: Path) -> dict:
    """Read resulting tags to verify artwork was actually embedded."""
    tags = ID3(path)
    def frame(key, fallback=''):
        item = tags.get(key)
        return str(item.text[0]) if item is not None and item.text else fallback
    return dict(title=frame('TIT2', path.stem), artist=frame('TPE1','Unknown Artist'),
                album=frame('TALB'), track=frame('TRCK'), cover=bool(tags.getall('APIC')))


def finalize_art(path: Path, *, auto_lookup: bool = True) -> dict:
    """Always return an exportable result; artwork lookup failures are warnings."""
    tags = inspect_mp3(path)
    if tags['cover']:
        return dict(path=path, warning='', **tags)
    warning = 'Cover not found. MP3 and other available metadata are ready.'
    if auto_lookup:
        from .catalog import find_track_art
        cover, reason = find_track_art(tags['title'], tags['artist'])
        if cover:
            try:
                write_tags(path, tags['title'], tags['artist'], cover,
                           tags['album'], int(tags['track'].split('/')[0]) if tags['track'] else None)
                tags = inspect_mp3(path)
                warning = ''
            except Exception:
                warning = 'Artwork was found but could not be embedded; MP3 is ready.'
        elif reason:
            warning = reason + ' MP3 is ready without cover.'
    return dict(path=path, warning=warning, **tags)


def embed_custom_metadata(path: Path, *, title: str, artist: str, album: str = '', cover: bytes | None = None) -> None:
    """Retag an existing MP3 without re-encoding it; preserve art unless explicitly replaced."""
    if cover is None:
        try:
            covers = ID3(path).getall('APIC')
            cover = covers[0].data if covers else None
        except Exception:
            pass
    write_tags(path, title, artist, cover, album)


def get_embedded_art(path: Path) -> bytes | None:
    try:
        arts = ID3(path).getall('APIC')
        return arts[0].data if arts else None
    except Exception:
        return None
