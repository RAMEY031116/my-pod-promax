"""Key-free catalogue lookups, with conservative MusicBrainz request pacing."""
from __future__ import annotations
import json
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import requests

AGENT = 'myPodPromax/0.6 (https://github.com/bipzilla; music metadata client)'
_lock = threading.Lock()
_last = 0.0


def mb(path: str, params: dict | None = None) -> dict:
    """MusicBrainz requests use Requests' certifi CA roots (macOS friendly).

    Return useful errors instead of conflating TLS/proxy problems with no matches.
    """
    global _last
    url = 'https://musicbrainz.org/ws/2/' + path.lstrip('/')
    query = {**(params or {}), 'fmt': 'json'}
    with _lock:
        delay = 1.15 - (time.monotonic() - _last)
        if delay > 0: time.sleep(delay)
        _last = time.monotonic()
        last = None
        for attempt in range(3):
            try:
                response = requests.get(url, params=query, headers={'User-Agent': AGENT, 'Accept': 'application/json'}, timeout=(8, 20))
                if response.status_code in (429, 503):
                    last = f'MusicBrainz is busy (HTTP {response.status_code})'
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
                        continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.SSLError as exc:
                raise RuntimeError('Secure connection to MusicBrainz failed (certificate/TLS). Try updating certifi and check VPN or network filtering.') from exc
            except requests.exceptions.ProxyError as exc:
                raise RuntimeError('A proxy or VPN prevented access to MusicBrainz. Try another network or disable the proxy.') from exc
            except requests.exceptions.RequestException as exc:
                last = str(exc)
                if attempt < 2: time.sleep(attempt + 1)
            except ValueError as exc:
                raise RuntimeError('MusicBrainz returned unreadable data. Try again later.') from exc
    raise RuntimeError('MusicBrainz could not be reached: ' + str(last)[:180])


def itunes_search(term: str, kind: str = 'artist', limit: int = 20) -> list[dict]:
    """Key-free search backup for discovery only; never cache/embed Apple artwork."""
    response = requests.get('https://itunes.apple.com/search', params={
        'term': term, 'entity': 'musicArtist' if kind == 'artist' else 'album', 'limit': limit
    }, headers={'User-Agent': AGENT}, timeout=(6, 14))
    response.raise_for_status()
    return response.json().get('results', [])


def backup_albums(term: str) -> list[dict]:
    return [{'id': 'itunes:' + str(i['collectionId']), 'title':i.get('collectionName','Untitled'),
             'artist':i.get('artistName','Unknown Artist'), 'year':i.get('releaseDate','')[:4],
             'kind':'Album', 'source':'Apple catalogue (discovery only)'}
            for i in itunes_search(term, 'album') if i.get('collectionId')]


def backup_artists(term: str) -> list[dict]:
    return [{'id':'itunes:'+str(i['artistId']), 'name':i.get('artistName','Unknown'),
             'disambiguation':'Backup catalogue', 'country':''}
            for i in itunes_search(term, 'artist') if i.get('artistId')]


def backup_artist_albums(artist_id: str) -> list[dict]:
    if not artist_id.startswith('itunes:'): return []
    response=requests.get('https://itunes.apple.com/lookup', params={'id':artist_id[7:], 'entity':'album','limit':100}, timeout=(6,14))
    response.raise_for_status()
    return [{'id':'itunes:'+str(i['collectionId']), 'title':i.get('collectionName','Untitled'),
             'artist':i.get('artistName','Unknown Artist'),'year':i.get('releaseDate','')[:4], 'kind':'Album'}
            for i in response.json().get('results',[]) if i.get('wrapperType')=='collection']


def backup_album_tracks(group_id: str) -> tuple[dict, list[dict]]:
    response=requests.get('https://itunes.apple.com/lookup', params={'id':group_id[7:],'entity':'song','limit':200}, timeout=(6,14))
    response.raise_for_status()
    results=response.json().get('results',[])
    meta=next((i for i in results if i.get('wrapperType')=='collection'), {})
    tracks=[{'title':x.get('trackName',''), 'artist':x.get('artistName','Unknown Artist'),
             'number':x.get('trackNumber',n), 'disc':x.get('discNumber',1)}
            for n,x in enumerate(results,1) if x.get('wrapperType')=='track' and x.get('kind')=='song']
    return {'title':meta.get('collectionName','Album')}, tracks

def artist_label(item: dict) -> str:
    return ''.join(x.get('name', '') + x.get('joinphrase', '') for x in item.get('artist-credit', []) if isinstance(x, dict)) or 'Unknown Artist'


def search_albums(term: str, limit: int = 20) -> list[dict]:
    data = mb('release-group/', {'query': term, 'limit': limit})
    return [dict(id=x['id'], title=x['title'], artist=artist_label(x), year=x.get('first-release-date', '')[:4], kind=x.get('primary-type', '?')) for x in data.get('release-groups', [])]


def search_artists(term: str, limit: int = 15) -> list[dict]:
    data = mb('artist/', {'query': term, 'limit': limit})
    return [dict(id=x['id'], name=x['name'], disambiguation=x.get('disambiguation', ''), country=x.get('country', '')) for x in data.get('artists', [])]


def artist_albums(artist_id: str, limit: int = 100) -> list[dict]:
    data = mb('release-group/', {'arid': artist_id, 'type': 'album|ep|single', 'limit': min(limit, 100)})
    return [dict(id=x['id'], title=x['title'], artist=artist_label(x), year=x.get('first-release-date', '')[:4], kind=x.get('primary-type', '?')) for x in data.get('release-groups', [])]


def album_tracks(group_id: str) -> tuple[dict, list[dict]]:
    # A release-group represents multiple editions; choose a release to expose its actual tracklist.
    group = mb(f'release-group/{group_id}', {'inc': 'releases+artist-credits'})
    releases = group.get('releases', [])
    if not releases:
        return group, []
    chosen = next((r for r in releases if r.get('status') == 'Official' and r.get('country') in ('XW', 'GB', 'US')), releases[0])
    rel = mb('release/' + chosen['id'], {'inc': 'recordings+artist-credits'})
    tracks = []
    for disc_number, medium in enumerate(rel.get('media', []), 1):
        for idx, item in enumerate(medium.get('tracks', []), 1):
            artist = artist_label(item) if item.get('artist-credit') else artist_label(group)
            tracks.append({'title': item.get('title', ''), 'artist': artist, 'number': int(item.get('position') or idx), 'disc': disc_number})
    return group, tracks


def cover_url(group_id: str) -> str:
    return f'https://coverartarchive.org/release-group/{group_id}/front-500'


def album_cover(group_id: str) -> bytes | None:
    """Try release-group artwork, then an individual official release's art."""
    from .core import download_cover
    if group_id.startswith('itunes:'): return None  # Apple catalogue images are not embedded
    art = download_cover(cover_url(group_id))
    if art: return art
    try:
        releases = mb('release/', {'release-group': group_id, 'limit': 8}).get('releases', [])
        for release in sorted(releases, key=lambda r: r.get('status') != 'Official'):
            art = download_cover(f"https://coverartarchive.org/release/{release['id']}/front-500")
            if art: return art
    except Exception:
        return None
    return None


def normalized_track(value: str) -> str:
    """Remove presentation labels, not the musical identity of the title."""
    import re
    value = re.sub(r'(?i)\s*[\[(]\s*(official\s+)?(audio|music video|video|visuali[sz]er|lyrics?|hd|4k)\s*[\])]', '', value)
    value = re.sub(r'(?i)\s*\b(feat\.?|ft\.?|featuring)\s+.+$', '', value)
    return re.sub(r'[^a-z0-9]+', '', value.casefold())


def search_title(value: str) -> str:
    import re
    value = re.sub(r'(?i)\s*[\[(]\s*(official\s+)?(audio|music video|video|visuali[sz]er|lyrics?|hd|4k)\s*[\])]', '', value)
    return re.sub(r'(?i)\s*\b(feat\.?|ft\.?|featuring)\s+.+$', '', value).strip()


def find_track_art(title: str, artist: str) -> tuple[bytes | None, str]:
    """Try verified MusicBrainz releases, with loose search and strict match validation."""
    from .core import download_cover
    if not title or not artist or artist.casefold() in ('unknown artist', 'unknown'):
        return None, 'No reliable artist and title for a catalogue artwork search.'
    simple_title = search_title(title)
    simple_artist = artist.split(' - Topic')[0].split(' feat.')[0].strip()
    if not simple_title: return None, 'No searchable song title.'
    variants = [f'recording:"{simple_title[:85]}" AND artist:"{simple_artist[:70]}"',
                f'recording:"{simple_title[:85]}"']
    seen = set()
    try:
        for query in variants:
            matches = mb('recording/', {'query': query, 'limit': 15}).get('recordings', [])
            for rec in matches:
                if normalized_track(rec.get('title', '')) != normalized_track(title):
                    continue
                credits = artist_label(rec).casefold()
                # Don't use a different artist's album just because song titles match.
                if simple_artist.casefold() not in credits and credits not in simple_artist.casefold():
                    continue
                for release in rec.get('releases', []):
                    gid = release.get('release-group', {}).get('id')
                    rid = release.get('id')
                    for url in ([f'https://coverartarchive.org/release/{rid}/front-500'] if rid else []) + ([cover_url(gid)] if gid else []):
                        if url in seen: continue
                        seen.add(url)
                        artwork = download_cover(url)
                        if artwork:
                            return artwork, 'Matched album cover through MusicBrainz.'
        return None, 'No confirmed album art in the catalogue.'
    except Exception:
        return None, 'Catalogue artwork service unavailable.'
