import execjs

from .common import InfoExtractor

js_code = """
function unPack(code) {
    function indent(code) {
        var tabs = 0, old=-1, add='';
        for(var i=0; i<code.length; i++) {
            if(code[i].indexOf("{") != -1) tabs++;
            if(code[i].indexOf("}") != -1) tabs--;
            if(old != tabs) {
                old = tabs;
                add = "";
                while (old > 0) {
                    add += "\\t";
                    old--;
                }
                old = tabs;
            }
            code[i] = add + code[i];
        }
        return code;
    }

    var env = {
        eval: function(c) {
            code = c;
        },
        window: {},
        document: {}
    };

    eval("with(env) {" + code + "}");

    code = (code+"").replace(/;/g, ";\\n").replace(/{/g, "\\n{\\n").replace(/}/g, "\\n}\\n").replace(/\\n;\\n/g, ";\\n").replace(/\\n\\n/g, "\\n");
    code = code.split("\\n");
    code = indent(code);
    code = code.join("\\n");
    return code;
}
"""


class FilemoonIE(InfoExtractor):
    _VALID_URL = r"https?://filemoon\.to/e/(?P<id>[a-z0-9-]+)"

    def _real_extract(self, url):
        headers = {
            "referer": "https://filemoon.to/",
            "sec-fetch-dest": "iframe",
        }
        video_id = "1_filemoon"
        webpage = self._download_webpage(url, video_id)
        iframe_url = self._search_regex(
            r'<iframe src="(.*)" frameborder', webpage, "IFRAME URL"
        )
        iframe_webpage = self._download_webpage(iframe_url, video_id, headers=headers)
        some_packed_code = self._html_search_regex(
            r"<script data-cfasync='false' type='text/javascript'>(.+?)\n</script>",
            iframe_webpage,
            "JS CODE",
            fatal=False,
        )
        ctx = execjs.compile(js_code)
        unpacked_code = ctx.call("unPack", some_packed_code)
        m3u8_url = self._search_regex(
            r'file:"(.*)"', unpacked_code, "search m3u8", fatal=False
        )
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, "mp4", m3u8_id="hls", headers={"Referer": url}
        )

        return {
            "id": video_id,
            "formats": formats,
            "http_headers": {"Referer": url},
        }
