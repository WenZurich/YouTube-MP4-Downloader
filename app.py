import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import traceback
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from curl_cffi import requests as browser_requests
import imageio_ffmpeg
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from PySide6.QtCore import QObject, Qt, QProcess, QTimer, Signal, QSettings, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QFileDialog, QFrame,
    QHeaderView, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy, QSpacerItem, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget
)

APP_NAME = "Video Downloader"
APP_VERSION = "2.6.0"
ORG_NAME = "WenZurich"

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
# Each language is a flat dict of string keys. Adding a new language is just a
# matter of adding another entry here with the same keys.

TRANSLATIONS = {
    "zh_TW": {
        "language_name": "繁體中文",
        "app_title": "影片下載器",
        "subtitle": "貼上任何網址，下載成 MP4",
        "link_section": "影片連結",
        "url_placeholder": "貼上影片網址，支援多數常見影音網站",
        "paste": "貼上並加入",
        "add_queue": "加入佇列",
        "queue": "下載佇列",
        "queue_hint": "可持續加入網址；清單固定捲動，不影響其他設定",
        "queue_count": "{count} 個項目",
        "queue_state_summary": "{pending} 等待 · {active} 下載中 · {done} 完成 · {failed} 失敗",
        "resume_queue": "繼續下載",
        "queue_status": "狀態",
        "queue_item": "項目",
        "queue_progress": "進度",
        "remove_selected": "移除選取",
        "clear_finished": "清除完成",
        "retry_failed": "重試失敗",
        "retrying": "正在自動重試",
        "retrying_detail": "網站回應異常，切換相容模式後再試一次",
        "missav_resolving": "正在解析網站播放器",
        "missav_resolving_detail": "正在取得可用 HLS / m3u8 串流…",
        "missav_ready": "已找到 HLS 串流",
        "missav_ready_detail": "正在以相容模式開始下載",
        "unexpected_error": "發生未預期錯誤；程式已攔截錯誤並保留開啟。詳細資訊已寫入錯誤紀錄。",
        "worker_crashed": "下載工作異常結束，但主程式仍保持開啟。你可以重試此項目。",
        "concurrency": "同時下載",
        "concurrency_1": "1（依序）",
        "concurrency_2": "2",
        "concurrency_3": "3",
        "status_pending": "等待中",
        "status_active": "下載中",
        "status_done": "完成",
        "status_failed": "失敗",
        "status_cancelled": "已停止",
        "start_queue": "開始下載",
        "queue_running": "下載中 {active} · 等待 {pending}",
        "queue_running_detail": "可繼續貼上網址，新項目會自動排入佇列",
        "queue_complete": "佇列完成",
        "queue_complete_detail": "完成 {done} · 失敗 {failed}",
        "queue_stopped": "佇列已停止",
        "queue_stopped_detail": "仍有 {pending} 個項目保留，可再次開始",
        "added_urls": "已加入 {added} 個網址",
        "skipped_duplicates": "略過 {skipped} 個重複網址",
        "warn_no_queue_title": "沒有下載項目",
        "warn_no_queue": "請先加入至少一個網址。",
        "quality": "畫質",
        "output_format": "輸出格式",
        "playlist": "播放清單",
        "playlist_single": "只下載這一部",
        "playlist_all": "下載整個播放清單",
        "save_location": "儲存位置",
        "choose_folder": "選擇資料夾",
        "open_folder": "開啟資料夾",
        "cancel": "取消",
        "download": "下載 MP4",
        "quality_best": "最高畫質",
        "ready": "準備完成",
        "ready_detail": "貼上影片連結後即可開始下載",
        "resolving": "正在解析影片",
        "resolving_detail": "正在取得可用畫質…",
        "downloading": "下載中 {pct:.1f}%",
        "receiving": "正在接收影片資料",
        "eta_seconds": "約 {eta} 秒",
        "processing": "正在處理影片",
        "processing_detail": "合併影音，或將 HLS / m3u8 無損重新封裝為 MP4",
        "playlist_item": "第 {n} 部 · {pct:.1f}%",
        "done": "下載完成",
        "done_dialog_title": "下載完成",
        "done_saved_to": "已儲存到：",
        "failed": "下載失敗",
        "failed_detail": "請查看錯誤訊息後再試一次",
        "cancelling": "正在取消",
        "cancelling_detail": "目前片段完成後會停止",
        "cancelled": "已取消",
        "cancelled_detail": "下載已停止",
        "warn_no_url_title": "缺少網址",
        "warn_no_url": "請先貼上影片網址。",
        "warn_no_folder_title": "缺少資料夾",
        "warn_no_folder": "請先選擇儲存位置。",
        "note": "僅下載你有權保存的內容，並遵守各網站使用條款與著作權規範。",
        "theme": "主題",
        "theme_system": "跟隨系統",
        "theme_light": "淺色",
        "theme_dark": "深色",
        "language": "語言",
        "err_drm": "這個網站的影片有數位版權保護（DRM），無法下載。",
        "err_unsupported": "無法辨識這個網址的影片，或這個網站不支援。",
        "err_private": "這部影片是私人或需要登入才能觀看。",
        "err_generic": "下載時發生問題。",
    },
    "en": {
        "language_name": "English",
        "app_title": "Video Downloader",
        "subtitle": "Paste any link, download as MP4",
        "link_section": "Video link",
        "url_placeholder": "Paste a video URL — supports many common video sites",
        "paste": "Paste & add",
        "add_queue": "Add to queue",
        "queue": "Download queue",
        "queue_hint": "Keep adding links; the queue stays compact and scrollable",
        "queue_count": "{count} items",
        "queue_state_summary": "{pending} waiting · {active} downloading · {done} done · {failed} failed",
        "resume_queue": "Resume downloads",
        "queue_status": "Status",
        "queue_item": "Item",
        "queue_progress": "Progress",
        "remove_selected": "Remove selected",
        "clear_finished": "Clear completed",
        "retry_failed": "Retry failed",
        "retrying": "Retrying automatically",
        "retrying_detail": "The site returned an error; retrying once in compatibility mode",
        "missav_resolving": "Resolving site player",
        "missav_resolving_detail": "Finding an available HLS / m3u8 stream…",
        "missav_ready": "HLS stream found",
        "missav_ready_detail": "Starting in compatibility mode",
        "unexpected_error": "An unexpected error was caught and the app was kept open. Details were written to the error log.",
        "worker_crashed": "The download worker exited unexpectedly, but the main app stayed open. You can retry this item.",
        "concurrency": "Concurrent",
        "concurrency_1": "1 (sequential)",
        "concurrency_2": "2",
        "concurrency_3": "3",
        "status_pending": "Waiting",
        "status_active": "Downloading",
        "status_done": "Done",
        "status_failed": "Failed",
        "status_cancelled": "Stopped",
        "start_queue": "Start downloads",
        "queue_running": "Downloading {active} · {pending} waiting",
        "queue_running_detail": "Keep pasting links; new items join the queue automatically",
        "queue_complete": "Queue complete",
        "queue_complete_detail": "{done} done · {failed} failed",
        "queue_stopped": "Queue stopped",
        "queue_stopped_detail": "{pending} items remain queued; start again to resume",
        "added_urls": "Added {added} links",
        "skipped_duplicates": "Skipped {skipped} duplicate links",
        "warn_no_queue_title": "Nothing to download",
        "warn_no_queue": "Add at least one link to the queue first.",
        "quality": "Quality",
        "output_format": "Format",
        "playlist": "Playlist",
        "playlist_single": "This video only",
        "playlist_all": "Download whole playlist",
        "save_location": "Save to",
        "choose_folder": "Choose folder",
        "open_folder": "Open folder",
        "cancel": "Cancel",
        "download": "Download MP4",
        "quality_best": "Best quality",
        "ready": "Ready",
        "ready_detail": "Paste a video link to start",
        "resolving": "Resolving video",
        "resolving_detail": "Fetching available qualities…",
        "downloading": "Downloading {pct:.1f}%",
        "receiving": "Receiving video data",
        "eta_seconds": "about {eta}s left",
        "processing": "Processing video",
        "processing_detail": "Merging streams or losslessly remuxing HLS / m3u8 to MP4",
        "playlist_item": "Item {n} · {pct:.1f}%",
        "done": "Download complete",
        "done_dialog_title": "Download complete",
        "done_saved_to": "Saved to:",
        "failed": "Download failed",
        "failed_detail": "Check the error and try again",
        "cancelling": "Cancelling",
        "cancelling_detail": "Will stop after the current fragment",
        "cancelled": "Cancelled",
        "cancelled_detail": "Download stopped",
        "warn_no_url_title": "No URL",
        "warn_no_url": "Please paste a video URL first.",
        "warn_no_folder_title": "No folder",
        "warn_no_folder": "Please choose where to save.",
        "note": "Only download content you are authorized to save, and follow each site's terms and copyright law.",
        "theme": "Theme",
        "theme_system": "System",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "language": "Language",
        "err_drm": "This video is DRM-protected and cannot be downloaded.",
        "err_unsupported": "Couldn't read a video from this URL, or the site isn't supported.",
        "err_private": "This video is private or requires sign-in.",
        "err_generic": "Something went wrong during the download.",
    },
}

LANG_ORDER = ["zh_TW", "en"]


class I18n:
    """Tiny translation helper. Call tr(key, **fmt)."""

    def __init__(self, lang="zh_TW"):
        self.lang = lang if lang in TRANSLATIONS else "zh_TW"

    def set_language(self, lang):
        if lang in TRANSLATIONS:
            self.lang = lang

    def tr(self, key, **fmt):
        table = TRANSLATIONS.get(self.lang, TRANSLATIONS["zh_TW"])
        text = table.get(key, TRANSLATIONS["en"].get(key, key))
        if fmt:
            try:
                return text.format(**fmt)
            except (KeyError, IndexError, ValueError):
                return text
        return text


# ---------------------------------------------------------------------------
# Theming
# ---------------------------------------------------------------------------
# Two full palettes. The system option resolves to one of them at runtime.

PALETTES = {
    "light": {
        "bg": "#F6F6F8",
        "surface": "#FFFFFF",
        "surface_2": "#F1F1F5",
        "border": "#E4E4EA",
        "border_strong": "#D5D5DD",
        "text": "#17171A",
        "text_muted": "#6B6B73",
        "text_faint": "#9A9AA2",
        "field": "#FBFBFD",
        "accent": "#4F46E5",
        "accent_hover": "#4338CA",
        "accent_text": "#FFFFFF",
        "secondary": "#ECECF1",
        "secondary_hover": "#E1E1E8",
        "disabled_bg": "#EAEAEF",
        "disabled_text": "#A7A7AF",
        "track": "#E4E4EA",
    },
    "dark": {
        "bg": "#151519",
        "surface": "#1E1E24",
        "surface_2": "#26262E",
        "border": "#2E2E37",
        "border_strong": "#3A3A45",
        "text": "#F2F2F5",
        "text_muted": "#A2A2AD",
        "text_faint": "#71717C",
        "field": "#26262E",
        "accent": "#6366F1",
        "accent_hover": "#7C7EF5",
        "accent_text": "#FFFFFF",
        "secondary": "#2E2E37",
        "secondary_hover": "#383842",
        "disabled_bg": "#26262E",
        "disabled_text": "#5A5A63",
        "track": "#2E2E37",
    },
}


def build_qss(p):
    """Build the full stylesheet string from a palette dict."""
    return f"""
QWidget {{
    background: {p['bg']};
    color: {p['text']};
    font-family: "Segoe UI", "Microsoft JhengHei UI", sans-serif;
    font-size: 14px;
}}
QFrame#Card {{
    background: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 20px;
}}
QLabel#Title {{
    font-size: 27px;
    font-weight: 700;
    color: {p['text']};
}}
QLabel#Subtitle {{
    color: {p['text_muted']};
    font-size: 14px;
}}
QLabel#Muted {{
    color: {p['text_muted']};
}}
QLabel#Faint {{
    color: {p['text_faint']};
    font-size: 12px;
}}
QLabel#Section {{
    font-size: 13px;
    font-weight: 600;
    color: {p['text_muted']};
}}
QLineEdit, QComboBox {{
    background: {p['field']};
    color: {p['text']};
    border: 1px solid {p['border_strong']};
    border-radius: 12px;
    padding: 0 13px;
    min-height: 42px;
    selection-background-color: {p['accent']};
    selection-color: {p['accent_text']};
}}
QLineEdit:focus, QComboBox:focus {{
    border: 2px solid {p['accent']};
    padding: 0 12px;
}}
QLineEdit:read-only {{
    color: {p['text_muted']};
    background: {p['surface_2']};
}}
QComboBox::drop-down {{
    border: none;
    width: 30px;
}}
QComboBox QAbstractItemView {{
    background: {p['surface']};
    color: {p['text']};
    border: 1px solid {p['border_strong']};
    border-radius: 10px;
    padding: 4px;
    outline: none;
    selection-background-color: {p['accent']};
    selection-color: {p['accent_text']};
}}
QTreeWidget {{
    background: {p['field']};
    color: {p['text']};
    border: 1px solid {p['border_strong']};
    border-radius: 12px;
    outline: none;
}}
QTreeWidget::item {{
    min-height: 34px;
    padding: 3px 6px;
    border-bottom: 1px solid {p['border']};
}}
QTreeWidget::item:alternate {{
    background: {p['surface']};
}}
QTreeWidget::item:selected {{
    background: {p['secondary']};
    color: {p['text']};
}}
QTreeWidget QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QTreeWidget QScrollBar::handle:vertical {{
    background: {p['border_strong']};
    border-radius: 5px;
    min-height: 28px;
}}
QTreeWidget QScrollBar::add-line:vertical,
QTreeWidget QScrollBar::sub-line:vertical {{
    height: 0;
}}
QHeaderView::section {{
    background: {p['surface_2']};
    color: {p['text_muted']};
    border: none;
    border-bottom: 1px solid {p['border']};
    padding: 8px 7px;
    font-weight: 600;
}}
QPushButton {{
    border: none;
    border-radius: 12px;
    min-height: 42px;
    padding: 0 18px;
    font-weight: 600;
}}
QPushButton#Primary {{
    color: {p['accent_text']};
    background: {p['accent']};
}}
QPushButton#Primary:hover {{
    background: {p['accent_hover']};
}}
QPushButton#Secondary {{
    color: {p['text']};
    background: {p['secondary']};
}}
QPushButton#Secondary:hover {{
    background: {p['secondary_hover']};
}}
QPushButton#Ghost {{
    color: {p['text']};
    background: transparent;
    border: 1px solid {p['border_strong']};
}}
QPushButton#Ghost:hover {{
    background: {p['surface_2']};
}}
QPushButton:disabled {{
    color: {p['disabled_text']};
    background: {p['disabled_bg']};
    border: none;
}}
QPushButton#Ghost:disabled {{
    background: transparent;
    border: 1px solid {p['border']};
    color: {p['disabled_text']};
}}
QFrame#SettingsPanel {{
    background: {p['surface_2']};
    border: 1px solid {p['border']};
    border-radius: 14px;
}}
QFrame#StatusCard {{
    background: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 12px;
}}
QComboBox#Toolbar {{
    min-height: 34px;
    padding: 0 10px;
    border-radius: 9px;
    background: {p['surface_2']};
    border: 1px solid {p['border']};
}}
QProgressBar {{
    min-height: 8px;
    max-height: 8px;
    border: none;
    border-radius: 4px;
    background: {p['track']};
    text-align: center;
}}
QProgressBar::chunk {{
    border-radius: 4px;
    background: {p['accent']};
}}
"""


def resolve_theme(mode):
    """Map a theme mode ('system'|'light'|'dark') to a concrete palette key."""
    if mode == "light":
        return "light"
    if mode == "dark":
        return "dark"
    # system
    try:
        hints = QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except Exception:
        pass
    return "light"


# ---------------------------------------------------------------------------
# Page metadata / output naming
# ---------------------------------------------------------------------------

class _PageTitleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.og_title = ""
        self.twitter_title = ""
        self.title_parts = []
        self.h1_parts = []
        self._in_title = False
        self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        name = tag.lower()
        attrs = {str(k).lower(): (v or "") for k, v in attrs}
        if name == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            value = attrs.get("content", "").strip()
            if key == "og:title" and value and not self.og_title:
                self.og_title = value
            elif key == "twitter:title" and value and not self.twitter_title:
                self.twitter_title = value
        elif name == "title":
            self._in_title = True
        elif name == "h1":
            self._in_h1 = True

    def handle_endtag(self, tag):
        name = tag.lower()
        if name == "title":
            self._in_title = False
        elif name == "h1":
            self._in_h1 = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if self._in_h1:
            self.h1_parts.append(data)


def _clean_title_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def extract_page_title(html_text):
    parser = _PageTitleParser()
    try:
        parser.feed(html_text or "")
    except Exception:
        return ""
    candidates = (
        parser.og_title,
        parser.twitter_title,
        " ".join(parser.h1_parts),
        " ".join(parser.title_parts),
    )
    for value in candidates:
        cleaned = _clean_title_text(value)
        if cleaned:
            return cleaned
    return ""


def safe_output_title(title, fallback="Video", max_chars=160):
    """Return a readable Windows-safe filename stem without changing the media."""
    title = _clean_title_text(title) or fallback
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", title)
    title = re.sub(r"\s+", " ", title).strip(" .")
    if not title:
        title = fallback

    reserved = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if title.upper() in reserved:
        title = "_" + title

    if len(title) > max_chars:
        title = title[:max_chars].rstrip(" .")
    return title or fallback


# ---------------------------------------------------------------------------
# Site-specific resolvers
# ---------------------------------------------------------------------------

MISSAV_DOMAINS = (
    "missav123.com",
    "missav.ai",
    "missav.ws",
    "missav.live",
)
MISSAV_STREAM_PREFERRED_DOMAINS = ("surrit.com",)
MISSAV_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
MISSAV_PACKER_RE = re.compile(
    r"eval\(\s*function\(p,a,c,k,e,d\).*?\}\(\s*"
    r"(?P<payload>'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")\s*,\s*"
    r"(?P<radix>\d+)\s*,\s*(?P<count>\d+)\s*,\s*"
    r"(?P<keys>'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"
    r"\.split\(\s*['\"]\|['\"]\s*\)",
    re.DOTALL,
)
MISSAV_HLS_RE = re.compile(
    r"https?://[^\s'\"<>\\;]+\.m3u8(?:\?[^\s'\"<>\\;]*)?",
    re.IGNORECASE,
)

AVPLE_DOMAINS = ("avple.tv",)
AVPLE_SOURCE_RE = re.compile(
    r"\bsource\s*=\s*(['\"])(?P<url>.+?)\1",
    re.IGNORECASE | re.DOTALL,
)
AVPLE_JSON_RE = re.compile(
    r"<script[^>]+type=['\"]application/json['\"][^>]*>(?P<json>.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)


def _domain_matches(host, domains):
    host = (host or "").lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def is_missav_url(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and _domain_matches(
        parsed.hostname, MISSAV_DOMAINS
    )


def is_avple_url(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and _domain_matches(
        parsed.hostname, AVPLE_DOMAINS
    )


def _decode_js_literal(literal):
    if len(literal) < 2 or literal[0] not in ("'", '"') or literal[-1] != literal[0]:
        raise ValueError("invalid JavaScript string")
    text = literal[1:-1]
    out = []
    i = 0
    escapes = {
        "b": "\b", "f": "\f", "n": "\n", "r": "\r",
        "t": "\t", "v": "\v", "0": "\0",
        "\\": "\\", "'": "'", '"': '"',
    }
    while i < len(text):
        ch = text[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(text):
            break
        esc = text[i]
        if esc == "x" and i + 2 < len(text):
            out.append(chr(int(text[i + 1:i + 3], 16)))
            i += 3
            continue
        if esc == "u" and i + 4 < len(text):
            out.append(chr(int(text[i + 1:i + 5], 16)))
            i += 5
            continue
        out.append(escapes.get(esc, esc))
        i += 1
    return "".join(out)


def _packer_token(number, radix):
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if not 2 <= radix <= len(alphabet):
        raise ValueError("unsupported packer radix")
    if number == 0:
        return "0"
    digits = []
    while number:
        number, remainder = divmod(number, radix)
        digits.append(alphabet[remainder])
    return "".join(reversed(digits))


def _unpack_missav_scripts(html):
    payloads = []
    for match in MISSAV_PACKER_RE.finditer(html):
        try:
            payload = _decode_js_literal(match.group("payload"))
            keys = _decode_js_literal(match.group("keys")).split("|")
            radix = int(match.group("radix"))
            count = int(match.group("count"))
            if count < 0 or count > 10000:
                continue
            for value in range(count - 1, -1, -1):
                token = _packer_token(value, radix)
                replacement = keys[value] if value < len(keys) and keys[value] else token
                payload = re.sub(
                    rf"\b{re.escape(token)}\b",
                    lambda _match, replacement=replacement: replacement,
                    payload,
                )
            payloads.append(payload)
        except (ValueError, OverflowError):
            continue
    return payloads


def extract_missav_hls_urls(html):
    values = [html.replace("\\/", "/"), *_unpack_missav_scripts(html)]
    urls = []
    for value in values:
        for match in MISSAV_HLS_RE.finditer(value):
            url = match.group(0).replace("&amp;", "&").replace("\\/", "/")
            if url not in urls:
                urls.append(url)
    return urls


def choose_missav_hls_url(urls):
    if not urls:
        return None

    def score(url):
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path.lower()
        preferred = _domain_matches(host, MISSAV_STREAM_PREFERRED_DOMAINS)
        master = path.endswith("/playlist.m3u8") or "master" in path
        return (100 if preferred else 0) + (20 if master else 0)

    return max(urls, key=score)


def resolve_missav_stream(page_url, timeout=30):
    """Resolve MissAV's public player page to a browser-authenticated HLS URL."""
    if not is_missav_url(page_url):
        raise RuntimeError("MISSAV_UNSUPPORTED_HOST")

    base_headers = {
        "User-Agent": MISSAV_BROWSER_UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    session = browser_requests.Session(impersonate="chrome", headers=base_headers)
    response = session.get(page_url, timeout=timeout, allow_redirects=True)
    if response.status_code != 200:
        raise RuntimeError(f"MISSAV_PAGE_HTTP_{response.status_code}")

    final_url = str(response.url)
    if not is_missav_url(final_url):
        raise RuntimeError("MISSAV_REDIRECTED_TO_UNSUPPORTED_HOST")

    page_title = extract_page_title(response.text)

    urls = extract_missav_hls_urls(response.text)
    stream_url = choose_missav_hls_url(urls)
    if not stream_url:
        raise RuntimeError("MISSAV_STREAM_NOT_FOUND")

    parsed_page = urlparse(final_url)
    request_headers = {
        "User-Agent": MISSAV_BROWSER_UA,
        "Referer": final_url,
        "Origin": f"{parsed_page.scheme}://{parsed_page.netloc}",
        "Accept-Language": "en-US,en;q=0.9",
    }
    cookies = session.cookies.get_dict()
    if cookies:
        request_headers["Cookie"] = "; ".join(
            f"{name}={value}" for name, value in cookies.items()
        )

    probe = session.get(
        stream_url,
        headers=request_headers,
        timeout=timeout,
        allow_redirects=True,
    )
    if probe.status_code != 200:
        raise RuntimeError(f"MISSAV_HLS_HTTP_{probe.status_code}")
    if "#EXTM3U" not in probe.text[:8192]:
        raise RuntimeError("MISSAV_HLS_INVALID_PLAYLIST")

    return {
        "url": stream_url,
        "page_url": final_url,
        "headers": request_headers,
        "title": page_title,
    }


def _extract_avple_json_metadata(html_text):
    for match in AVPLE_JSON_RE.finditer(html_text or ""):
        raw = match.group("json").strip()
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

        page_props = ((data or {}).get("props") or {}).get("pageProps") or {}
        instance = page_props.get("instance") or {}
        meta_info = page_props.get("metaInfo") or {}
        title = _clean_title_text(
            instance.get("title", "") or meta_info.get("siteTitle", "")
        )
        play = instance.get("play") or ""
        asset_prefix = str((data or {}).get("assetPrefix") or "")
        if title or play or asset_prefix:
            return {
                "title": title,
                "play": str(play),
                "asset_prefix": asset_prefix,
            }
    return {"title": "", "play": "", "asset_prefix": ""}


def _extract_avple_source(html_text, page_url):
    match = AVPLE_SOURCE_RE.search(html_text or "")
    if match:
        raw = (
            match.group("url")
            .replace("\\/", "/")
            .replace("&amp;", "&")
            .strip()
        )
        if raw:
            return urljoin(page_url, raw)

    meta = _extract_avple_json_metadata(html_text)
    play = (meta.get("play") or "").replace("\\/", "/").strip()
    if play.startswith(("http://", "https://", "//", "/")):
        return urljoin(page_url, play)

    asset_prefix = (meta.get("asset_prefix") or "").rstrip("/")
    if play and asset_prefix:
        # Older/current Next.js pages expose a relative media path in page
        # metadata. The asset prefix is a useful fallback when inline player
        # JavaScript is unavailable.
        return f"{asset_prefix}/{play.lstrip('/')}"

    candidates = re.findall(
        r"https?://[^\s'\"<>\\;]+\.(?:m3u8|mp4)(?:\?[^\s'\"<>\\;]*)?",
        (html_text or "").replace("\\/", "/"),
        flags=re.IGNORECASE,
    )
    return candidates[0] if candidates else ""


def resolve_avple_stream(page_url, timeout=30):
    if not is_avple_url(page_url):
        raise RuntimeError("SITE2_UNSUPPORTED_HOST")

    base_headers = {
        "User-Agent": MISSAV_BROWSER_UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    parsed_input = urlparse(page_url)
    site_root = f"{parsed_input.scheme}://{parsed_input.netloc}/"

    session = None
    response = None
    last_status = 0
    # Some player pages are stricter about TLS/browser fingerprints than
    # generic extractors. Try a small set of real browser profiles while
    # preserving cookies from a root-page warm-up within each profile.
    for profile in ("chrome", "safari", "chrome_android"):
        candidate = browser_requests.Session(
            impersonate=profile,
            headers=base_headers,
        )
        try:
            candidate.get(
                site_root,
                timeout=min(timeout, 12),
                allow_redirects=True,
            )
        except Exception:
            pass
        try:
            candidate_response = candidate.get(
                page_url,
                headers={**base_headers, "Referer": site_root},
                timeout=timeout,
                allow_redirects=True,
            )
        except Exception:
            continue
        last_status = candidate_response.status_code
        if candidate_response.status_code == 200:
            session = candidate
            response = candidate_response
            break

    if response is None:
        raise RuntimeError(f"SITE2_PAGE_HTTP_{last_status or 'NETWORK'}")

    final_url = str(response.url)
    if not is_avple_url(final_url):
        raise RuntimeError("SITE2_REDIRECTED_TO_UNSUPPORTED_HOST")

    meta = _extract_avple_json_metadata(response.text)
    page_title = meta.get("title") or extract_page_title(response.text)
    stream_url = _extract_avple_source(response.text, final_url)
    if not stream_url:
        raise RuntimeError("SITE2_STREAM_NOT_FOUND")

    parsed_page = urlparse(final_url)
    request_headers = {
        "User-Agent": MISSAV_BROWSER_UA,
        "Referer": final_url,
        "Origin": f"{parsed_page.scheme}://{parsed_page.netloc}",
        "Accept-Language": "en-US,en;q=0.9",
    }
    cookies = session.cookies.get_dict()
    if cookies:
        request_headers["Cookie"] = "; ".join(
            f"{name}={value}" for name, value in cookies.items()
        )

    stream_path = urlparse(stream_url).path.lower()
    if stream_path.endswith(".m3u8"):
        probe = session.get(
            stream_url,
            headers=request_headers,
            timeout=timeout,
            allow_redirects=True,
        )
        if probe.status_code != 200:
            raise RuntimeError(f"SITE2_HLS_HTTP_{probe.status_code}")
        if "#EXTM3U" not in probe.text[:8192]:
            raise RuntimeError("SITE2_HLS_INVALID_PLAYLIST")
    else:
        probe_headers = dict(request_headers)
        probe_headers["Range"] = "bytes=0-4095"
        probe = session.get(
            stream_url,
            headers=probe_headers,
            timeout=timeout,
            allow_redirects=True,
        )
        if probe.status_code not in (200, 206):
            raise RuntimeError(f"SITE2_MEDIA_HTTP_{probe.status_code}")
        if not probe.content:
            raise RuntimeError("SITE2_MEDIA_EMPTY")

    return {
        "url": stream_url,
        "page_url": final_url,
        "headers": request_headers,
        "title": _clean_title_text(page_title),
    }


# ---------------------------------------------------------------------------
# Download worker
# ---------------------------------------------------------------------------

class DownloadWorker(QObject):
    progress = Signal(float, str, str)
    finished = Signal(str)
    failed = Signal(str)      # emits "err_key|raw message"
    cancelled = Signal()

    def __init__(self, url, folder, quality, playlist, i18n):
        super().__init__()
        self.url = url
        self.folder = folder
        self.quality = quality
        self.playlist = playlist
        self.i18n = i18n
        self._cancel = threading.Event()
        self._current_index = 0
        self.media_title = ""

    def cancel(self):
        self._cancel.set()

    def _format_selector(self):
        limits = {
            "4K": 2160, "1440p": 1440, "1080p": 1080,
            "720p": 720, "480p": 480,
        }
        if self.quality in ("最高畫質", "Best quality"):
            return "bv*+ba/b"
        h = limits.get(self.quality)
        if h is None:
            return "bv*+ba/b"
        return f"bv*[height<={h}]+ba/b[height<={h}]"

    def _build_options(self, ffmpeg_exe, compatibility=False):
        """Build yt-dlp options with a lossless MP4 remux guarantee.

        HLS/m3u8 sources can arrive as MPEG-TS or another container. We never
        re-encode them here: FFmpegVideoRemuxer uses stream copy (-c copy).
        yt-dlp's forced fixup also repairs the common MPEG-TS-in-MP4 HLS case.
        """
        if self.playlist:
            outtmpl = os.path.join(
                self.folder,
                "%(playlist_title,uploader)s",
                "%(playlist_index)03d - %(title)s [%(id)s].%(ext)s",
            )
        else:
            outtmpl = os.path.join(self.folder, "%(title)s [%(id)s].%(ext)s")

        options = {
            "format": self._format_selector(),
            "format_sort": ["res", "vcodec:h264", "acodec:aac"],
            "merge_output_format": "mp4",
            "hls_use_mpegts": False,
            "postprocessors": [
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4",
                },
            ],
            # Force yt-dlp's HLS fixup check. For m3u8-native downloads that
            # contain MPEG-TS data behind an .mp4 extension, yt-dlp remuxes
            # with stream copy rather than re-encoding.
            "fixup": "force",
            "outtmpl": outtmpl,
            "windowsfilenames": True,
            "noplaylist": not self.playlist,
            "yesplaylist": self.playlist,
            "ignoreerrors": self.playlist,
            "progress_hooks": [self._hook],
            "ffmpeg_location": ffmpeg_exe,
            # curl_cffi browser impersonation — Chrome fingerprint.
            "impersonate": ImpersonateTarget("chrome"),
            "extractor_args": {
                "generic": {"impersonate": ["chrome"]},
            },
            "retries": 10,
            "fragment_retries": 10,
            "continuedl": True,
            "concurrent_fragment_downloads": 4,
            "quiet": True,
            "no_warnings": True,
        }

        if compatibility:
            # Conservative fallback for flaky CDNs / anti-bot edges. Keep the
            # same selected media, but reduce fragment pressure and retry more.
            options.update({
                "concurrent_fragment_downloads": 1,
                "retries": 20,
                "fragment_retries": 20,
                "extractor_retries": 5,
                "file_access_retries": 5,
                "socket_timeout": 30,
            })

            # Current YouTube fallback: web_safari exposes HLS formats that can
            # avoid some GVS PO-token 403s. Those HLS streams are then finalized
            # by this app's lossless m3u8 -> MP4 remux path.
            if self._is_youtube_url(self.url):
                options["extractor_args"] = {
                    **options.get("extractor_args", {}),
                    "youtube": {"player_client": ["web_safari"]},
                }
        return options

    def _apply_title_output(self, options, resolved_title):
        if resolved_title and not self.playlist:
            options["outtmpl"] = os.path.join(
                self.folder,
                safe_output_title(resolved_title) + ".%(ext)s",
            )
        return options

    @staticmethod
    def _is_missav_url(url):
        return is_missav_url(url)

    @staticmethod
    def _is_avple_url(url):
        return is_avple_url(url)

    @staticmethod
    def _is_youtube_url(url):
        low = (url or "").lower()
        return (
            "youtube.com/" in low
            or "youtu.be/" in low
            or "youtube-nocookie.com/" in low
        )

    @staticmethod
    def _is_retryable_error(message):
        low = (message or "").lower()
        retryable_markers = (
            "http error 403",
            "http error 429",
            "too many requests",
            "temporarily unavailable",
            "timed out",
            "timeout",
            "connection reset",
            "connection aborted",
            "remote end closed",
            "unable to download",
            "fragment",
            "nsig",
            "signature extraction",
            "confirm you're not a bot",
            "confirm you’re not a bot",
            "po token",
            "proof of origin",
            "requested format is not available",
        )
        return any(marker in low for marker in retryable_markers)

    def _hook(self, data):
        if self._cancel.is_set():
            raise yt_dlp.utils.DownloadError("USER_CANCELLED")

        state = data.get("status")
        info_dict = data.get("info_dict") or {}
        media_title = _clean_title_text(info_dict.get("title", ""))
        if media_title and not self.media_title:
            self.media_title = media_title

        if state == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            current = data.get("downloaded_bytes") or 0
            pct = (current / total * 100.0) if total else 0.0

            # Track playlist position for nicer status text.
            idx = data.get("info_dict", {}).get("playlist_index")
            if idx:
                self._current_index = idx

            details = []
            speed = data.get("speed")
            eta = data.get("eta")
            if speed:
                details.append(f"{speed / 1024 / 1024:.1f} MB/s")
            if eta is not None:
                details.append(self.i18n.tr("eta_seconds", eta=eta))
            detail = " · ".join(details) if details else self.i18n.tr("receiving")

            if self.playlist and self._current_index:
                title = self.i18n.tr("playlist_item", n=self._current_index, pct=pct)
            else:
                title = self.i18n.tr("downloading", pct=pct)
            self.progress.emit(pct, title, detail)

        elif state == "finished":
            self.progress.emit(
                100.0, self.i18n.tr("processing"), self.i18n.tr("processing_detail")
            )

    def run(self):
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if not ffmpeg_exe or not os.path.isfile(ffmpeg_exe):
                raise RuntimeError(f"Bundled FFmpeg missing: {ffmpeg_exe}")

            download_url = self.url
            resolved_headers = None
            resolved_title = ""

            if self._is_missav_url(self.url):
                self.progress.emit(
                    0.0,
                    self.i18n.tr("missav_resolving"),
                    self.i18n.tr("missav_resolving_detail"),
                )
                resolved = resolve_missav_stream(self.url)
                download_url = resolved["url"]
                resolved_headers = resolved["headers"]
                resolved_title = _clean_title_text(resolved.get("title", ""))
                if resolved_title:
                    self.media_title = resolved_title
                self.progress.emit(
                    0.0,
                    self.i18n.tr("missav_ready"),
                    self.i18n.tr("missav_ready_detail"),
                )
            elif self._is_avple_url(self.url):
                self.progress.emit(
                    0.0,
                    self.i18n.tr("missav_resolving"),
                    self.i18n.tr("missav_resolving_detail"),
                )
                resolved = resolve_avple_stream(self.url)
                download_url = resolved["url"]
                resolved_headers = resolved["headers"]
                resolved_title = _clean_title_text(resolved.get("title", ""))
                if resolved_title:
                    self.media_title = resolved_title
                self.progress.emit(
                    0.0,
                    self.i18n.tr("missav_ready"),
                    self.i18n.tr("missav_ready_detail"),
                )

            options = self._build_options(ffmpeg_exe)
            if resolved_headers:
                options["http_headers"] = resolved_headers
            self._apply_title_output(options, resolved_title)

            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(download_url, download=True)
            except Exception as first_exc:
                first_msg = str(first_exc)
                if self._cancel.is_set() or "USER_CANCELLED" in first_msg:
                    raise
                if not self._is_retryable_error(first_msg):
                    raise

                self.progress.emit(
                    0.0,
                    self.i18n.tr("retrying"),
                    self.i18n.tr("retrying_detail"),
                )
                fallback = self._build_options(ffmpeg_exe, compatibility=True)
                if resolved_headers:
                    fallback["http_headers"] = resolved_headers
                self._apply_title_output(fallback, resolved_title)
                with yt_dlp.YoutubeDL(fallback) as ydl:
                    info = ydl.extract_info(download_url, download=True)

            if self._cancel.is_set():
                self.cancelled.emit()
                return

            if resolved_title:
                title = resolved_title
            elif info and info.get("_type") == "playlist":
                title = info.get("title") or "Playlist"
            else:
                title = (info or {}).get("title") or "Video"
            self.finished.emit(title)

        except Exception as exc:
            msg = str(exc)
            if self._cancel.is_set() or "USER_CANCELLED" in msg:
                self.cancelled.emit()
            else:
                self.failed.emit(self._classify_error(msg))

    def _classify_error(self, msg):
        low = msg.lower()
        if "drm" in low or "protected" in low:
            return "err_drm|" + msg
        if "private" in low or "sign in" in low or "log in" in low or "login" in low:
            return "err_private|" + msg
        if (
            "unsupported url" in low
            or "no video" in low
            or "unable to extract" in low
            or "missav_stream_not_found" in low
            or "missav_redirected_to_unsupported_host" in low
            or "site2_stream_not_found" in low
            or "site2_redirected_to_unsupported_host" in low
        ):
            return "err_unsupported|" + msg
        return "err_generic|" + msg


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.jobs = []
        self.active_jobs = {}
        self.next_job_id = 1
        self.queue_running = False
        self.stop_requested = False
        self.run_config = None
        self.settings = settings or QSettings(ORG_NAME, APP_NAME)

        lang = self.settings.value("language", "zh_TW")
        self.theme_mode = self.settings.value("theme", "system")
        self.i18n = I18n(lang)

        self.setWindowTitle(APP_NAME)
        self.resize(1040, 840)
        self.setMinimumSize(880, 720)
        saved_geometry = self.settings.value("window_geometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)

        root = QWidget()
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(34, 20, 34, 22)
        page.setSpacing(14)

        # ---- Header: title + toolbar (theme / language) ----
        head = QHBoxLayout()
        head.setSpacing(12)

        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.title = QLabel()
        self.title.setObjectName("Title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("Subtitle")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        head.addLayout(titles)
        head.addStretch(1)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("Toolbar")
        self.theme_combo.setFixedWidth(130)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("Toolbar")
        self.lang_combo.setFixedWidth(120)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        toolbar.addWidget(self.theme_combo)
        toolbar.addWidget(self.lang_combo)
        head.addLayout(toolbar)
        page.addLayout(head)

        # ---- Main card ----
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 18, 24, 18)
        card_layout.setSpacing(12)

        self.link_label = self._section_label()
        card_layout.addWidget(self.link_label)

        url_row = QHBoxLayout()
        url_row.setSpacing(10)
        self.url_edit = QLineEdit()
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.returnPressed.connect(self.add_input_to_queue)

        self.add_btn = QPushButton()
        self.add_btn.setObjectName("Secondary")
        self.add_btn.setMinimumWidth(108)
        self.add_btn.clicked.connect(self.add_input_to_queue)

        self.paste_btn = QPushButton()
        self.paste_btn.setObjectName("Secondary")
        self.paste_btn.setMinimumWidth(126)
        self.paste_btn.clicked.connect(self.paste_url)

        self.focus_url_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.focus_url_shortcut.activated.connect(self._focus_url_input)

        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(self.add_btn)
        url_row.addWidget(self.paste_btn)
        card_layout.addLayout(url_row)

        # Desktop download-manager layout: queue gets the main canvas; the
        # adjustable settings and actions live in a compact side panel.
        body_row = QHBoxLayout()
        body_row.setSpacing(16)

        queue_panel = QWidget()
        queue_layout = QVBoxLayout(queue_panel)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        queue_layout.setSpacing(10)

        queue_head = QHBoxLayout()
        queue_head.setSpacing(10)
        self.queue_label = self._section_label()
        self.queue_count_label = QLabel()
        self.queue_count_label.setObjectName("Muted")
        self.queue_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        queue_head.addWidget(self.queue_label)
        queue_head.addStretch(1)
        queue_head.addWidget(self.queue_count_label)
        queue_layout.addLayout(queue_head)

        self.queue_hint_label = QLabel()
        self.queue_hint_label.setObjectName("Faint")
        self.queue_hint_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.queue_hint_label.setMinimumWidth(0)
        queue_layout.addWidget(self.queue_hint_label)

        self.queue_tree = QTreeWidget()
        self.queue_tree.setColumnCount(3)
        self.queue_tree.setRootIsDecorated(False)
        self.queue_tree.setIndentation(0)
        self.queue_tree.setUniformRowHeights(True)
        self.queue_tree.setAlternatingRowColors(True)
        self.queue_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.queue_tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.queue_tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.queue_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.queue_tree.setTextElideMode(Qt.ElideMiddle)
        self.queue_tree.setMinimumHeight(280)
        self.queue_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.queue_tree.itemSelectionChanged.connect(self._refresh_queue_controls)
        self.delete_queue_shortcut = QShortcut(QKeySequence("Delete"), self.queue_tree)
        self.delete_queue_shortcut.activated.connect(self.remove_selected_jobs)

        header = self.queue_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(0, 104)
        header.resizeSection(2, 76)
        queue_layout.addWidget(self.queue_tree, 1)

        queue_actions = QHBoxLayout()
        queue_actions.setSpacing(8)
        self.remove_btn = QPushButton()
        self.remove_btn.setObjectName("Ghost")
        self.remove_btn.clicked.connect(self.remove_selected_jobs)
        self.clear_finished_btn = QPushButton()
        self.clear_finished_btn.setObjectName("Ghost")
        self.clear_finished_btn.clicked.connect(self.clear_finished_jobs)
        self.retry_failed_btn = QPushButton()
        self.retry_failed_btn.setObjectName("Ghost")
        self.retry_failed_btn.clicked.connect(self.retry_failed_jobs)

        queue_actions.addWidget(self.remove_btn)
        queue_actions.addWidget(self.retry_failed_btn)
        queue_actions.addWidget(self.clear_finished_btn)
        queue_actions.addStretch(1)
        queue_layout.addLayout(queue_actions)

        body_row.addWidget(queue_panel, 1)

        settings_panel = QFrame()
        settings_panel.setObjectName("SettingsPanel")
        settings_panel.setMinimumWidth(286)
        settings_panel.setMaximumWidth(324)
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setSpacing(8)

        self.quality_label = self._section_label()
        self.quality_combo = QComboBox()
        settings_layout.addWidget(self.quality_label)
        settings_layout.addWidget(self.quality_combo)

        self.playlist_label = self._section_label()
        self.playlist_combo = QComboBox()
        settings_layout.addWidget(self.playlist_label)
        settings_layout.addWidget(self.playlist_combo)

        self.concurrency_label = self._section_label()
        self.concurrency_combo = QComboBox()
        for value in (1, 2, 3):
            self.concurrency_combo.addItem("", value)
        saved_concurrency = int(self.settings.value("concurrency", 1) or 1)
        saved_concurrency = saved_concurrency if saved_concurrency in (1, 2, 3) else 1
        self.concurrency_combo.setCurrentIndex(saved_concurrency - 1)
        self.concurrency_combo.currentIndexChanged.connect(self.on_concurrency_changed)
        settings_layout.addWidget(self.concurrency_label)
        settings_layout.addWidget(self.concurrency_combo)

        self.save_label = self._section_label()
        settings_layout.addWidget(self.save_label)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        saved_path = self.settings.value("folder", str(Path.home() / "Downloads"))
        self.path_edit = QLineEdit(saved_path)
        self.browse_btn = QPushButton()
        self.browse_btn.setObjectName("Secondary")
        self.browse_btn.setMinimumWidth(106)
        self.browse_btn.clicked.connect(self.choose_folder)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(self.browse_btn)
        settings_layout.addLayout(path_row)

        settings_layout.addStretch(1)

        status_card = QFrame()
        status_card.setObjectName("StatusCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(12, 10, 12, 11)
        status_layout.setSpacing(4)

        self.status_label = QLabel()
        f = QFont("Segoe UI", 11)
        f.setWeight(QFont.DemiBold)
        self.status_label.setFont(f)
        self.status_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.status_label.setMinimumWidth(0)

        self.detail_label = QLabel()
        self.detail_label.setObjectName("Muted")
        self.detail_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.detail_label.setMinimumWidth(0)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.detail_label)
        status_layout.addSpacing(4)
        status_layout.addWidget(self.progress)
        settings_layout.addWidget(status_card)

        secondary_actions = QHBoxLayout()
        secondary_actions.setSpacing(8)
        self.open_btn = QPushButton()
        self.open_btn.setObjectName("Ghost")
        self.open_btn.clicked.connect(self.open_folder)
        self.cancel_btn = QPushButton()
        self.cancel_btn.setObjectName("Ghost")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        secondary_actions.addWidget(self.open_btn, 1)
        secondary_actions.addWidget(self.cancel_btn, 1)
        settings_layout.addLayout(secondary_actions)

        self.download_btn = QPushButton()
        self.download_btn.setObjectName("Primary")
        self.download_btn.clicked.connect(self.start_download)
        settings_layout.addWidget(self.download_btn)

        body_row.addWidget(settings_panel)
        card_layout.addLayout(body_row, 1)

        self.note = QLabel()
        self.note.setObjectName("Faint")
        self.note.setWordWrap(True)
        card_layout.addWidget(self.note)

        page.addWidget(card, 1)

        # Populate combos & text, then apply theme.
        self._populate_static_combos()
        self.retranslate()
        self.apply_theme()

    # ---- helpers ----
    def _section_label(self):
        label = QLabel()
        label.setObjectName("Section")
        return label

    def _populate_static_combos(self):
        # Theme combo (store mode as data)
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        for mode in ("system", "light", "dark"):
            self.theme_combo.addItem("", mode)
        idx = {"system": 0, "light": 1, "dark": 2}.get(self.theme_mode, 0)
        self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)

        # Language combo (store lang code as data)
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        for code in LANG_ORDER:
            self.lang_combo.addItem(TRANSLATIONS[code]["language_name"], code)
        cur = LANG_ORDER.index(self.i18n.lang) if self.i18n.lang in LANG_ORDER else 0
        self.lang_combo.setCurrentIndex(cur)
        self.lang_combo.blockSignals(False)

    def retranslate(self):
        tr = self.i18n.tr
        self.title.setText(tr("app_title"))
        self.subtitle.setText(tr("subtitle"))
        self.link_label.setText(tr("link_section"))
        self.url_edit.setPlaceholderText(tr("url_placeholder"))
        self.add_btn.setText(tr("add_queue"))
        self.paste_btn.setText(tr("paste"))
        self.queue_label.setText(tr("queue"))
        self.queue_hint_label.setText(tr("queue_hint"))
        self.remove_btn.setText(tr("remove_selected"))
        self.retry_failed_btn.setText(tr("retry_failed"))
        self.clear_finished_btn.setText(tr("clear_finished"))
        self.concurrency_label.setText(tr("concurrency"))
        self.concurrency_combo.blockSignals(True)
        for index, key in enumerate(("concurrency_1", "concurrency_2", "concurrency_3")):
            self.concurrency_combo.setItemText(index, tr(key))
        self.concurrency_combo.blockSignals(False)
        self.queue_tree.setHeaderLabels(
            [tr("queue_status"), tr("queue_item"), tr("queue_progress")]
        )
        for job in self.jobs:
            self._render_job(job)
        self._refresh_queue_controls()
        self.quality_label.setText(tr("quality"))
        self.playlist_label.setText(tr("playlist"))
        self.save_label.setText(tr("save_location"))
        self.browse_btn.setText(tr("choose_folder"))
        self.open_btn.setText(tr("open_folder"))
        self.cancel_btn.setText(tr("cancel"))
        self.download_btn.setText(tr("start_queue"))
        self.note.setText(tr("note"))

        # Quality combo — preserve selection by index.
        q_idx = max(0, self.quality_combo.currentIndex())
        self.quality_combo.blockSignals(True)
        self.quality_combo.clear()
        self.quality_combo.addItems(
            [tr("quality_best"), "4K", "1440p", "1080p", "720p", "480p"]
        )
        self.quality_combo.setCurrentIndex(q_idx)
        self.quality_combo.blockSignals(False)

        # Playlist combo
        p_idx = max(0, self.playlist_combo.currentIndex())
        self.playlist_combo.blockSignals(True)
        self.playlist_combo.clear()
        self.playlist_combo.addItems([tr("playlist_single"), tr("playlist_all")])
        self.playlist_combo.setCurrentIndex(p_idx)
        self.playlist_combo.blockSignals(False)

        # Theme combo labels
        self.theme_combo.blockSignals(True)
        self.theme_combo.setItemText(0, tr("theme_system"))
        self.theme_combo.setItemText(1, tr("theme_light"))
        self.theme_combo.setItemText(2, tr("theme_dark"))
        self.theme_combo.blockSignals(False)

        # Only reset status text if idle and no completed queue summary is showing.
        if not self.queue_running and not self.active_jobs:
            counts = self._queue_counts()
            if counts["pending"]:
                self.status_label.setText(tr("ready"))
                self.detail_label.setText(tr("queue_stopped_detail", pending=counts["pending"]))
            elif counts["done"] or counts["failed"]:
                self.status_label.setText(tr("queue_complete"))
                self.detail_label.setText(
                    tr("queue_complete_detail", done=counts["done"], failed=counts["failed"])
                )
            else:
                self.status_label.setText(tr("ready"))
                self.detail_label.setText(tr("ready_detail"))

    def apply_theme(self):
        key = resolve_theme(self.theme_mode)
        qss = build_qss(PALETTES[key])
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)

    # ---- toolbar handlers ----
    def on_theme_changed(self, index):
        self.theme_mode = self.theme_combo.itemData(index) or "system"
        self.settings.setValue("theme", self.theme_mode)
        self.apply_theme()

    def on_language_changed(self, index):
        code = self.lang_combo.itemData(index) or "zh_TW"
        self.i18n.set_language(code)
        self.settings.setValue("language", code)
        self.retranslate()

    def on_concurrency_changed(self, index):
        value = int(self.concurrency_combo.itemData(index) or 1)
        self.settings.setValue("concurrency", value)

    # ---- actions ----
    def _focus_url_input(self):
        self.url_edit.setFocus()
        self.url_edit.selectAll()

    def _extract_urls(self, text):
        """Extract HTTP(S) links from clipboard/input while preserving order."""
        if not text:
            return []
        found = re.findall(r"https?://\S+", text, flags=re.IGNORECASE)
        urls = []
        for raw in found:
            url = raw.rstrip(".,;")
            if url:
                urls.append(url)
        return urls

    def _status_text(self, status):
        return self.i18n.tr({
            "pending": "status_pending",
            "active": "status_active",
            "done": "status_done",
            "failed": "status_failed",
            "cancelled": "status_cancelled",
        }.get(status, "status_pending"))

    @staticmethod
    def _compact_url(url):
        try:
            parsed = urlparse(url)
            host = parsed.hostname or url
            path = (parsed.path or "").rstrip("/")
            tail = path.rsplit("/", 1)[-1] if path else ""
            if tail:
                return f"{host}  ·  {tail}"
            return host
        except Exception:
            return url

    def _render_job(self, job):
        item = job["item"]
        item.setText(0, self._status_text(job["status"]))

        display_name = _clean_title_text(job.get("title", ""))
        if not display_name:
            display_name = self._compact_url(job["url"])
        item.setText(1, display_name)

        pct = job.get("pct", 0.0)
        if job["status"] == "done":
            item.setText(2, "100%")
        elif job["status"] == "failed":
            item.setText(2, "—")
        else:
            item.setText(2, f"{pct:.0f}%")

        tooltip = job["url"]
        if job.get("title"):
            tooltip = job["title"] + "\n" + job["url"]
        item.setToolTip(1, tooltip)
        item.setToolTip(0, job.get("error", ""))

    def _queue_counts(self):
        counts = {"pending": 0, "active": 0, "done": 0, "failed": 0, "cancelled": 0}
        for job in self.jobs:
            counts[job["status"]] = counts.get(job["status"], 0) + 1
        return counts

    def _find_job(self, job_id):
        return next((job for job in self.jobs if job["id"] == job_id), None)

    def _refresh_queue_controls(self):
        counts = self._queue_counts()
        self.queue_count_label.setText(self.i18n.tr("queue_count", count=len(self.jobs)))
        if self.jobs:
            self.queue_hint_label.setText(
                self.i18n.tr(
                    "queue_state_summary",
                    pending=counts["pending"],
                    active=counts["active"],
                    done=counts["done"],
                    failed=counts["failed"],
                )
            )
        else:
            self.queue_hint_label.setText(self.i18n.tr("queue_hint"))

        removable = any(
            self._find_job(item.data(0, Qt.UserRole)) is not None
            and self._find_job(item.data(0, Qt.UserRole))["status"] != "active"
            for item in self.queue_tree.selectedItems()
        )
        self.remove_btn.setEnabled(removable)
        self.clear_finished_btn.setEnabled(
            any(job["status"] == "done" for job in self.jobs)
        )
        self.retry_failed_btn.setEnabled(
            any(job["status"] == "failed" for job in self.jobs)
        )
        can_start = (
            (not self.queue_running)
            and (not self.active_jobs)
            and counts["pending"] > 0
        )
        self.download_btn.setEnabled(can_start)
        if can_start and (counts["done"] or counts["failed"] or counts["cancelled"]):
            self.download_btn.setText(self.i18n.tr("resume_queue"))
        else:
            self.download_btn.setText(self.i18n.tr("start_queue"))
        self._update_overall_progress()

    def _update_overall_progress(self):
        if not self.jobs:
            self.progress.setValue(0)
            return
        total = 0.0
        for job in self.jobs:
            if job["status"] in ("done", "failed"):
                total += 100.0
            else:
                total += float(job.get("pct", 0.0))
        self.progress.setValue(int((total / len(self.jobs)) * 10))

    def add_urls(self, text):
        urls = self._extract_urls(text)
        existing = {
            job["url"] for job in self.jobs if job["status"] in ("pending", "active")
        }
        scroll_bar = self.queue_tree.verticalScrollBar()
        follow_tail = (
            scroll_bar.maximum() == 0
            or scroll_bar.value() >= max(0, scroll_bar.maximum() - 24)
        )

        added = 0
        skipped = 0
        last_added_item = None
        for url in urls:
            if url in existing:
                skipped += 1
                continue
            job_id = self.next_job_id
            self.next_job_id += 1
            item = QTreeWidgetItem()
            item.setData(0, Qt.UserRole, job_id)
            job = {
                "id": job_id,
                "url": url,
                "status": "pending",
                "pct": 0.0,
                "title": "",
                "error": "",
                "item": item,
            }
            self.jobs.append(job)
            self.queue_tree.addTopLevelItem(item)
            self._render_job(job)
            last_added_item = item
            existing.add(url)
            added += 1

        if added:
            self.url_edit.clear()
            self.url_edit.setFocus()
            self.status_label.setText(self.i18n.tr("ready"))
            detail = self.i18n.tr("added_urls", added=added)
            if skipped:
                detail += " · " + self.i18n.tr("skipped_duplicates", skipped=skipped)
            self.detail_label.setText(detail)
        elif skipped:
            self.detail_label.setText(self.i18n.tr("skipped_duplicates", skipped=skipped))

        self._refresh_queue_controls()
        if last_added_item is not None and follow_tail:
            self.queue_tree.scrollToItem(
                last_added_item,
                QAbstractItemView.PositionAtBottom,
            )
        if self.queue_running:
            self._pump_queue()
        return added, skipped

    def add_input_to_queue(self):
        text = self.url_edit.text().strip()
        if text:
            self.add_urls(text)

    def paste_url(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.add_urls(text)

    def remove_selected_jobs(self):
        selected_ids = {item.data(0, Qt.UserRole) for item in self.queue_tree.selectedItems()}
        for job in list(self.jobs):
            if job["id"] not in selected_ids or job["status"] == "active":
                continue
            index = self.queue_tree.indexOfTopLevelItem(job["item"])
            if index >= 0:
                self.queue_tree.takeTopLevelItem(index)
            self.jobs.remove(job)
        self._refresh_queue_controls()

    def clear_finished_jobs(self):
        # Keep failed rows visible so users do not lose retry/error context.
        for job in list(self.jobs):
            if job["status"] != "done":
                continue
            index = self.queue_tree.indexOfTopLevelItem(job["item"])
            if index >= 0:
                self.queue_tree.takeTopLevelItem(index)
            self.jobs.remove(job)
        self._refresh_queue_controls()

    def retry_failed_jobs(self):
        retried = 0
        for job in self.jobs:
            if job["status"] != "failed":
                continue
            job["status"] = "pending"
            job["pct"] = 0.0
            job["error"] = ""
            self._render_job(job)
            retried += 1
        self._refresh_queue_controls()
        if retried and self.queue_running:
            self._pump_queue()

    def closeEvent(self, event):
        self.settings.setValue("window_geometry", self.saveGeometry())
        super().closeEvent(event)

    def choose_folder(self):
        current = self.path_edit.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, self.i18n.tr("choose_folder"), current
        )
        if folder:
            self.path_edit.setText(folder)
            self.settings.setValue("folder", folder)

    def open_folder(self):
        folder = self.path_edit.text().strip()
        if not folder:
            return
        Path(folder).mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def set_busy(self, busy):
        self.cancel_btn.setEnabled(busy)
        self.quality_combo.setEnabled(not busy)
        self.playlist_combo.setEnabled(not busy)
        self.path_edit.setEnabled(not busy)
        self.browse_btn.setEnabled(not busy)
        self.concurrency_combo.setEnabled(not busy)
        # URL input stays live while downloading so new links can join the queue.
        self.url_edit.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.paste_btn.setEnabled(True)
        self._refresh_queue_controls()

    def start_download(self):
        # One-click compatibility: text still in the input is queued first.
        if self.url_edit.text().strip():
            self.add_input_to_queue()

        folder = self.path_edit.text().strip()
        tr = self.i18n.tr
        counts = self._queue_counts()

        if not counts["pending"]:
            QMessageBox.warning(self, tr("warn_no_queue_title"), tr("warn_no_queue"))
            return
        if not folder:
            QMessageBox.warning(self, tr("warn_no_folder_title"), tr("warn_no_folder"))
            return

        Path(folder).mkdir(parents=True, exist_ok=True)
        self.settings.setValue("folder", folder)
        self.run_config = {
            "folder": folder,
            "quality": self.quality_combo.currentText(),
            "playlist": self.playlist_combo.currentIndex() == 1,
            "concurrency": int(self.concurrency_combo.currentData() or 1),
        }
        self.stop_requested = False
        self.queue_running = True
        self.status_label.setText(tr("resolving"))
        self.detail_label.setText(tr("queue_running_detail"))
        self.set_busy(True)
        self._pump_queue()

    def _pump_queue(self):
        if not self.queue_running or not self.run_config:
            return
        limit = self.run_config["concurrency"]
        while len(self.active_jobs) < limit:
            job = next((j for j in self.jobs if j["status"] == "pending"), None)
            if not job:
                break
            self._start_job(job)

        counts = self._queue_counts()
        if self.active_jobs:
            self.status_label.setText(
                self.i18n.tr(
                    "queue_running",
                    active=len(self.active_jobs),
                    pending=counts["pending"],
                )
            )
            self.detail_label.setText(self.i18n.tr("queue_running_detail"))
        elif counts["pending"] == 0:
            self._finish_queue()

    def _make_worker_request(self, job):
        return {
            "url": job["url"],
            "folder": self.run_config["folder"],
            "quality": self.run_config["quality"],
            "playlist": self.run_config["playlist"],
            "language": self.i18n.lang,
        }

    def _worker_command(self, request_path, state_path):
        if getattr(sys, "frozen", False):
            return sys.executable, ["--download-worker", request_path, state_path]
        return (
            sys.executable,
            [str(Path(__file__).resolve()), "--download-worker", request_path, state_path],
        )

    def _start_job(self, job):
        job["status"] = "active"
        job["pct"] = 0.0
        job["error"] = ""
        self._render_job(job)

        job_id = job["id"]
        work_dir = tempfile.mkdtemp(prefix=f"video-downloader-{job_id}-")
        request_path = str(Path(work_dir) / "request.json")
        state_path = str(Path(work_dir) / "state.json")
        _atomic_write_json(request_path, self._make_worker_request(job))

        process = QProcess(self)
        timer = QTimer(self)
        timer.setInterval(200)

        program, args = self._worker_command(request_path, state_path)
        process.setProgram(program)
        process.setArguments(args)

        self.active_jobs[job_id] = {
            "process": process,
            "timer": timer,
            "tempdir": work_dir,
            "state_path": state_path,
            "last_state": None,
            "finalized": False,
            "cancel_requested": False,
        }

        timer.timeout.connect(lambda jid=job_id: self._poll_worker_state(jid))
        process.finished.connect(
            lambda code, status, jid=job_id:
                self._on_worker_process_finished(jid, int(code), status)
        )
        process.errorOccurred.connect(
            lambda error, jid=job_id: self._on_worker_process_error(jid, error)
        )

        timer.start()
        process.start()
        self._refresh_queue_controls()

    def _poll_worker_state(self, job_id):
        entry = self.active_jobs.get(job_id)
        if not entry:
            return
        path = Path(entry["state_path"])
        if not path.is_file():
            return
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if state == entry.get("last_state"):
            return
        entry["last_state"] = state

        if state.get("status") == "progress":
            job = self._find_job(job_id)
            media_title = _clean_title_text(state.get("media_title", ""))
            if job is not None and media_title:
                job["title"] = media_title
            self.on_job_progress(
                job_id,
                float(state.get("pct", 0.0)),
                str(state.get("title", "")),
                str(state.get("detail", "")),
            )

    def _on_worker_process_error(self, job_id, error):
        entry = self.active_jobs.get(job_id)
        if not entry or entry.get("finalized"):
            return
        if error == QProcess.ProcessError.FailedToStart:
            entry["last_state"] = {
                "status": "failed",
                "payload": "err_generic|Download worker failed to start.",
            }
            self._finalize_worker_job(job_id, -1, QProcess.ExitStatus.CrashExit)

    def _on_worker_process_finished(self, job_id, exit_code, exit_status):
        self._finalize_worker_job(job_id, exit_code, exit_status)

    def _finalize_worker_job(self, job_id, exit_code, exit_status):
        entry = self.active_jobs.get(job_id)
        if not entry or entry.get("finalized"):
            return
        entry["finalized"] = True
        self._poll_worker_state(job_id)
        state = entry.get("last_state") or {}

        if entry.get("cancel_requested") or self.stop_requested:
            self.on_job_cancelled(job_id)
        elif state.get("status") == "done":
            self.on_job_finished(job_id, str(state.get("title") or "Video"))
        elif state.get("status") == "failed":
            self.on_job_failed(
                job_id,
                str(state.get("payload") or "err_generic|Download failed."),
            )
        elif state.get("status") == "cancelled":
            self.on_job_cancelled(job_id)
        else:
            status_value = getattr(exit_status, "value", exit_status)
            raw = (
                f"Download worker exited unexpectedly "
                f"(exit code {exit_code}, status {status_value})."
            )
            self.on_job_failed(job_id, "worker_crashed|" + raw)

        timer = entry.get("timer")
        process = entry.get("process")
        if timer:
            timer.stop()
            timer.deleteLater()
        if process:
            process.deleteLater()
        shutil.rmtree(entry.get("tempdir", ""), ignore_errors=True)
        self.active_jobs.pop(job_id, None)

        if self.queue_running:
            self._pump_queue()
        elif not self.active_jobs:
            self.set_busy(False)
            counts = self._queue_counts()
            self.status_label.setText(self.i18n.tr("queue_stopped"))
            self.detail_label.setText(
                self.i18n.tr("queue_stopped_detail", pending=counts["pending"])
            )

    def cancel_download(self):
        if not self.active_jobs:
            return
        self.queue_running = False
        self.stop_requested = True
        self.status_label.setText(self.i18n.tr("cancelling"))
        self.detail_label.setText(self.i18n.tr("cancelling_detail"))
        for entry in list(self.active_jobs.values()):
            entry["cancel_requested"] = True
            process = entry.get("process")
            if process and process.state() != QProcess.ProcessState.NotRunning:
                process.terminate()
                QTimer.singleShot(
                    2500,
                    lambda p=process: (
                        p.kill()
                        if p.state() != QProcess.ProcessState.NotRunning
                        else None
                    ),
                )

    def on_job_progress(self, job_id, pct, title, detail):
        job = self._find_job(job_id)
        if not job:
            return
        job["pct"] = max(0.0, min(100.0, pct))
        self._render_job(job)
        self.status_label.setText(title)
        self.detail_label.setText(detail)
        self._update_overall_progress()

    def on_job_finished(self, job_id, title):
        job = self._find_job(job_id)
        if not job:
            return
        job["status"] = "done"
        job["pct"] = 100.0
        job["title"] = title
        self._render_job(job)
        self.status_label.setText(self.i18n.tr("done"))
        self.detail_label.setText(title)
        self._refresh_queue_controls()

    def on_job_failed(self, job_id, payload):
        job = self._find_job(job_id)
        if not job:
            return
        if "|" in payload:
            key, raw = payload.split("|", 1)
        else:
            key, raw = "err_generic", payload
        job["status"] = "failed"
        job["pct"] = 100.0
        job["error"] = self.i18n.tr(key) + "\n" + raw
        self._render_job(job)
        self.status_label.setText(self.i18n.tr("failed"))
        self.detail_label.setText(self.i18n.tr(key))
        self._refresh_queue_controls()

    def on_job_cancelled(self, job_id):
        job = self._find_job(job_id)
        if not job:
            return
        # Stopping the queue is resumable: cancelled active items return to pending.
        if self.stop_requested:
            job["status"] = "pending"
            job["pct"] = 0.0
        else:
            job["status"] = "cancelled"
        self._render_job(job)
        self._refresh_queue_controls()

    def _finish_queue(self):
        self.queue_running = False
        self.stop_requested = False
        self.run_config = None
        self.set_busy(False)
        counts = self._queue_counts()
        self.progress.setValue(1000 if self.jobs else 0)
        self.status_label.setText(self.i18n.tr("queue_complete"))
        self.detail_label.setText(
            self.i18n.tr(
                "queue_complete_detail",
                done=counts["done"],
                failed=counts["failed"],
            )
        )


def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def download_worker_main(request_path, state_path):
    """Run one download in a separate OS process.

    A native crash in yt-dlp/curl_cffi/FFmpeg can terminate this worker, but
    cannot terminate the Qt GUI process that owns the download queue.
    """
    try:
        request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    except Exception as exc:
        _atomic_write_json(
            state_path,
            {"status": "failed", "payload": "err_generic|" + str(exc)},
        )
        return 2

    test_mode = request.get("_test_mode")
    if test_mode == "crash":
        os._exit(23)
    if test_mode == "unsupported":
        _atomic_write_json(
            state_path,
            {
                "status": "failed",
                "payload": "err_unsupported|ERROR: Unsupported URL: test fixture",
            },
        )
        return 2
    if test_mode == "success":
        _atomic_write_json(
            state_path,
            {"status": "done", "title": "CI worker success"},
        )
        return 0

    i18n = I18n(request.get("language", "zh_TW"))
    worker = DownloadWorker(
        request["url"],
        request["folder"],
        request["quality"],
        bool(request.get("playlist")),
        i18n,
    )
    terminal = {"status": None}

    def on_progress(pct, title, detail):
        _atomic_write_json(
            state_path,
            {
                "status": "progress",
                "pct": float(pct),
                "title": title,
                "detail": detail,
                "media_title": worker.media_title,
            },
        )

    def on_finished(title):
        terminal["status"] = "done"
        _atomic_write_json(state_path, {"status": "done", "title": title})

    def on_failed(payload):
        terminal["status"] = "failed"
        _atomic_write_json(state_path, {"status": "failed", "payload": payload})

    def on_cancelled():
        terminal["status"] = "cancelled"
        _atomic_write_json(state_path, {"status": "cancelled"})

    worker.progress.connect(on_progress)
    worker.finished.connect(on_finished)
    worker.failed.connect(on_failed)
    worker.cancelled.connect(on_cancelled)

    try:
        worker.run()
    except BaseException as exc:
        _atomic_write_json(
            state_path,
            {
                "status": "failed",
                "payload": "err_generic|" + repr(exc),
            },
        )
        return 2

    return 0 if terminal["status"] == "done" else 2


def install_exception_hook():
    """Log unexpected UI exceptions instead of letting them terminate silently."""
    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        try:
            base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
            log_dir = base / ORG_NAME / APP_NAME
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "error.log").open("a", encoding="utf-8") as log:
                log.write("\n" + "=" * 72 + "\n")
                log.write(detail)
        except Exception:
            pass

        app = QApplication.instance()
        if app is not None:
            try:
                lang = QSettings(ORG_NAME, APP_NAME).value("language", "zh_TW")
                QMessageBox.critical(
                    None,
                    APP_NAME,
                    I18n(lang).tr("unexpected_error"),
                )
                return
            except Exception:
                pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = handle_exception


# ---------------------------------------------------------------------------
# Smoke test (used by CI) & entry point
# ---------------------------------------------------------------------------

def smoke_test(app):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if not ffmpeg or not os.path.isfile(ffmpeg):
        raise RuntimeError(f"Bundled FFmpeg missing: {ffmpeg}")

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        if ydl is None:
            raise RuntimeError("yt-dlp initialization failed")
        if not ydl._impersonate_target_available(ImpersonateTarget()):
            raise RuntimeError("curl_cffi impersonation target is unavailable")

    # Regression guard: HLS/non-MP4 media is always stream-copied into MP4.
    worker = DownloadWorker(
        "https://example.com/video.m3u8",
        str(Path.home() / "Downloads"),
        "Best quality",
        False,
        I18n("en"),
    )
    opts = worker._build_options(ffmpeg)
    assert opts["merge_output_format"] == "mp4"
    assert opts["hls_use_mpegts"] is False
    assert opts["fixup"] == "force"
    assert {
        "key": "FFmpegVideoRemuxer",
        "preferedformat": "mp4",
    } in opts["postprocessors"]

    yt_worker = DownloadWorker(
        "https://www.youtube.com/watch?v=nZAHDChkLkk",
        str(Path.home() / "Downloads"),
        "Best quality",
        False,
        I18n("en"),
    )
    yt_fallback = yt_worker._build_options(ffmpeg, compatibility=True)
    assert yt_fallback["extractor_args"]["youtube"]["player_client"] == ["web_safari"]
    assert yt_fallback["hls_use_mpegts"] is False
    assert DownloadWorker._is_retryable_error("PO Token required")

    # Test both themes and both languages render without error.
    settings = QSettings(ORG_NAME, APP_NAME + "-SmokeTest")
    settings.clear()
    window = MainWindow(settings=settings)
    window.resize(1040, 840)

    for mode in ("system", "light", "dark"):
        window.theme_mode = mode
        window.apply_theme()
        app.processEvents()

    for code in LANG_ORDER:
        window.i18n.set_language(code)
        window.retranslate()
        app.processEvents()

    window.show()
    app.processEvents()
    app.processEvents()

    assert window.url_edit.height() >= 42
    assert window.path_edit.height() >= 42
    assert window.download_btn.height() >= 42
    assert window.quality_combo.height() >= 42
    assert window.playlist_combo.height() >= 42
    assert window.queue_tree.minimumHeight() >= 160
    assert window.concurrency_combo.count() == 3
    assert window.width() >= 880
    assert window.height() >= 720

    # Queue UX regression: multi-paste preserves order, skips active/pending duplicates,
    # and removing a selected waiting item never touches another entry.
    added, skipped = window.add_urls(
        "https://example.com/video-a\n"
        "https://example.com/video-b\n"
        "https://example.com/video-a"
    )
    assert added == 2 and skipped == 1
    assert [j["url"] for j in window.jobs] == [
        "https://example.com/video-a",
        "https://example.com/video-b",
    ]
    assert all(j["status"] == "pending" for j in window.jobs)
    window.queue_tree.setCurrentItem(window.jobs[0]["item"])
    window.remove_selected_jobs()
    assert len(window.jobs) == 1
    assert window.jobs[0]["url"] == "https://example.com/video-b"

    # Failure isolation regression: a website failure must stay inside its row,
    # keep the app alive, and be retryable without discarding the queue.
    failed_job = window.jobs[0]
    window.on_job_failed(
        failed_job["id"],
        "err_generic|HTTP Error 403: Forbidden",
    )
    assert failed_job["status"] == "failed"
    assert window.retry_failed_btn.isEnabled()
    window.retry_failed_jobs()
    assert failed_job["status"] == "pending"
    assert DownloadWorker._is_retryable_error("HTTP Error 403: Forbidden")
    assert not DownloadWorker._is_retryable_error("This video is private")

    # Real process-isolation regression: a hard child-process crash and an
    # unsupported URL must fail only those rows and the sequential queue must
    # continue to the following item while the GUI process remains alive.
    iso_settings = QSettings(ORG_NAME, APP_NAME + "-IsolationSmokeTest")
    iso_settings.clear()
    iso = MainWindow(settings=iso_settings)
    iso.run_config = {
        "folder": str(Path.home() / "Downloads"),
        "quality": "Best quality",
        "playlist": False,
        "concurrency": 1,
    }
    iso.queue_running = False
    iso.add_urls(
        "https://example.com/ci-crash\n"
        "https://example.com/ci-unsupported\n"
        "https://example.com/ci-success"
    )

    original_request = iso._make_worker_request

    def ci_request(job):
        request = original_request(job)
        if job["url"].endswith("ci-crash"):
            request["_test_mode"] = "crash"
        elif job["url"].endswith("ci-unsupported"):
            request["_test_mode"] = "unsupported"
        else:
            request["_test_mode"] = "success"
        return request

    iso._make_worker_request = ci_request
    iso.queue_running = True
    iso._pump_queue()

    deadline = time.time() + 20
    while (iso.active_jobs or iso.queue_running) and time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)

    assert not iso.active_jobs
    assert not iso.queue_running
    assert [job["status"] for job in iso.jobs] == ["failed", "failed", "done"]
    assert "unexpectedly" in iso.jobs[0]["error"].lower() or "異常" in iso.jobs[0]["error"]
    assert "unsupported" in iso.jobs[1]["error"].lower()

    iso.close()
    iso_settings.clear()
    window.close()
    settings.clear()


def main():
    if "--download-worker" in sys.argv:
        index = sys.argv.index("--download-worker")
        if len(sys.argv) <= index + 2:
            return 2
        return download_worker_main(sys.argv[index + 1], sys.argv[index + 2])

    install_exception_hook()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    if "--smoke-test" in sys.argv:
        smoke_test(app)
        return 0

    window = MainWindow()
    window.show()

    # Repaint on live OS theme changes while in "system" mode.
    def on_scheme_changed(_):
        if window.theme_mode == "system":
            window.apply_theme()
    try:
        QGuiApplication.styleHints().colorSchemeChanged.connect(on_scheme_changed)
    except Exception:
        pass

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
