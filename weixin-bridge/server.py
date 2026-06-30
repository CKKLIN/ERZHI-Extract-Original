"""
WeixinProxyBridge — 视频号 MITM 代理桥接服务

功能:
  1. 运行本地 HTTPS MITM 代理 (mitmproxy)，捕获微信 PC 客户端的视频流量
  2. 提供 REST API，供 Java 后端查询/触发视频解析
  3. SQLite 存储捕获记录，支持按 URL 匹配

用法:
  pip install -r requirements.txt
  python server.py

API:
  POST /api/parse       — 提交视频号链接，等待代理捕获到对应视频后返回
  GET  /api/health      — 健康检查
  GET  /api/videos      — 列出最近捕获的视频
  GET  /api/proxy/status — 代理运行状态
"""

import json
import os
import re
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from flask import Flask, request, jsonify
from waitress import serve as waitress_serve

# ============================================================================
# SQLite 存储
# ============================================================================

DB_PATH = Path(__file__).parent / "captured.db"


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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_tasks (
            task_id     TEXT PRIMARY KEY,
            source_url  TEXT NOT NULL,
            status      TEXT DEFAULT 'pending',
            result      TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            resolved_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_captured(video_url, source_url="", title="", poster="",
                  duration=0, width=0, height=0, bitrate=0,
                  author_name="", raw_headers=None):
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        INSERT INTO captured_videos (source_url, video_url, title, poster,
            duration, width, height, bitrate, author_name, raw_headers)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (source_url, video_url, title, poster, duration, width, height,
          bitrate, author_name, json.dumps(raw_headers or {})))
    conn.commit()
    conn.close()


def _is_valid_video_url(url):
    """检查 URL 是否是有效的视频号 CDN 视频地址"""
    if not url:
        return False
    lower = url.lower()
    # 必须是受信任的视频 CDN 域名
    if not re.search(r'finder\.video\.qq\.com|sns\.video\.qq\.com|wxapp\.tc\.qq\.com|vweixinf\.tc\.qq\.com|szdownload\.weixin\.qq\.com', lower):
        return False
    # 排除静态资源扩展名
    static_exts = ('.ico', '.png', '.jpg', '.jpeg', '.svg', '.js', '.css', '.json', '.xml', '.html', '.woff', '.woff2', '.ttf', '.eot', '.gif', '.bmp', '.webp')
    path = lower.split('?')[0]
    if any(path.endswith(ext) for ext in static_exts):
        return False
    return True


def get_recent_videos(limit=50, filter_cdn=True):
    """获取最近捕获的视频。filter_cdn=True 时只返回视频号 CDN 的视频。"""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT * FROM captured_videos ORDER BY id DESC LIMIT ?", (limit * 3,)
    ).fetchall()
    conn.close()

    if not filter_cdn:
        return rows[:limit]

    filtered = [row for row in rows if _is_valid_video_url(row[2])]
    return filtered[:limit]


def find_video_by_source(source_url, within_seconds=120):
    """根据来源 URL 查找最近捕获的匹配视频。

    匹配策略（按优先级）：
    1. 精确匹配 source_url
    2. 提取 feedId/shortCode 模糊匹配
    3. 返回时间窗口内最新的视频（兜底）
    """
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT * FROM captured_videos ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()

    feed_id = _extract_feed_id(source_url)
    short_code = _extract_short_code(source_url)

    cutoff = datetime.now().timestamp() - within_seconds

    # 第一轮：精确/模糊匹配（只匹配有效视频 URL）
    for row in rows:
        if not _is_valid_video_url(row[2]):
            continue
        try:
            captured_at = datetime.strptime(row[11], "%Y-%m-%d %H:%M:%S").timestamp()
        except (ValueError, IndexError):
            captured_at = 0
        if captured_at < cutoff:
            continue

        row_source = row[1] or ""
        # 精确匹配
        if row_source == source_url:
            return row
        # feedId 匹配
        if feed_id and feed_id in row_source:
            return row
        # shortCode 匹配
        if short_code and short_code in row_source:
            return row

    # 第二轮：窗口内最新有效视频（兜底）
    for row in rows:
        if not _is_valid_video_url(row[2]):
            continue
        try:
            captured_at = datetime.strptime(row[11], "%Y-%m-%d %H:%M:%S").timestamp()
        except (ValueError, IndexError):
            captured_at = 0
        if captured_at >= cutoff:
            return row

    return None


def _extract_short_code(url):
    """从短链接中提取 short code，如 weixin.qq.com/sph/AwsX4oHSu3 -> AwsX4oHSu3"""
    if not url:
        return None
    m = re.search(r'/sph/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/s/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    return None


def _extract_feed_id(url):
    """从视频号 URL 中提取 feedId"""
    if not url:
        return None
    # patterns: feed/xxx, feedId=xxx, id=xxx, objectId=xxx
    m = re.search(r'(?:feed/|feedId=|feedid=|objectId=|id=)([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else None


# ============================================================================
# 视频 URL 分类与过滤
# ============================================================================

# 视频号 CDN 域名特征
VIDEO_CDN_PATTERNS = [
    r'finder\.video\.qq\.com',
    r'sns\.video\.qq\.com',
    r'wxapp\.tc\.qq\.com',
    r'vweixinf\.tc\.qq\.com',
    r'szdownload\.weixin\.qq\.com',
    r'sns\.qzone\.qq\.com',
]

# 排除的静态资源
STATIC_EXTENSIONS = re.compile(
    r'\.(js|css|svg|png|jpg|jpeg|webp|ico|woff2?|gif|bmp|ttf|eot)(\?|$)', re.I
)


def is_video_url(url):
    """判断 URL 是否是视频文件"""
    if not url or not url.startswith("http"):
        return False
    lower = url.lower()

    # 排除静态资源（除非含 video/media 关键字）
    if STATIC_EXTENSIONS.search(lower):
        if not any(k in lower for k in ("video", "mp4", "m3u8", "media")):
            return False

    # 排除图片（picformat 是微信图片参数）
    if any(k in lower for k in ("picformat=", "wxampicformat=", "thumb_url", "cover_url")):
        return False

    # 匹配 CDN 域名 + 视频路径
    if any(re.search(p, lower) for p in VIDEO_CDN_PATTERNS):
        return True

    # 通用 mp4 / m3u8
    if ".mp4" in lower or "m3u8" in lower or "video" in lower:
        return True

    return False


def classify_video_url(url):
    """分类: combined(完整视频) / video(纯画面) / audio(纯音频)"""
    if not url:
        return None
    lower = url.lower()
    if any(k in lower for k in ("media-audio", "/audio/")) or (
            "audio" in lower and "track" in lower):
        return "audio"
    if any(k in lower for k in ("media-video",)) or (
            "video" in lower and "track" in lower):
        return "video"
    return "combined"


def extract_bitrate(url):
    """从 URL 中提取码率信息"""
    m = re.search(r'[?&]br=(\d+)', url)
    if m:
        return int(m.group(1))
    # 从分辨率推断
    m = re.search(r'[^a-zA-Z](\d{3,4})p?[^a-zA-Z]', url)
    if m:
        res = int(m.group(1))
        if 360 <= res <= 4320:
            return res * 10
    return 0


# ============================================================================
# mitmproxy 插件 — 拦截视频流量
# ============================================================================

class VideoSniffer:
    """mitmproxy addon: 拦截视频号流量并存入 SQLite"""

    def __init__(self):
        self.captured_count = 0

    def request(self, flow):
        url = flow.request.pretty_url
        if is_video_url(url):
            print(f"[SNIFFER] 捕获视频请求: {url[:120]}")

    def response(self, flow):
        url = flow.request.pretty_url
        if not is_video_url(url):
            return

        content_type = flow.response.headers.get("content-type", "")
        # 只记录视频/音频内容（或来自视频 CDN 的响应）
        is_media = any(t in content_type for t in ("video/", "audio/", "application/octet-stream",
                                                    "application/vnd.apple.mpegurl"))
        is_cdn = any(re.search(p, url) for p in VIDEO_CDN_PATTERNS)

        if not (is_media or is_cdn):
            return

        self.captured_count += 1

        # 提取 metadata
        raw_headers = dict(flow.response.headers)

        # 尝试从 referer/请求中提取源 URL
        source_url = flow.request.headers.get("referer", "")
        title = ""
        poster = ""

        # 如果请求 body 或响应中包含 JSON metadata
        try:
            ct = flow.request.headers.get("content-type", "")
            if "json" in ct and flow.request.content:
                body = json.loads(flow.request.content.decode("utf-8", errors="ignore"))
                if isinstance(body, dict):
                    title = body.get("title", body.get("object_desc", ""))
        except Exception:
            pass

        duration = 0
        width = 0
        height = 0
        bitrate = extract_bitrate(url)

        # 从 content-length 估算文件大小
        cl = flow.response.headers.get("content-length", "")
        if cl and cl.isdigit():
            pass  # 可用于后续过滤

        save_captured(
            video_url=url,
            source_url=source_url,
            title=title,
            poster=poster,
            duration=duration,
            width=width,
            height=height,
            bitrate=bitrate,
            raw_headers=raw_headers,
        )

        print(f"[SNIFFER] 捕获 #{self.captured_count}: {url[:150]}")


# ============================================================================
# Proxy 管理器（在独立线程中运行 mitmproxy）
# ============================================================================

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8899

_proxy_thread = None
_proxy_running = False
_sniffer: VideoSniffer | None = None


def start_proxy():
    """启动 mitmdump 子进程（兼容 mitmproxy 各版本）"""
    global _proxy_thread, _proxy_running, _sniffer

    if _proxy_running:
        return True

    _sniffer = VideoSniffer()

    try:
        import subprocess
        import shutil

        addon_path = str(Path(__file__).parent / "sniffer_addon.py")

        def _run():
            global _proxy_running

            # 方式1: python -m mitmdump (venv)
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "mitmdump", "--version"],
                    capture_output=True, timeout=5)
                if result.returncode == 0:
                    _proxy_running = True
                    cmd = [sys.executable, "-m", "mitmdump",
                           "-s", addon_path,
                           "--listen-host", PROXY_HOST,
                           "--listen-port", str(PROXY_PORT),
                           "--ssl-insecure",
                           "--set", "block_global=false"]
                    print(f"[PROXY] Using: python -m mitmdump")
                    print(f"[PROXY] mitmdump starting on {PROXY_HOST}:{PROXY_PORT}")
                    print(f"[PROXY] Addon: {addon_path}")
                    subprocess.run(cmd, check=False)
                    return
            except Exception:
                pass

            # 方式2: standalone mitmdump (PATH)
            if shutil.which("mitmdump"):
                _proxy_running = True
                cmd = ["mitmdump", "-s", addon_path,
                       "--listen-host", PROXY_HOST,
                       "--listen-port", str(PROXY_PORT),
                       "--ssl-insecure",
                       "--set", "block_global=false"]
                print(f"[PROXY] Using: mitmdump (PATH)")
                print(f"[PROXY] mitmdump starting on {PROXY_HOST}:{PROXY_PORT}")
                subprocess.run(cmd, check=False)
                return

            _proxy_running = False
            print("[PROXY] mitmdump not found.")
            print("[PROXY] Ensure mitmproxy is installed: pip install mitmproxy")

        _proxy_thread = threading.Thread(target=_run, daemon=True)
        _proxy_thread.start()
        time.sleep(1.5)

        return True

    except Exception as e:
        print(f"[PROXY] 启动失败: {e}")
        return False


def stop_proxy():
    global _proxy_running
    _proxy_running = False
    # mitmproxy master 会随进程退出而停止


def get_proxy_status():
    conn = sqlite3.connect(str(DB_PATH))
    count = conn.execute("SELECT COUNT(*) FROM captured_videos").fetchone()[0]
    conn.close()
    return {
        "running": _proxy_running,
        "host": PROXY_HOST,
        "port": PROXY_PORT,
        "captured_count": count,
    }


# ============================================================================
# Flask API
# ============================================================================

app = Flask(__name__)

# 存储待处理任务
_pending_tasks: dict = {}  # task_id -> {url, status, result, event}


@app.route("/api/health", methods=["GET"])
def health():
    proxy_status = get_proxy_status()
    return jsonify({
        "status": "ok",
        "service": "WeixinProxyBridge",
        "version": "1.0.0",
        "proxy": proxy_status,
    })


@app.route("/api/proxy/status", methods=["GET"])
def proxy_status():
    return jsonify(get_proxy_status())


@app.route("/api/proxy/start", methods=["POST"])
def api_start_proxy():
    ok = start_proxy()
    return jsonify({"success": ok, "proxy": get_proxy_status()})


@app.route("/api/proxy/stop", methods=["POST"])
def api_stop_proxy():
    stop_proxy()
    return jsonify({"success": True})


@app.route("/api/videos", methods=["GET"])
def list_videos():
    limit = request.args.get("limit", 50, type=int)
    rows = get_recent_videos(limit)
    videos = []
    for row in rows:
        videos.append({
            "id": row[0],
            "sourceUrl": row[1],
            "videoUrl": row[2],
            "title": row[3],
            "poster": row[4],
            "duration": row[5],
            "width": row[6],
            "height": row[7],
            "bitrate": row[8],
            "authorName": row[9],
            "capturedAt": row[11],
        })
    return jsonify({"videos": videos, "count": len(videos)})


@app.route("/api/parse", methods=["POST"])
def parse_video():
    """
    提交视频号链接，等待代理捕获到对应视频后返回。
    解析成功后自动下载解密视频并存到本地 static/ 目录，返回本地播放链接。
    """
    data = request.get_json(silent=True) or {}
    source_url = data.get("url", "").strip()

    if not source_url:
        return jsonify({"success": False, "error": "缺少 url 参数"}), 400

    wait_seconds = min(data.get("waitSeconds", 60), 120)

    # 1. 先查是否已捕获
    existing = find_video_by_source(source_url, within_seconds=120)
    if not existing:
        # 轮询等待
        print(f"[API] 解析请求: {source_url[:80]}... (等待 {wait_seconds}s)")
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            time.sleep(1.5)
            existing = find_video_by_source(source_url, within_seconds=wait_seconds + 30)
            if existing:
                break
        else:
            # 兜底：返回最近视频
            recent = get_recent_videos(1)
            if recent:
                existing = recent[0]

    if not existing:
        return jsonify({
            "success": False,
            "error": "解析超时。请在微信 PC 客户端中播放该视频后重试。"
        }), 504

    row = existing
    video_id = row[0]
    cdn_url = row[2]
    source = "cache"

    # 2. 下载 + 解密 → static/
    static_dir = Path(__file__).parent / "static" / "videos"
    static_dir.mkdir(parents=True, exist_ok=True)
    local_path = static_dir / f"{video_id}.mp4"
    local_url = f"http://127.0.0.1:9600/static/videos/{video_id}.mp4"

    # 即使文件已存在，也检查是否有效 MP4
    need_download = True
    if local_path.exists():
        size = local_path.stat().st_size
        if size > 10000:  # 至少 10KB
            with open(local_path, 'rb') as f:
                header = f.read(16)
            if len(header) > 12 and header[4:8] == b'ftyp':
                print(f"[API] Reusing valid cached MP4: {local_path} ({size} bytes)")
                need_download = False
            else:
                print(f"[API] Cached file invalid (header={header.hex()}), re-downloading...")
        else:
            print(f"[API] Cached file too small ({size} bytes), re-downloading...")

    if need_download:
        print(f"[API] Downloading + decrypting video #{video_id}...")
        try:
            _download_and_decrypt(cdn_url, str(local_path))
            size = local_path.stat().st_size
            print(f"[API] Saved: {local_path} ({size} bytes)")
        except Exception as e:
            print(f"[API] Decrypt failed: {e}")
            return jsonify({
                "success": False,
                "error": f"视频下载解密失败: {str(e)[:100]}",
            }), 502
    else:
        print(f"[API] Using cached decrypted video: {local_path}")

    return jsonify({
        "success": True,
        "data": _row_to_response(row, local_url),
        "source": source,
    })


def _download_and_decrypt(cdn_url, output_path):
    """下载视频（尝试解密），保存为 MP4"""
    import requests as req
    import urllib.parse

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://channels.weixin.qq.com/",
        "Origin": "https://channels.weixin.qq.com",
    }
    # 绕过系统代理，直接连接 CDN
    resp = req.get(cdn_url, headers=headers, timeout=120,
                   proxies={"http": None, "https": None})
    resp.raise_for_status()
    data = resp.content
    print(f"[decrypt] Downloaded {len(data)} bytes, first 16 bytes: {data[:16].hex()}")

    # 已解密则直接保存
    if len(data) > 12 and data[4:8] == b'ftyp':
        print(f"[decrypt] Already valid MP4, saving directly")
        Path(output_path).write_bytes(data)
        return

    # 尝试解密 — 多种方式
    m = re.search(r'encfilekey=([^&]+)', cdn_url)
    encfilekey = urllib.parse.unquote(m.group(1)) if m else ""

    if not encfilekey:
        print(f"[decrypt] No encfilekey, saving raw data")
        Path(output_path).write_bytes(data)
        return

    # 尝试多种 XOR 密钥推导方式
    import hashlib
    methods = [
        ("md5(encfilekey)", hashlib.md5(encfilekey.encode()).digest()),
        ("md5(WXVideo+key)", hashlib.md5(b"WXVideo" + encfilekey.encode()).digest()),
        ("md5(key+finder)", hashlib.md5(encfilekey.encode() + b"_finder_video").digest()),
        ("md5(key only)", hashlib.md5(encfilekey.encode()[:16]).digest()),
    ]

    for method_name, key in methods:
        for skip in (0, 32):
            decrypted = bytearray(len(data))
            decrypted[:skip] = data[:skip]
            for i in range(skip, len(data)):
                decrypted[i] = data[i] ^ key[(i - skip) % len(key)]
            result = bytes(decrypted)
            if len(result) > 12 and result[4:8] == b'ftyp':
                print(f"[decrypt] SUCCESS with {method_name}, skip={skip}")
                Path(output_path).write_bytes(result)
                return
            # Check header at offset 0 (no skip)
            if skip == 0 and result[:4] == b'\x00\x00\x00':
                # Might be MP4 with zero-padded size
                size = int.from_bytes(result[:4], 'big')
                if 0 < size < len(result) + 1000 and len(result) > 100000:
                    print(f"[decrypt] Possible MP4 with {method_name}, size hint={size}")

    # 全部失败 → 保存原始数据
    print(f"[decrypt] All methods failed, saving raw data ({len(data)} bytes)")
    Path(output_path).write_bytes(data)


def _row_to_response(row, local_url=None):
    """将 SQLite 行转换为前端需要的 VideoInfoResponse 格式"""
    video_url = local_url or row[2]
    return {
        "title": row[3] or "未知标题",
        "url": row[1] or "",
        "poster": row[4] or "",
        "duration": row[5] or 0,
        "width": row[6] or 0,
        "height": row[7] or 0,
        "platform": "weixin",
        "postType": "video",
        "author": {
            "name": row[9] or "",
            "avatar": "",
        } if row[9] else None,
        "downloadLinks": {
            "combined": {
                "url": video_url,
                "type": "combined",
                "quality": _format_bitrate(row[8]),
            } if video_url else None,
        },
    }


def _format_bitrate(br):
    if br >= 1000000:
        return f"{br / 1000000:.1f} Mbps"
    if br >= 1000:
        return f"{br / 1000:.1f} Kbps"
    if br > 0:
        return f"{br} bps"
    return None


# ============================================================================
# 启动入口
# ============================================================================

def main():
    print("=" * 60)
    print("  WeixinProxyBridge — 视频号解析桥接服务")
    print("=" * 60)

    # 初始化数据库
    init_db()
    print(f"[INIT] 数据库已初始化: {DB_PATH}")

    # 启动 mitmproxy
    ok = start_proxy()
    if ok:
        print(f"[INIT] MITM 代理已启动: {PROXY_HOST}:{PROXY_PORT}")
        print(f"[INIT] 请确保:")
        print(f"       1. Windows 系统代理 → {PROXY_HOST}:{PROXY_PORT}")
        print(f"       2. 已安装并信任 mitmproxy 的 CA 证书")
        print(f"       3. CA 证书位置: %USERPROFILE%\\.mitmproxy\\mitmproxy-ca-cert.cer")
    else:
        print("[INIT] ⚠️  MITM 代理启动失败，请检查端口是否被占用")
        print(f"[INIT]    检查: netstat -ano | findstr {PROXY_PORT}")

    # 启动 Flask API
    api_port = int(os.environ.get("BRIDGE_PORT", "9600"))
    print(f"[INIT] API 服务启动在: http://0.0.0.0:{api_port}")
    print(f"[INIT] 健康检查: http://127.0.0.1:{api_port}/api/health")
    print("=" * 60)

    # 使用 waitress（生产级 WSGI 服务器，Windows 兼容）
    waitress_serve(app, host="0.0.0.0", port=api_port)


if __name__ == "__main__":
    main()
