import json
from urllib.parse import urlparse

from .common import InfoExtractor
from ..utils import determine_ext, traverse_obj, unescapeHTML, update_url_query

class StreamingCommunityIE(InfoExtractor):
    #_VALID_URL = r'https?://(?:www\.)?streamingcommunityz\.[a-z]{3}/[a-zA-Z]{2}/watch/(?P<id>[0-9]+)(?:\?(.*))?'
    _VALID_URL = r'https?://(?:www\.)?streamingcommunityz\.[a-z]+/[a-zA-Z]{2}/watch/(?P<id>[0-9]+)(?:\?(.*))?'
    _TESTS = [{
        'url': 'https://streamingcommunityz.ltd/it/watch/645',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '645',
            'ext': 'mp4',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        try:
            title = self._html_search_regex(r'(?s)<title inertia>(.+?)</title>', webpage, 'title')
        except Exception:
            title = None
        datapage = json.loads(self._search_regex(r'<div id="app"[^>]* data-page=(.+?)"', webpage, 'datapage').replace("&quot;", '"')[1:])
        if datapage["props"].get("episode",None) is not None or title is None:
            #title = title.split("Watch ")[1].split(" - StreamingCommunity")[0] + " - " + datapage["props"]["episode"].get("name", title)
            title = datapage["props"]["title"]["name"]
        description = datapage["props"]["title"].get("plot", "")
        embed_url = unescapeHTML(datapage["props"]["embedUrl"])
        webpage_iframe = self._download_webpage(
            embed_url, video_id, headers={'Referer': url})
        iframe_url = unescapeHTML(
            self._html_search_regex(r'<iframe[^>]+src="([^"]+)"', webpage_iframe, 'iframe url'))

        webpage_iframe_final = self._download_webpage(
            iframe_url, video_id, headers={'Referer': embed_url})
        token = self._search_regex(r"'token':\s*'([^']+)'", webpage_iframe_final, 'token')
        expiration = self._search_regex(r"'expires':\s*'([^']+)'", webpage_iframe_final, 'expiration')
        asn = self._search_regex(r"'asn':\s*'([^']*)'", webpage_iframe_final, 'asn', default='')
        source_url = unescapeHTML(self._search_regex(r"url:\s*'([^']+)'", webpage_iframe_final, 'source_url'))

        streams = self._parse_json(
            self._search_regex(r'window\.streams\s*=\s*(\[.+?\]);', webpage_iframe_final, 'streams', default='[]'),
            video_id, fatal=False) or []
        source_url = unescapeHTML(
            traverse_obj(streams, (lambda _, v: v.get('active') and v.get('url')), get_all=False).get("url") or source_url).replace('\\/', '/')
        source_url_backup = source_url
        source_url = update_url_query(source_url_backup, {
            'token': token,
            'expires': expiration,
            #'asn': asn,
            'scz': '1',
            "lang": "it",
            "h": "1",
        })

        iframe_origin = f'{urlparse(iframe_url).scheme}://{urlparse(iframe_url).netloc}'
        hls_headers = {
            'Referer': iframe_url,
            'Origin': iframe_origin,
        }

        try:
            formats, subs = self._extract_m3u8_formats_and_subtitles(
                source_url,
                video_id,
                ext='mp4',
                entry_protocol='m3u8_native',
                m3u8_id='hls',
                headers=hls_headers,
                fatal=False,
                live=False
            )
            if formats == []:
                raise Exception("No formats found")
        except Exception as e:
            self.to_screen(f'Error extracting formats with source_url: {source_url}, error: {e}')
            self.to_screen('Attempting to extract formats with alternative method ...')
            source_url = update_url_query(source_url_backup, {
                'token': token,
                'expires': expiration,
                #'asn': asn,
                'scz': '1',
                "lang": "it",
                #"h": "1",
            })

            formats, subs = self._extract_m3u8_formats_and_subtitles(
                source_url,
                video_id,
                ext='mp4',
                entry_protocol='m3u8_native',
                m3u8_id='hls',
                headers=hls_headers,
                fatal=False,
                live=False
            )

        hls_headers["Referer"] = hls_headers["Origin"]+"/"

        for fmt in formats:
            fmt['http_headers'] = hls_headers

        for lang_subs in subs.values():
            for sub in lang_subs:
                # Some subtitle playlists are served without a useful extension.
                # Mark them as HLS WebVTT to avoid ffmpeg embedding failures.
                sub_ext = (sub.get('ext') or determine_ext(sub.get('url')) or '').lower()
                if sub_ext in ('m3u8', 'unknown_video'):
                    sub['ext'] = 'vtt'
                    sub['protocol'] = 'm3u8_native'
                sub.setdefault('http_headers', hls_headers)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            "formats": formats,
            "subtitles": subs
        }