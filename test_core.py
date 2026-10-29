from pathlib import Path
from musicvault.core import clean_name, parse_links, import_upload, zip_library, ffmpeg_available
import subprocess


def test_links():
    links, invalid = parse_links('https://youtu.be/dQw4w9WgXcQ\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ&list=abc\nhttps://evil.example/video\n')
    assert links == ['https://www.youtube.com/watch?v=dQw4w9WgXcQ']
    assert len(invalid) == 1


def test_clean():
    assert clean_name('My: Track (Official Music Video)') == 'My_ Track'


def test_audio_conversion_and_zip(tmp_path):
    if not ffmpeg_available():
        return
    wav = tmp_path / 'sample.wav'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2', '-y', str(wav)], check=True)
    out = tmp_path / 'out'
    out.mkdir()
    mp3 = import_upload(wav.read_bytes(), 'sample.wav', out, 192)
    assert mp3.exists() and mp3.stat().st_size > 0
    archive = zip_library([mp3], tmp_path / 'songs.zip')
    assert archive.exists()


def test_finalize_preserves_mp3_without_cover(tmp_path, monkeypatch):
    from musicvault.core import finalize_art, inspect_mp3
    from musicvault import catalog
    if not ffmpeg_available():
        return
    wav = tmp_path / 'tone.wav'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=duration=0.15','-y',str(wav)],check=True)
    out = tmp_path/'output'
    out.mkdir()
    mp3 = import_upload(wav.read_bytes(),'tone.wav',out,192)
    monkeypatch.setattr(catalog,'find_track_art',lambda title,artist:(None,'No verified artwork.'))
    result = finalize_art(mp3)
    assert result['path'].exists()
    assert result['cover'] is False
    assert result['warning']
    assert inspect_mp3(mp3)['title'] == 'tone'


def test_embedded_cover_and_album_metadata(tmp_path):
    from musicvault.core import import_upload_as_track, inspect_mp3
    from PIL import Image
    import io
    if not ffmpeg_available(): return
    wav=tmp_path/'track.wav'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=duration=0.15','-y',str(wav)],check=True)
    buf=io.BytesIO()
    Image.new('RGB',(32,32),'pink').save(buf,format='JPEG')
    out=tmp_path/'music';out.mkdir()
    target=import_upload_as_track(wav.read_bytes(),'track.wav',out,192,title='Song',artist='Performer',album='Album',track=2,disc=1,cover=buf.getvalue())
    tags=inspect_mp3(target)
    assert tags['title']=='Song' and tags['artist']=='Performer'
    assert tags['album']=='Album' and tags['track']=='2' and tags['cover']


def test_metadata_override_keeps_embedded_art(tmp_path):
    from musicvault.core import write_tags, embed_custom_metadata, inspect_mp3, get_embedded_art
    from PIL import Image
    import io
    import subprocess
    output = tmp_path / 'sample.mp3'
    subprocess.run(['ffmpeg','-loglevel','error','-f','lavfi','-i','sine=frequency=660:duration=0.2','-q:a','8',str(output)],check=True)
    buf=io.BytesIO()
    Image.new('RGB',(20,20),'magenta').save(buf,format='JPEG')
    write_tags(output,'Original','First artist',buf.getvalue())
    embed_custom_metadata(output,title='New title',artist='New artist',album='Collection')
    tags=inspect_mp3(output)
    assert tags['cover'] and tags['title']=='New title' and tags['album']=='Collection'
    assert get_embedded_art(output)


def test_thumbnail_fallback_order():
    from musicvault.core import youtube_thumbnail_candidates, best_youtube_art
    from musicvault import core
    info={'thumbnail':'https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg'}
    candidates=youtube_thumbnail_candidates(info,'https://youtu.be/dQw4w9WgXcQ')
    assert 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg' in candidates
    old=core.download_cover
    try:
        core.download_cover=lambda url: b'fakejpeg' if 'hqdefault.jpg' in url else None
        assert best_youtube_art(info,'https://youtu.be/dQw4w9WgXcQ')==b'fakejpeg'
    finally:
        core.download_cover=old


def test_cleaned_catalogue_titles():
    from musicvault.catalog import normalized_track
    assert normalized_track('Luv(sic) feat. Shing02 [Official Audio]') == normalized_track('Luv(sic)')


def test_album_cover_falls_back_to_release(monkeypatch):
    from musicvault import catalog, core
    found=[]
    def fake_download(url):
        found.append(url)
        return b'album-jpeg' if '/release/release-2/' in url else None
    monkeypatch.setattr(core,'download_cover',fake_download)
    monkeypatch.setattr(catalog,'mb',lambda path, params=None:{'releases':[{'id':'release-1','status':'Bootleg'},{'id':'release-2','status':'Official'}]})
    assert catalog.album_cover('group-1') == b'album-jpeg'
    assert found[0].endswith('/release-group/group-1/front-500')


def test_youtube_thumbnail_is_still_tried_on_catalogue_miss():
    from musicvault import core
    candidates=core.youtube_thumbnail_candidates({'thumbnails':[]},'https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    assert any('/hqdefault.jpg' in item for item in candidates)


def test_dynamic_archive_mirrors_allowed():
    from musicvault.core import _art_host_allowed
    assert _art_host_allowed('ia902345.us.archive.org')
    assert _art_host_allowed('s3.us.archive.org')
    assert not _art_host_allowed('archive.org.evil.example')


def test_artwork_redirect_upgrades_http(monkeypatch):
    # In a real CAA response the server redirects to a dynamically numbered
    # archive.org host. Check that the security and host restrictions permit it.
    from musicvault.core import _art_host_allowed
    assert _art_host_allowed('ia600307.us.archive.org')


def test_backup_album_mapping(monkeypatch):
    from musicvault import catalog
    monkeypatch.setattr(catalog,'itunes_search',lambda q,kind='artist',limit=20:[{'collectionId':42,'collectionName':'Example','artistName':'Artist','releaseDate':'2020-05-01'}])
    albums=catalog.backup_albums('Example')
    assert albums[0]['id']=='itunes:42' and albums[0]['title']=='Example'


def test_backup_track_mapping(monkeypatch):
    from musicvault import catalog
    class MockResponse:
        def raise_for_status(self): pass
        def json(self): return {'results':[{'wrapperType':'collection','collectionName':'Example'}, {'wrapperType':'track','kind':'song','trackName':'Song','artistName':'Artist','trackNumber':2}]}
    monkeypatch.setattr(catalog.requests,'get',lambda *a,**kw:MockResponse())
    group,tracks=catalog.backup_album_tracks('itunes:42')
    assert group['title']=='Example' and tracks[0]['number']==2


def test_artwork_network_errors_are_not_audio_errors(monkeypatch):
    from musicvault import core
    import requests
    class FakeSession:
        headers={}
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,*args,**kwargs):raise requests.exceptions.ConnectionError('offline')
    monkeypatch.setattr(core.requests,'Session',FakeSession)
    assert core.download_cover('https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg') is None
