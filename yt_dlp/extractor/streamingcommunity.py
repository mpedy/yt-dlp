from .common import InfoExtractor
import json

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
        title = self._html_search_regex(r'<title inertia>(.+?)</title>', webpage, 'title')
        datapage = json.loads(self._search_regex(r'<div id="app"[^>]* data-page=(.+?)"', webpage, 'datapage').replace("&quot;", '"')[1:])
        if datapage["props"].get("episode",None) is not None:
            title = title.split("Watch ")[1].split(" - StreamingCommunity")[0] + " - " + datapage["props"]["episode"].get("name", title)
        description = datapage["props"]["title"].get("plot", "")
        webpage_iframe = self._download_webpage(datapage["props"]["embedUrl"], video_id)
        iframe_url = self._html_search_regex(r'<iframe[^>]+src="([^"]+)"', webpage_iframe, 'iframe url')

        webpage_iframe_final = self._download_webpage(iframe_url, video_id)
        token = self._search_regex(r"'token':\s*'([^']+)'", webpage_iframe_final, 'token')
        expiration = self._search_regex(r"'expires':\s*'([^']+)'", webpage_iframe_final, 'expiration')
        source_url = self._search_regex(r"url:\s*'([^']+)'", webpage_iframe_final, 'source_url')

        formats, subs = self._extract_m3u8_formats_and_subtitles(
            source_url+('?' if '?' not in source_url else '&')+'token='+token+'&expires='+expiration+"&h=1&scz=1", 
            video_id, 
            ext='mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
            fatal=False,
            live=False
        )

        return {
            'id': video_id,
            'title': title,
            'description': description,
            "formats": formats,
            "subtitles": subs
        }