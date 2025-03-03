import random

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    lowercase_escape,
    traverse_obj,
)


class ImliveIE(InfoExtractor):
    _VALID_URL = r'https?://imlive\.com/live-sex-chats/(?P<type>[^/?#]+)/video-chats/(?P<id>[^/?#]+)'
    _QUALITYS = {
        'ld': '/live-360.m3u8',
        'sd': '/live-480.m3u8',
        'hd': '/live-720.m3u8',
        'fhd': '/live-fhd.m3u8',
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, headers=self.geo_verification_headers())
        data = self._search_json(
            r'<script\b[^>]*>\s*var videoChatSettings\s*=',
            webpage, 'data', video_id, transform_source=lowercase_escape)
        formats = []
        if traverse_obj(data, ('host', 'webrtcdata', 'streamid')):
            m3u8_url = (
                'https://streamerpnx.wlmediahub.com/video/imlive.com/' + 
                traverse_obj(data, ('host', 'webrtcdata', 'streamid')) +
                self._QUALITYS.get(traverse_obj(data, ('host', 'webrtcdata', 'quality')), '/live.m3u8')
            )
            formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', m3u8_id='hls', fatal=False, live=True)

        else:
            if data['host'].get('workingServer') and data['host'].get('id') and data['host'].get('name'):
                working_server = data['host']['workingServer']
                server_parts = working_server.split(".")
                last_part = server_parts[-1].replace("fly", "")
                formats.append({
                    'url': f"https://streamer{last_part}.wlmediahub.com/flc/{data['host']['id']}/playlist.mp4?anticash={random.random()}",
                    'format_id': 'html5',
                    'ext': 'mp4',
                    'quality': 1,
                })
            else:
                raise ExtractorError('Unable to extract video information', expected=True)

        return {
            'id': video_id,
            'title': video_id,
            'description': traverse_obj(data, ('host', 'aboutme')),
            'is_live': True,
            'formats': formats,
            'age_limit': 18,
        }