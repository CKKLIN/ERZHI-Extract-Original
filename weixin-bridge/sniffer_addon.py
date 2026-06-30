"""
mitmproxy addon — 拦截视频号流量并写入 SQLite。

通过 mitmdump 加载:
    mitmdump -s sniffer_addon.py --listen-host 127.0.0.1 --listen-port 8899 --ssl-insecure
"""

import json
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "captured.db"

# 只匹配这些域名
TRUSTED_VIDEO_DOMAINS = [
    r'finder\.video\.qq\.com',
    r'sns\.video\.qq\.com',
    r'wxapp\.tc\.qq\.com',
    r'vweixinf\.tc\.qq\.com',
    r'szdownload\.weixin\.qq\.com',
]

# 明确排除
SKIP_DOMAINS = [
    r'edge\.microsoft\.com',
    r'mobile\.events\.data\.microsoft',
    r'events\.data\.microsoft',
    r'githubcopilot\.com',
    r'google\.com',
    r'googleapis\.com',
    r'gstatic\.com',
    r'cloudmessaging\.edge\.microsoft',
]

STATIC_EXTS = re.compile(
    r'\.(js|css|svg|png|jpg|jpeg|webp|ico|woff2?|gif|bmp|ttf|eot|json|xml|html?)(\?|$)', re.I
)


def is_video_cdn(url: str) -> bool:
    """只接受已知视频 CDN 域名"""
    if not url or not url.startswith("http"):
        return False
    lower = url.lower()
    for d in SKIP_DOMAINS:
        if re.search(d, lower):
            return False
    for d in TRUSTED_VIDEO_DOMAINS:
        if re.search(d, lower):
            return True
    return False


def has_video_content_type(ct: str) -> bool:
    """响应 Content-Type 是否为视频/音频"""
    video_types = ("video/", "audio/", "application/vnd.apple.mpegurl")
    return any(t in ct for t in video_types)


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS captured_videos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url  TEXT,
            video_url   TEXT NOT NULL,
            title       TEXT DEFAULT '',
            poster      TEXT DEFAULT '',
            duration    REAL DEFAULT 0,
            width       INTEGER DEFAULT 0,
            height      INTEGER DEFAULT 0,
            bitrate     INTEGER DEFAULT 0,
            author_name TEXT DEFAULT '',
            raw_headers TEXT DEFAULT '{}',
            captured_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


def save_video(video_url, source_url="", bitrate=0, raw_headers=None):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            INSERT INTO captured_videos (source_url, video_url, bitrate, raw_headers)
            VALUES (?, ?, ?, ?)
        """, (source_url, video_url, bitrate, json.dumps(raw_headers or {})))
        conn.commit()
        conn.close()
    except Exception:
        pass


class VideoSnifferAddon:
    """mitmproxy addon: 只捕获视频号 CDN 的 video/audio 响应"""

    def __init__(self):
        self.captured_count = 0
        init_db()
        print("[SNIFFER] Addon ready (strict mode — finder.video.qq.com only)")

    def request(self, flow):
        url = flow.request.pretty_url
        if is_video_cdn(url):
            print(f"[SNIFFER] REQ: {url[:200]}")

    def response(self, flow):
        url = flow.request.pretty_url

        # 只处理视频 CDN 域名
        if not is_video_cdn(url):
            return

        ct = flow.response.headers.get("content-type", "").lower()
        length = flow.response.headers.get("content-length", "?")
        print(f"[SNIFFER] RES [{ct}] len={length} {url[:200]}")

        # 必须有视频/音频 Content-Type，或者 .mp4/.m3u8 扩展名
        if not (has_video_content_type(ct) or ".mp4" in url.lower() or ".m3u8" in url.lower()):
            return

        # 排除静态资源
        if STATIC_EXTS.search(url.lower()):
            return

        self.captured_count += 1
        source_url = flow.request.headers.get("referer", "")
        raw_headers = dict(flow.response.headers)

        bitrate = 0
        m = re.search(r'[?&]br=(\d+)', url)
        if m:
            bitrate = int(m.group(1))

        save_video(
            video_url=url,
            source_url=source_url,
            bitrate=bitrate,
            raw_headers=raw_headers,
        )

        print(f"[SNIFFER] CAPTURED #{self.captured_count}: {url[:200]}")


addons = [VideoSnifferAddon()]
