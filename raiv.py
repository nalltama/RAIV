from __future__ import annotations

import ctypes
import json
import locale
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass, field
from functools import cmp_to_key
from pathlib import Path, PurePosixPath

try:
    from PySide6.QtCore import QObject, QPoint, QRect, QSize, Qt, QEvent, QTimer, Signal
    from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap, QTransform
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListView,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QSpinBox,
        QSplitter,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise SystemExit(
        "PySide6 が見つかりません。install_support.bat を実行してください。"
    ) from exc

try:
    import rarfile
except ImportError:
    rarfile = None

try:
    import py7zr
except ImportError:
    py7zr = None

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None


APP_NAME = "Realtime AI Image Viewer"
APP_SHORT_NAME = "RAIV"
APP_ID = "RealtimeAIImageViewer.RAIV"
APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "setting.json"
APP_ICON_ICO = APP_DIR / "assets" / "app_icon.ico"
APP_ICON_PNG = APP_DIR / "assets" / "app_icon.png"
CURVE_DIR = APP_DIR / "cur"
REALESRGAN_FIXED_SCALE = 4
BUNDLED_REALCUGAN_EXE = APP_DIR / "tools" / "realcugan-ncnn-vulkan" / "realcugan-ncnn-vulkan.exe"
BUNDLED_REALESRGAN_EXE = APP_DIR / "tools" / "realesrgan-ncnn-vulkan" / "realesrgan-ncnn-vulkan.exe"
LEGACY_REALCUGAN_TEMPLATE = 'realcugan-ncnn-vulkan.exe -i "{input}" -o "{output}" -s {scale} -n {denoise} -t {tile}'
DEFAULT_REALCUGAN_TEMPLATE = (
    f'"{BUNDLED_REALCUGAN_EXE}" -i "{{input}}" -o "{{output}}" -s {{scale}} -n {{denoise}} -t {{tile}}'
    if BUNDLED_REALCUGAN_EXE.exists()
    else LEGACY_REALCUGAN_TEMPLATE
)
LEGACY_REALESRGAN_TEMPLATE = 'realesrgan-ncnn-vulkan.exe -i "{input}" -o "{output}" -s {scale} -t {tile} -n {model}'
DEFAULT_REALESRGAN_TEMPLATE = (
    f'"{BUNDLED_REALESRGAN_EXE}" -i "{{input}}" -o "{{output}}" -s {{scale}} -t {{tile}} -n {{model}}'
    if BUNDLED_REALESRGAN_EXE.exists()
    else LEGACY_REALESRGAN_TEMPLATE
)
ENGINE_REALCUGAN = "realcugan"
ENGINE_REALESRGAN = "realesrgan"
ENGINE_LABELS = {
    ENGINE_REALCUGAN: "Real-CUGAN",
    ENGINE_REALESRGAN: "Real-ESRGAN",
}
REALESRGAN_MODELS = ["realesr-animevideov3", "realesrgan-x4plus", "realesrgan-x4plus-anime"]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
ARCHIVE_EXTENSIONS = {".zip", ".cbz", ".rar", ".cbr", ".7z", ".cb7"}
TEMP_ARCHIVE_PREFIX = "realcugan_qt_archive_"
TEMP_WORK_PREFIX = "realcugan_qt_work_"
TEMP_OUTPUT_PREFIX = "realcugan_"
TEMP_LOCK_FILE = "viewer.lock"
SINGLE_INSTANCE_MUTEX_NAME = "Local\\RealtimeAIImageViewer_RAIV_SingleInstance"
BORDERLESS_FULLSCREEN_OVERSCAN = 1
FORM_LABEL_WIDTH = 132
MAX_DISPLAY_SCALE = 5.0
PREFETCH_DEBOUNCE_MS = 80
THUMBNAIL_TRIGGER_MARGIN = 48
THUMBNAIL_MIN_HEIGHT = 96
THUMBNAIL_MAX_HEIGHT = 320
THUMBNAIL_RESIZE_GRIP = 10
THUMBNAIL_HIDE_GRACE_SEC = 0.45
THUMBNAIL_HIDE_MARGIN = 28
THUMBNAIL_HIDE_DELAY_MS = 220
SIDE_PANEL_HIDE_GRACE_SEC = 0.45
SIDE_PANEL_HIDE_MARGIN = 36
SIDE_PANEL_HIDE_DELAY_MS = 220
PROFILE_UPDATE_INTERVAL_MS = 500
RESAMPLE_ALGORITHMS = {
    "lanczos3": "Lanczos3",
    "lanczos4": "Lanczos4",
    "bicubic": "Bicubic",
    "area": "Area",
}
DEFAULT_RESAMPLE_ALGORITHM = "bicubic"
MODIFIER_MASK = (
    Qt.ControlModifier.value
    | Qt.ShiftModifier.value
    | Qt.AltModifier.value
)
ACTION_DEFS = [
    ("open_image", "画像を開く"),
    ("open_folder", "フォルダを開く"),
    ("next_page", "次ページ送り"),
    ("previous_page", "前ページ送り"),
    ("last_page", "最終ページ飛ばし"),
    ("first_page", "最初ページ飛ばし"),
    ("toggle_fullscreen", "全画面表示/解除"),
    ("toggle_thumbnail_panel", "サムネイル固定/自動表示"),
    ("toggle_side_panel", "右ペイン固定/自動表示"),
    ("toggle_compare", "比較モードオン/オフ"),
    ("toggle_dual_page", "見開き表示オン/オフ"),
    ("dual_page_shift_forward", "1ページ送り(見開き表示時)"),
    ("dual_page_shift_backward", "1ページ戻し(見開き表示時)"),
    ("toggle_tone_curve", "トーンカーブ補正オン/オフ"),
    ("actual_size", "等倍表示"),
    ("fit_view", "画面フィット表示"),
    ("rotate_right", "画像右回転"),
    ("rotate_left", "画像左回転"),
    ("flip_horizontal", "画像左右反転"),
    ("flip_vertical", "画像上下反転"),
]


def natural_sort_fallback_key(value: str) -> tuple:
    parts = re.split(r"(\d+)", value.casefold().replace("/", "\\"))
    key = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part), len(part)))
        else:
            key.append((1, part))
    return tuple(key)


def windows_logical_compare(left: str, right: str) -> int:
    left_text = str(left).replace("/", "\\")
    right_text = str(right).replace("/", "\\")
    if os.name == "nt":
        try:
            return int(ctypes.windll.shlwapi.StrCmpLogicalW(left_text, right_text))
        except Exception:
            pass
    left_key = natural_sort_fallback_key(left_text)
    right_key = natural_sort_fallback_key(right_text)
    return (left_key > right_key) - (left_key < right_key)


def windows_logical_sorted(items, text_func):
    return sorted(items, key=cmp_to_key(lambda left, right: windows_logical_compare(text_func(left), text_func(right))))

UI_TEXT_EN = {
    "画像を開く": "Open image",
    "フォルダを開く": "Open folder",
    "次ページ送り": "Next page",
    "前ページ送り": "Previous page",
    "最終ページ飛ばし": "Jump to last page",
    "最初ページ飛ばし": "Jump to first page",
    "全画面表示/解除": "Toggle fullscreen",
    "サムネイル固定/自動表示": "Thumbnail pinned/auto",
    "右ペイン固定/自動表示": "Right panel pinned/auto",
    "比較モードオン/オフ": "Toggle compare mode",
    "見開き表示オン/オフ": "Toggle spread view",
    "1ページ送り(見開き表示時)": "Shift one page forward (spread view)",
    "1ページ戻し(見開き表示時)": "Shift one page backward (spread view)",
    "トーンカーブ補正オン/オフ": "Toggle tone curve adjustment",
    "等倍表示": "Actual size",
    "画面フィット表示": "Fit to window",
    "画像右回転": "Rotate right",
    "画像左回転": "Rotate left",
    "画像左右反転": "Flip horizontal",
    "画像上下反転": "Flip vertical",
    "設定": "Settings",
    "固定": "Pin",
    "固定中": "Pinned",
    "自動表示": "Auto",
    "エンジン設定": "Engine",
    "全般": "General",
    "画像調整": "Image Adjustment",
    "その他": "Other",
    "キーコンフィグ": "Key Config",
    "エンジン": "Engine",
    "倍率": "Scale",
    "ノイズ": "Denoise",
    "Real-ESRGANモデル": "Real-ESRGAN model",
    "ノイズ: Real-CUGAN専用。-1 はノイズ除去なし。0/1/2/3 は数値が大きいほど強く除去します。": "Denoise: Real-CUGAN only. -1 disables denoising. 0/1/2/3 remove noise more strongly as the value increases.",
    "Real-ESRGANはノイズ値を使わず、モデルで画風や復元傾向を選びます。": "Real-ESRGAN does not use the denoise value. Choose a model to change image style and restoration behavior.",
    "realesr-animevideov3: アニメ/イラスト向けの軽量標準モデル。 realesrgan-x4plus: 写真や一般画像向け。 realesrgan-x4plus-anime: アニメ/イラスト向けのx4plus派生モデル。 RAIVではReal-ESRGAN選択中、倍率は4倍固定として処理します。": "realesr-animevideov3: lightweight standard model for anime/illustration. realesrgan-x4plus: for photos and general images. realesrgan-x4plus-anime: x4plus-derived model for anime/illustration. In RAIV, Real-ESRGAN is processed at fixed 4x scale.",
    "tile: 0 は自動。小さめの値はGPUメモリ使用量を抑えますが、遅くなることがあります。": "tile: 0 is automatic. Smaller values can reduce GPU memory usage but may be slower.",
    "エンジン先読み": "Engine prefetch",
    "選択中の拡大エンジンで処理を先に進める枚数。大きいほど待ち時間を減らせますが、GPU負荷と一時ファイル作成が増えます。": "Number of images to process ahead with the selected engine. Higher values reduce waiting but increase GPU load and temporary files.",
    "縦サイズが閾値以上なら拡大処理しない": "Skip processing when height is at or above threshold",
    "縦サイズ閾値(px)": "Height threshold (px)",
    "モニタ解像度以上の画像をさらに拡大しても表示上の効果は小さく、処理時間とメモリ使用量が増えます。普段使うモニタの縦解像度に合わせる設定が目安です。": "Upscaling images already above monitor resolution often has little visible benefit and increases processing time and memory usage. Set this near your usual monitor height.",
    "拡大結果を倍率フォルダに保存": "Save processed results to scale folder",
    "倍率フォルダがあれば表示に使う": "Use scale folder when available",
    "アーカイブ表示中は保存先フォルダがないため、倍率フォルダ保存と倍率フォルダ読み込みは無効です。": "Scale-folder saving/loading is disabled while viewing archives because there is no output folder.",
    "再実行": "Run again",
    "コマンドテンプレート": "Command template",
    "エンジンexeを選択": "Select engine exe",
    "使用できる置換: {input} {output} {scale} {denoise} {tile} {model}": "Available placeholders: {input} {output} {scale} {denoise} {tile} {model}",
    "次回起動時に古い一時ファイルを削除": "Delete old temporary files on next startup",
    "アプリの二重起動を禁止する": "Prevent multiple app instances",
    "表示言語": "Language",
    "ビューアー先読み": "Viewer prefetch",
    "表示用に画像をメモリへ先読みする枚数。大きいほどページ送りは速くなりますが、メモリ使用量が増えます。": "Number of images to preload into memory for display. Higher values make page navigation faster but use more memory.",
    "拡大縮小を高品質に補完する": "Use high-quality scaling",
    "表示リサンプル方式": "Display resampling method",
    "原寸と異なる表示サイズの画像を、よりきれいに見えるよう作成して保持します。オフにすると標準の高速表示になります。": "Creates and keeps high-quality display-size images when shown at a different size. Turn off for standard fast display.",
    "Lanczos3: 精細で標準的。Lanczos4: より鋭いがリンギングが出ることがあります。Bicubic: やや柔らかく自然。Area: 大きく縮小する時に安定し、ジャギーを抑えやすい方式です。": "Lanczos3: sharp and standard. Lanczos4: sharper but may introduce ringing. Bicubic: softer and natural. Area: stable for large reductions and helps reduce jaggies.",
    "Lanczos4はOpenCVがある環境ではLanczos4、ない環境ではLanczos3相当で処理します。": "Lanczos4 uses OpenCV when available; otherwise it falls back to Lanczos3-equivalent processing.",
    "選択": "Select",
    "背景色": "Background color",
    "見開き表示": "Spread view",
    "見開き表示時は比較モードは無効です。": "Compare mode is disabled while using spread view.",
    "横長画像は1枚表示にする": "Show landscape images as a single page",
    "横長画像を既に見開きのページとして扱い、隣の画像と並べずに表示します。": "Treat landscape images as already-spread pages and do not pair them with the next image.",
    "比較モード": "Compare mode",
    "比較スライダー": "Compare slider",
    "中央に戻す": "Center",
    "境界線色": "Divider color",
    "境界線の太さ(px)": "Divider width (px)",
    "比較の左右を入れ替える": "Swap compare sides",
    "比較中はShift+ドラッグで境界線を動かす": "Use Shift+drag to move divider in compare mode",
    "ズーム: 100%": "Zoom: 100%",
    "表示を中央へリセット": "Reset view to center",
    "ページ送り間隔(ms)": "Page interval (ms)",
    "ホイールやキー操作で連続ページ送りする時の間隔。0 は最短です。": "Interval used for continuous page navigation by wheel or key. 0 is the shortest.",
    "ページ位置": "Page position",
    "ページ位置スライダーの左右を入れ替える（右綴じにする）": "Reverse page position slider (right-to-left reading)",
    "オンにすると、ページ位置スライダーとサムネイル列の左右方向が連動して入れ替わります。": "When enabled, the page position slider and thumbnail strip directions are reversed together.",
    "画面下部にサムネイルを表示する": "Show thumbnails at bottom",
    "オフにするとサムネイル生成処理も停止します。大量の画像を開く時に、初期表示や先読みを軽くできます。": "Turning this off also stops thumbnail generation, which can make initial display and prefetch lighter for large folders.",
    "サムネイル列を固定表示する": "Pin thumbnail strip",
    "最後/最初でページ送りしたら反対側へ移動": "Wrap around at first/last page",
    "ページ送り時にズームと表示位置を維持": "Preserve zoom and position when changing pages",
    "マウス横スクロールでページ送り": "Use horizontal mouse wheel for page navigation",
    "横スクロールのページ送り方向を反転": "Reverse horizontal wheel direction",
    "全画面表示時にマウスカーソルを非表示": "Hide mouse cursor in fullscreen",
    "画像またはフォルダ/アーカイブをドロップしてください": "Drop an image, folder, or archive",
    "トーンカーブ補正を使う": "Use tone curve adjustment",
    "GIMP .curファイルを使い、輝度に応じてRGBを割り当てます。モノクロ漫画を疑似4色刷りのように表示できます。": "Uses a GIMP .cur file to map luminance to RGB, making monochrome manga look like pseudo four-color printing.",
    "トーンカーブ": "Tone curve",
    "再読み込み": "Reload",
    "フォルダ": "Folder",
    "curフォルダを開く": "Open cur folder",
    "チャンネル": "Channel",
    "保存": "Save",
    "選択中の曲線をドラッグして調整できます。保存するとcurフォルダへGIMP旧形式.curとして出力します。": "Drag the selected curve to adjust it. Save writes a GIMP legacy-format .cur file into the cur folder.",
    "値": "Value",
    "赤": "Red",
    "緑": "Green",
    "青": "Blue",
    "アルファ": "Alpha",
    "状態": "Status",
    "ログを表示": "Show log",
    "拡大前メモリ読込": "Original memory load",
    "拡大画像生成": "Processed image generation",
    "拡大後メモリ読込": "Processed memory load",
    "表示用QPixmap": "Display QPixmap",
    "ログ": "Log",
    "内部プロファイリングを表示": "Show internal profiling",
    "設定値をクリックすると割当を変更できます。Escを入力すると未割当に戻ります。Spaceは次ページ、Backspaceは前ページとして固定です。": "Click a binding value to change it. Press Esc to clear it. Space is fixed to next page and Backspace is fixed to previous page.",
    "機能": "Action",
    "キーボード": "Keyboard",
    "マウス": "Mouse",
    "キーコンフィグを初期値に戻す": "Reset key config to defaults",
    "重複しているため、この割当は無効です。": "This binding is duplicated and disabled.",
    "未割当": "Unassigned",
    "左クリック": "Left click",
    "右クリック": "Right click",
    "ホイールクリック": "Middle click",
    "戻るボタン": "Back button",
    "進むボタン": "Forward button",
    "左ダブルクリック": "Left double click",
    "右ダブルクリック": "Right double click",
    "ホイールダブルクリック": "Middle double click",
    "戻るボタンダブルクリック": "Back button double click",
    "進むボタンダブルクリック": "Forward button double click",
    "現在": "Current",
    "キャンセル": "Cancel",
    "入力待ち... Escで解除": "Waiting for input... Esc clears",
    "ここをクリック後、設定するキーを押下": "Click here, then press a key",
    "ここをクリック後、設定するマウスボタンを押下": "Click here, then press a mouse button",
    "ダブルクリック": "Double click",
    "画像ファイル、画像フォルダ、またはアーカイブを指定してください。": "Please select an image file, image folder, or archive.",
    "対応画像がありません。": "No supported images found.",
    "このアーカイブには対応画像がありません。": "This archive contains no supported images.",
}

UI_TEXT_JA = {value: key for key, value in UI_TEXT_EN.items()}


def key_binding(key: Qt.Key | int, modifiers: int = 0) -> dict[str, int]:
    return {"key": int(key), "modifiers": int(modifiers) & MODIFIER_MASK}


def mouse_binding(button: Qt.MouseButton | int, modifiers: int = 0, double: bool = False) -> dict[str, int | bool]:
    return {
        "button": int(button.value if hasattr(button, "value") else button),
        "modifiers": int(modifiers) & MODIFIER_MASK,
        "double": bool(double),
    }


def default_key_bindings() -> dict[str, dict[str, dict | None]]:
    return {
        "open_image": {"keyboard": key_binding(Qt.Key_O), "mouse": None},
        "open_folder": {"keyboard": key_binding(Qt.Key_F), "mouse": None},
        "next_page": {"keyboard": key_binding(Qt.Key_Left), "mouse": None},
        "previous_page": {"keyboard": key_binding(Qt.Key_Right), "mouse": None},
        "last_page": {"keyboard": None, "mouse": mouse_binding(Qt.ForwardButton)},
        "first_page": {"keyboard": None, "mouse": mouse_binding(Qt.BackButton)},
        "toggle_fullscreen": {"keyboard": None, "mouse": mouse_binding(Qt.MiddleButton)},
        "toggle_thumbnail_panel": {"keyboard": key_binding(Qt.Key_F3), "mouse": None},
        "toggle_side_panel": {"keyboard": key_binding(Qt.Key_F4), "mouse": None},
        "toggle_compare": {"keyboard": None, "mouse": None},
        "toggle_dual_page": {"keyboard": key_binding(Qt.Key_W), "mouse": None},
        "dual_page_shift_forward": {"keyboard": key_binding(Qt.Key_Q), "mouse": None},
        "dual_page_shift_backward": {"keyboard": key_binding(Qt.Key_E), "mouse": None},
        "toggle_tone_curve": {"keyboard": key_binding(Qt.Key_T), "mouse": None},
        "actual_size": {"keyboard": None, "mouse": mouse_binding(Qt.RightButton, double=True)},
        "fit_view": {"keyboard": None, "mouse": mouse_binding(Qt.LeftButton, double=True)},
        "rotate_right": {"keyboard": key_binding(Qt.Key_R), "mouse": None},
        "rotate_left": {"keyboard": key_binding(Qt.Key_L), "mouse": None},
        "flip_horizontal": {"keyboard": key_binding(Qt.Key_H), "mouse": None},
        "flip_vertical": {"keyboard": key_binding(Qt.Key_V), "mouse": None},
    }


@dataclass
class AppConfig:
    engine: str = ENGINE_REALCUGAN
    command_template: str = DEFAULT_REALCUGAN_TEMPLATE
    realcugan_command_template: str = DEFAULT_REALCUGAN_TEMPLATE
    realesrgan_command_template: str = DEFAULT_REALESRGAN_TEMPLATE
    scale: int = 2
    denoise: int = 0
    tile: int = 0
    realesrgan_model: str = "realesr-animevideov3"
    realcugan_prefetch_count: int = 10
    viewer_prefetch_count: int = 20
    save_upscaled_to_scale_folder: bool = False
    use_scale_folder_cache: bool = True
    skip_realcugan_for_tall_images: bool = True
    skip_realcugan_height_threshold: int = 2160
    background_color: str = "#000000"
    cpu_resample_cache_enabled: bool = True
    cpu_resample_algorithm: str = DEFAULT_RESAMPLE_ALGORITHM
    compare_enabled: bool = False
    compare_split: int = 500
    compare_line_color: str = "#ffffff"
    compare_line_width: int = 2
    compare_swap_sides: bool = False
    compare_shift_drag_moves_boundary: bool = False
    dual_page_enabled: bool = False
    dual_page_landscape_single: bool = True
    tone_curve_enabled: bool = False
    tone_curve_file: str = ""
    hide_cursor_in_fullscreen: bool = False
    show_log_panel: bool = False
    show_profile_panel: bool = False
    ui_language: str = "ja"
    thumbnail_enabled: bool = True
    thumbnail_pinned: bool = False
    thumbnail_size: int = 96
    thumbnail_height: int = 142
    horizontal_wheel_navigation: bool = False
    horizontal_wheel_inverted: bool = False
    wrap_page_navigation: bool = False
    preserve_view_on_page_navigation: bool = False
    invert_page_position_slider: bool = True
    page_scroll_interval_ms: int = 1
    arrow_right_next: bool = True
    key_bindings: dict[str, dict[str, dict | None]] = field(default_factory=default_key_bindings)
    cleanup_temp_on_start: bool = False
    single_instance_enabled: bool = False
    settings_tab: str = "realcugan"
    window_rect: list[int] | None = None
    window_maximized: bool = False
    window_geometry: str = ""
    side_panel_visible: bool = True
    side_panel_pinned: bool = True
    side_panel_width: int = 460
    splitter_sizes: list[int] | None = None
    last_dir: str = ""


def set_process_app_user_model_id() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def enable_high_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def command_executable_exists(command: str) -> bool:
    stripped = command.strip()
    if not stripped:
        return False
    if stripped.startswith('"'):
        end = stripped.find('"', 1)
        token = stripped[1:end] if end > 1 else ""
    else:
        token = stripped.split(maxsplit=1)[0]
    if not token:
        return False
    exe_path = Path(os.path.expandvars(token))
    if exe_path.is_absolute():
        return exe_path.is_file()
    return (APP_DIR / exe_path).is_file() or shutil.which(token) is not None


def normalize_key_bindings(value: object) -> dict[str, dict[str, dict | None]]:
    defaults = default_key_bindings()
    if not isinstance(value, dict):
        return defaults
    normalized = defaults
    for action_id, parts in value.items():
        if action_id not in normalized or not isinstance(parts, dict):
            continue
        for kind in ("keyboard", "mouse"):
            binding = parts.get(kind)
            if binding is None:
                normalized[action_id][kind] = None
                continue
            if not isinstance(binding, dict):
                continue
            if kind == "keyboard":
                key = binding.get("key")
                if isinstance(key, int) and key > 0:
                    normalized[action_id][kind] = {
                        "key": key,
                        "modifiers": int(binding.get("modifiers", 0)) & MODIFIER_MASK,
                    }
            else:
                button = binding.get("button")
                if isinstance(button, int) and button > 0:
                    normalized[action_id][kind] = {
                        "button": button,
                        "modifiers": int(binding.get("modifiers", 0)) & MODIFIER_MASK,
                        "double": bool(binding.get("double", False)),
                    }
    return normalized


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        return AppConfig()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        config = AppConfig(**{**asdict(AppConfig()), **data})
        if config.command_template == LEGACY_REALCUGAN_TEMPLATE and BUNDLED_REALCUGAN_EXE.exists():
            config.command_template = DEFAULT_REALCUGAN_TEMPLATE
        if config.realcugan_command_template in {LEGACY_REALCUGAN_TEMPLATE, ""} and BUNDLED_REALCUGAN_EXE.exists():
            config.realcugan_command_template = DEFAULT_REALCUGAN_TEMPLATE
        if config.realesrgan_command_template in {LEGACY_REALESRGAN_TEMPLATE, ""} and BUNDLED_REALESRGAN_EXE.exists():
            config.realesrgan_command_template = DEFAULT_REALESRGAN_TEMPLATE
        if "realcugan_command_template" not in data:
            config.realcugan_command_template = config.command_template or DEFAULT_REALCUGAN_TEMPLATE
        if config.engine not in ENGINE_LABELS:
            config.engine = ENGINE_REALCUGAN
        if config.realesrgan_model not in REALESRGAN_MODELS:
            config.realesrgan_model = REALESRGAN_MODELS[0]
        if config.cpu_resample_algorithm not in RESAMPLE_ALGORITHMS:
            config.cpu_resample_algorithm = DEFAULT_RESAMPLE_ALGORITHM
        if config.ui_language not in {"ja", "en"}:
            config.ui_language = "ja"
        config.key_bindings = normalize_key_bindings(getattr(config, "key_bindings", None))
        if BUNDLED_REALCUGAN_EXE.exists() and not command_executable_exists(config.realcugan_command_template):
            config.realcugan_command_template = DEFAULT_REALCUGAN_TEMPLATE
        if BUNDLED_REALESRGAN_EXE.exists() and not command_executable_exists(config.realesrgan_command_template):
            config.realesrgan_command_template = DEFAULT_REALESRGAN_TEMPLATE
        if "compare_split" in data and 0 <= int(data.get("compare_split", 500)) <= 100:
            config.compare_split = int(data["compare_split"]) * 10
        return config
    except Exception:
        return AppConfig()


def save_config(config: AppConfig) -> None:
    CONFIG_PATH.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")


def acquire_single_instance_mutex_if_needed() -> object | None:
    config = load_config()
    if not config.single_instance_enabled or os.name != "nt":
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
    if not handle:
        return None
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        raise SystemExit(0)
    return handle


def release_single_instance_mutex(handle: object | None) -> None:
    if handle and os.name == "nt":
        try:
            ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass


def modifier_value(modifiers) -> int:
    return int(modifiers.value if hasattr(modifiers, "value") else modifiers) & MODIFIER_MASK


def binding_modifiers_text(modifiers: int) -> list[str]:
    names = []
    if modifiers & Qt.ControlModifier.value:
        names.append("Ctrl")
    if modifiers & Qt.ShiftModifier.value:
        names.append("Shift")
    if modifiers & Qt.AltModifier.value:
        names.append("Alt")
    return names


def key_binding_text(binding: dict | None) -> str:
    if not binding:
        return "未割当"
    parts = binding_modifiers_text(int(binding.get("modifiers", 0)))
    key = int(binding.get("key", 0))
    key_text = QKeySequence(key).toString(QKeySequence.NativeText) if key else ""
    parts.append(key_text or f"Key {key}")
    return "+".join(parts)


def mouse_binding_text(binding: dict | None) -> str:
    if not binding:
        return "未割当"
    parts = binding_modifiers_text(int(binding.get("modifiers", 0)))
    button = int(binding.get("button", 0))
    names = {
        Qt.LeftButton.value: "左クリック",
        Qt.RightButton.value: "右クリック",
        Qt.MiddleButton.value: "ホイールクリック",
        Qt.BackButton.value: "戻るボタン",
        Qt.ForwardButton.value: "進むボタン",
    }
    button_text = names.get(button, f"ボタン{button}")
    if binding.get("double"):
        button_text = button_text.replace("クリック", "ダブルクリック")
        if "ダブルクリック" not in button_text:
            button_text = f"{button_text}ダブルクリック"
    parts.append(button_text)
    return "+".join(parts)


def keyboard_signature(binding: dict | None) -> tuple[int, int] | None:
    if not binding:
        return None
    key = int(binding.get("key", 0))
    if key <= 0:
        return None
    return key, int(binding.get("modifiers", 0)) & MODIFIER_MASK


def mouse_signature(binding: dict | None) -> tuple[int, int, bool] | None:
    if not binding:
        return None
    button = int(binding.get("button", 0))
    if button <= 0:
        return None
    return button, int(binding.get("modifiers", 0)) & MODIFIER_MASK, bool(binding.get("double", False))


def duplicate_binding_signatures(bindings: dict[str, dict[str, dict | None]], kind: str) -> set[tuple]:
    seen: dict[tuple, str] = {}
    duplicates: set[tuple] = set()
    if kind == "keyboard":
        # Space/Backspace are fixed operations, so configurable bindings cannot use them.
        seen[(int(Qt.Key_Space), 0)] = "__fixed_space__"
        seen[(int(Qt.Key_Backspace), 0)] = "__fixed_backspace__"
        signature_func = keyboard_signature
    else:
        signature_func = mouse_signature
    for action_id, action_bindings in bindings.items():
        if not isinstance(action_bindings, dict):
            continue
        signature = signature_func(action_bindings.get(kind))
        if signature is None:
            continue
        if signature in seen:
            duplicates.add(signature)
        else:
            seen[signature] = action_id
    return duplicates


CURVE_CHANNELS = ("value", "red", "green", "blue", "alpha")
CURVE_CHANNEL_LABELS = {
    "value": "値",
    "red": "赤",
    "green": "緑",
    "blue": "青",
    "alpha": "アルファ",
}


@dataclass
class ToneCurve:
    name: str = ""
    path: str = ""
    points: dict[str, list[tuple[int, int]]] = field(default_factory=dict)

    def normalized_points(self, channel: str) -> list[tuple[int, int]]:
        points = [(max(0, min(255, int(x))), max(0, min(255, int(y)))) for x, y in self.points.get(channel, []) if x >= 0 and y >= 0]
        if not points:
            points = [(0, 0), (255, 255)]
        if all(x != 0 for x, _y in points):
            points.append((0, 0))
        if all(x != 255 for x, _y in points):
            points.append((255, 255))
        return sorted(set(points), key=lambda item: item[0])

    def lut(self, channel: str) -> list[int]:
        points = self.normalized_points(channel)
        output = [0] * 256
        for index, (x0, y0) in enumerate(points[:-1]):
            x1, y1 = points[index + 1]
            if x1 <= x0:
                continue
            for x in range(max(0, x0), min(255, x1) + 1):
                ratio = (x - x0) / (x1 - x0)
                output[x] = max(0, min(255, round(y0 + (y1 - y0) * ratio)))
        first_x, first_y = points[0]
        last_x, last_y = points[-1]
        for x in range(0, max(0, first_x)):
            output[x] = first_y
        for x in range(min(255, last_x), 256):
            output[x] = last_y
        return output

    def copy(self) -> "ToneCurve":
        return ToneCurve(self.name, self.path, {channel: list(points) for channel, points in self.points.items()})


def default_tone_curve(name: str = "linear") -> ToneCurve:
    return ToneCurve(name=name, points={channel: [(0, 0), (255, 255)] for channel in CURVE_CHANNELS})


def parse_legacy_cur(path: Path, text: str) -> ToneCurve:
    curve = default_tone_curve(path.stem)
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    for channel, line in zip(CURVE_CHANNELS, lines):
        values = [int(float(value)) for value in line.split()]
        points: list[tuple[int, int]] = []
        for index in range(0, len(values) - 1, 2):
            x, y = values[index], values[index + 1]
            if x >= 0 and y >= 0:
                points.append((x, y))
        if points:
            curve.points[channel] = points
    curve.path = str(path)
    return curve


def parse_modern_cur(path: Path, text: str) -> ToneCurve:
    curve = default_tone_curve(path.stem)
    for channel in CURVE_CHANNELS:
        match = re.search(rf"\(channel\s+{re.escape(channel)}\)(.*?)(?=\n\(channel\s+|\Z)", text, re.S)
        if not match:
            continue
        block = match.group(1)
        points_match = re.search(r"\(points\s+(\d+)\s+([^)]*)\)", block, re.S)
        if points_match:
            numbers = [float(value) for value in points_match.group(2).split()]
            points: list[tuple[int, int]] = []
            for index in range(0, len(numbers) - 1, 2):
                x, y = numbers[index], numbers[index + 1]
                if x >= 0 and y >= 0:
                    points.append((round(x * 255), round(y * 255)))
            if points:
                curve.points[channel] = points
    curve.path = str(path)
    return curve


def load_tone_curve(path: Path) -> ToneCurve | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "GIMP curves tool settings" in text:
            return parse_modern_cur(path, text)
        if "GIMP Curves File" in text:
            return parse_legacy_cur(path, text)
    except Exception:
        return None
    return None


def save_legacy_cur(path: Path, curve: ToneCurve) -> None:
    lines = ["# GIMP Curves File"]
    for channel in CURVE_CHANNELS:
        points = curve.normalized_points(channel)
        pairs: list[str] = []
        for index in range(17):
            if index < len(points):
                x, y = points[index]
                pairs.extend([str(x), str(y)])
            else:
                pairs.extend(["-1", "-1"])
        lines.append(" ".join(pairs) + " ")
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


class KeyBindingDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, kind: str, binding: dict | None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.binding = dict(binding) if binding else None
        self.capturing = False
        self.language = parent.ui_language() if hasattr(parent, "ui_language") else "ja"
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        self.capture_button = QPushButton(self.dialog_text("ここをクリック後、設定するキーを押下" if kind == "keyboard" else "ここをクリック後、設定するマウスボタンを押下"))
        self.capture_button.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_button)
        mods = QHBoxLayout()
        self.ctrl_check = QCheckBox("Ctrl")
        self.shift_check = QCheckBox("Shift")
        self.alt_check = QCheckBox("Alt")
        for checkbox in (self.ctrl_check, self.shift_check, self.alt_check):
            checkbox.stateChanged.connect(self.on_option_changed)
            mods.addWidget(checkbox)
        mods.addStretch(1)
        layout.addLayout(mods)
        self.double_check = QCheckBox(self.dialog_text("ダブルクリック"))
        self.double_check.stateChanged.connect(self.on_option_changed)
        if kind == "mouse":
            layout.addWidget(self.double_check)
        self.preview_label = QLabel()
        layout.addWidget(self.preview_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("OK")
        buttons.button(QDialogButtonBox.Cancel).setText(self.dialog_text("キャンセル"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.load_binding(binding)

    def dialog_text(self, text: str) -> str:
        return UI_TEXT_EN.get(text, text) if self.language == "en" else UI_TEXT_JA.get(text, text)

    def load_binding(self, binding: dict | None) -> None:
        modifiers = int(binding.get("modifiers", 0)) if binding else 0
        self.ctrl_check.setChecked(bool(modifiers & Qt.ControlModifier.value))
        self.shift_check.setChecked(bool(modifiers & Qt.ShiftModifier.value))
        self.alt_check.setChecked(bool(modifiers & Qt.AltModifier.value))
        if self.kind == "mouse":
            self.double_check.setChecked(bool(binding.get("double", False)) if binding else False)
        self.update_preview()

    def selected_modifiers(self) -> int:
        modifiers = 0
        if self.ctrl_check.isChecked():
            modifiers |= Qt.ControlModifier.value
        if self.shift_check.isChecked():
            modifiers |= Qt.ShiftModifier.value
        if self.alt_check.isChecked():
            modifiers |= Qt.AltModifier.value
        return modifiers

    def start_capture(self) -> None:
        self.capturing = True
        self.capture_button.setText(self.dialog_text("入力待ち... Escで解除"))
        self.capture_button.setFocus()
        if self.kind == "keyboard":
            self.grabKeyboard()
        else:
            self.grabMouse()

    def on_option_changed(self) -> None:
        if self.binding:
            self.binding["modifiers"] = self.selected_modifiers()
            if self.kind == "mouse":
                self.binding["double"] = self.double_check.isChecked()
        self.update_preview()

    def stop_capture(self) -> None:
        if self.kind == "keyboard":
            self.releaseKeyboard()
        else:
            self.releaseMouse()
        self.capturing = False
        self.capture_button.setText(self.dialog_text("ここをクリック後、設定するキーを押下" if self.kind == "keyboard" else "ここをクリック後、設定するマウスボタンを押下"))

    def keyPressEvent(self, event) -> None:
        if not self.capturing:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key == Qt.Key_Escape:
            self.binding = None
        elif key not in {Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta}:
            self.binding = key_binding(key, self.selected_modifiers())
        self.stop_capture()
        self.update_preview()

    def mousePressEvent(self, event) -> None:
        if not self.capturing or self.kind != "mouse":
            super().mousePressEvent(event)
            return
        self.binding = mouse_binding(event.button(), self.selected_modifiers(), self.double_check.isChecked())
        self.stop_capture()
        self.update_preview()

    def update_preview(self) -> None:
        text = key_binding_text(self.binding) if self.kind == "keyboard" else mouse_binding_text(self.binding)
        if self.language == "en":
            for source, target in UI_TEXT_EN.items():
                text = text.replace(source, target)
        self.preview_label.setText(f"{self.dialog_text('現在')}: {text}")


class ToneCurveGraph(QWidget):
    curveChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.curve = default_tone_curve()
        self.channel = "value"
        self.drag_index: int | None = None
        self.setMinimumHeight(220)
        self.setMinimumWidth(96)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMouseTracking(True)

    def set_curve(self, curve: ToneCurve | None) -> None:
        self.curve = curve.copy() if curve is not None else default_tone_curve()
        self.drag_index = None
        self.update()

    def set_channel(self, channel: str) -> None:
        if channel in CURVE_CHANNELS:
            self.channel = channel
            self.drag_index = None
            self.update()

    def graph_rect(self) -> QRect:
        rect = self.rect()
        left_margin = min(24, max(8, rect.width() // 6))
        right_margin = min(12, max(4, rect.width() // 12))
        return rect.adjusted(left_margin, 12, -right_margin, -24)

    def point_to_pos(self, point: tuple[int, int]) -> QPoint:
        rect = self.graph_rect()
        x = rect.left() + round(point[0] / 255 * rect.width())
        y = rect.bottom() - round(point[1] / 255 * rect.height())
        return QPoint(x, y)

    def pos_to_point(self, pos: QPoint) -> tuple[int, int]:
        rect = self.graph_rect()
        x = max(rect.left(), min(rect.right(), pos.x()))
        y = max(rect.top(), min(rect.bottom(), pos.y()))
        value_x = round((x - rect.left()) / max(1, rect.width()) * 255)
        value_y = round((rect.bottom() - y) / max(1, rect.height()) * 255)
        return max(0, min(255, value_x)), max(0, min(255, value_y))

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        rect = self.graph_rect()
        painter.setPen(QPen(self.palette().mid().color(), 1))
        painter.drawRect(rect)
        for index in range(1, 4):
            x = rect.left() + rect.width() * index // 4
            y = rect.top() + rect.height() * index // 4
            painter.drawLine(x, rect.top(), x, rect.bottom())
            painter.drawLine(rect.left(), y, rect.right(), y)
        color = {
            "value": QColor("#dddddd"),
            "red": QColor("#ff6060"),
            "green": QColor("#60d060"),
            "blue": QColor("#6090ff"),
            "alpha": QColor("#c080ff"),
        }.get(self.channel, QColor("#dddddd"))
        points = self.curve.normalized_points(self.channel)
        lut = self.curve.lut(self.channel)
        painter.setPen(QPen(color, 2))
        previous: QPoint | None = None
        for x in range(256):
            y = lut[x]
            current = self.point_to_pos((x, y))
            if previous is not None:
                painter.drawLine(previous, current)
            previous = current
        painter.setBrush(color)
        painter.setPen(QPen(Qt.black, 1))
        for point in points:
            pos = self.point_to_pos(point)
            painter.drawEllipse(pos, 4, 4)
        painter.end()

    def nearest_point_index(self, pos: QPoint) -> int | None:
        points = self.curve.normalized_points(self.channel)
        best_index: int | None = None
        best_distance = 999999
        for index, point in enumerate(points):
            point_pos = self.point_to_pos(point)
            distance = (point_pos.x() - pos.x()) ** 2 + (point_pos.y() - pos.y()) ** 2
            if distance < best_distance:
                best_index = index
                best_distance = distance
        return best_index if best_distance <= 18 ** 2 else None

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        points = self.curve.normalized_points(self.channel)
        index = self.nearest_point_index(pos)
        if index is None:
            points.append(self.pos_to_point(pos))
            points = sorted(points, key=lambda item: item[0])
            self.curve.points[self.channel] = points
            index = self.nearest_point_index(pos)
        self.drag_index = index
        self.update_drag_point(pos)

    def mouseMoveEvent(self, event) -> None:
        if self.drag_index is None:
            return
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        self.update_drag_point(pos)

    def mouseReleaseEvent(self, _event) -> None:
        self.drag_index = None

    def update_drag_point(self, pos: QPoint) -> None:
        points = self.curve.normalized_points(self.channel)
        if self.drag_index is None or self.drag_index < 0 or self.drag_index >= len(points):
            return
        x, y = self.pos_to_point(pos)
        if self.drag_index == 0:
            x = 0
        elif self.drag_index == len(points) - 1:
            x = 255
        else:
            previous_x = points[self.drag_index - 1][0] + 1
            next_x = points[self.drag_index + 1][0] - 1
            x = max(previous_x, min(next_x, x))
        points[self.drag_index] = (x, y)
        self.curve.points[self.channel] = points
        self.curveChanged.emit()
        self.update()


class AppSignals(QObject):
    process_started = Signal(str)
    process_done = Signal(object)
    folder_images_ready = Signal(object, object)
    prefetch_done = Signal(int, object, object, object, object)
    thumbnail_done = Signal(int, int, object)
    profile_event = Signal(str, float)


class GLImageView(QOpenGLWidget):
    pageRequested = Signal(int)
    firstRequested = Signal()
    lastRequested = Signal()
    zoomChanged = Signal(float)
    splitChanged = Signal(int)
    fullscreenRequested = Signal()
    resetRequested = Signal()
    actualSizeRequested = Signal()
    actionRequested = Signal(str)
    pixmapPrefetchProgress = Signal(int, int, int, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.background = QColor("#000000")
        self.raw_source_image = QImage()
        self.raw_processed_image = QImage()
        self.raw_secondary_source_image = QImage()
        self.raw_secondary_processed_image = QImage()
        self.source_image = QImage()
        self.processed_image = QImage()
        self.secondary_source_image = QImage()
        self.secondary_processed_image = QImage()
        self.source_pixmap = QPixmap()
        self.processed_pixmap = QPixmap()
        self.secondary_source_pixmap = QPixmap()
        self.secondary_processed_pixmap = QPixmap()
        self.display_rotation = 0
        self.display_flip_horizontal = False
        self.display_flip_vertical = False
        self.dual_page_enabled = False
        self.dual_page_reversed = False
        self.key_bindings = default_key_bindings()
        self.duplicate_mouse_bindings: set[tuple] = set()
        self.resample_cache: OrderedDict[tuple[int, int, int, int, str], QPixmap] = OrderedDict()
        self.pixmap_cache: OrderedDict[tuple[int, int, bool, bool], QPixmap] = OrderedDict()
        self.pixmap_cache_limit = 128
        self.pixmap_prefetch_queue: deque[tuple[object, QImage]] = deque()
        self.pixmap_prefetch_keys: set[object] = set()
        self.pixmap_prefetch_done_keys: set[object] = set()
        self.pixmap_prefetch_timer = QTimer(self)
        self.pixmap_prefetch_timer.setSingleShot(True)
        self.pixmap_prefetch_timer.timeout.connect(self.process_pixmap_prefetch)
        self.cpu_resample_cache_enabled = True
        self.cpu_resample_algorithm = DEFAULT_RESAMPLE_ALGORITHM
        self.resample_debounce_timer = QTimer(self)
        self.resample_debounce_timer.setSingleShot(True)
        self.resample_debounce_timer.timeout.connect(self.finish_interactive_resample_delay)
        self.resample_interaction_active = False
        self.resample_debounce_ms = 180
        self.compare_enabled = False
        self.compare_split = 500
        self.compare_line_color = QColor("#ffffff")
        self.compare_line_width = 2
        self.compare_swap_sides = False
        self.compare_shift_drag_moves_boundary = False
        self.tone_curve_enabled = False
        self.tone_curve_luts: dict[str, list[int]] | None = None
        self.horizontal_wheel_navigation = False
        self.horizontal_wheel_inverted = False
        self.zoom = 1.0
        self.offset = QPoint(0, 0)
        self.pan_start: QPoint | None = None
        self.zoom_drag_start: QPoint | None = None
        self.fit_scale_anchor: float | None = None
        self.fit_image_size: tuple[int, int] | None = None

    def set_images(
        self,
        source: QImage,
        processed: QImage | None,
        preserve_view: bool = False,
        secondary_source: QImage | None = None,
        secondary_processed: QImage | None = None,
        dual_page: bool = False,
        dual_page_reversed: bool = False,
    ) -> None:
        preserved_scale = self.current_scale() if preserve_view and not self.current_content_size().isEmpty() else None
        preserved_offset = QPoint(self.offset) if preserve_view else QPoint(0, 0)
        preserved_rotation = self.display_rotation if preserve_view else 0
        preserved_flip_horizontal = self.display_flip_horizontal if preserve_view else False
        preserved_flip_vertical = self.display_flip_vertical if preserve_view else False
        self.raw_source_image = source
        self.raw_processed_image = processed or QImage()
        self.raw_secondary_source_image = secondary_source or QImage()
        self.raw_secondary_processed_image = secondary_processed or QImage()
        self.dual_page_enabled = bool(dual_page)
        self.dual_page_reversed = bool(dual_page_reversed)
        self.display_rotation = preserved_rotation
        self.display_flip_horizontal = preserved_flip_horizontal
        self.display_flip_vertical = preserved_flip_vertical
        self.rebuild_display_images()
        self.clear_resample_cache()
        if preserve_view and preserved_scale is not None:
            content_size = self.current_content_size()
            if not content_size.isEmpty() and self.width() > 0 and self.height() > 0:
                self.fit_scale_anchor = min(self.width() / content_size.width(), self.height() / content_size.height())
                self.fit_image_size = (content_size.width(), content_size.height())
                self.zoom = self.clamp_zoom_factor(preserved_scale / max(self.fit_scale_anchor, 0.000001))
                self.offset = preserved_offset
                self.zoomChanged.emit(self.current_scale())
            else:
                self.reset_view(update=False)
        else:
            self.reset_view(update=False)
        self.update()

    def set_processed(self, processed: QImage | None, page_slot: int = 0) -> None:
        if page_slot == 1:
            self.raw_secondary_processed_image = processed or QImage()
        else:
            self.raw_processed_image = processed or QImage()
        self.rebuild_display_images()
        self.clear_resample_cache()
        self.update()

    def set_key_bindings(self, bindings: dict[str, dict[str, dict | None]]) -> None:
        self.key_bindings = normalize_key_bindings(bindings)
        self.duplicate_mouse_bindings = duplicate_binding_signatures(self.key_bindings, "mouse")

    def transformed_image(self, image: QImage) -> QImage:
        if image.isNull():
            return QImage()
        if self.display_rotation % 360 == 0 and not self.display_flip_horizontal and not self.display_flip_vertical:
            return image
        transform = QTransform()
        transform.scale(-1 if self.display_flip_horizontal else 1, -1 if self.display_flip_vertical else 1)
        transform.rotate(self.display_rotation)
        return image.transformed(transform, Qt.SmoothTransformation)

    def rebuild_display_images(self) -> None:
        self.source_image = self.transformed_image(self.apply_tone_curve_image(self.raw_source_image))
        self.processed_image = self.transformed_image(self.apply_tone_curve_image(self.raw_processed_image))
        self.secondary_source_image = self.transformed_image(self.apply_tone_curve_image(self.raw_secondary_source_image))
        self.secondary_processed_image = self.transformed_image(self.apply_tone_curve_image(self.raw_secondary_processed_image))
        self.source_pixmap = self.pixmap_for_image(self.raw_source_image, self.source_image)
        self.processed_pixmap = self.pixmap_for_image(self.raw_processed_image, self.processed_image)
        self.secondary_source_pixmap = self.pixmap_for_image(self.raw_secondary_source_image, self.secondary_source_image)
        self.secondary_processed_pixmap = self.pixmap_for_image(self.raw_secondary_processed_image, self.secondary_processed_image)

    def pixmap_for_image(self, raw_image: QImage, display_image: QImage) -> QPixmap:
        if raw_image.isNull() or display_image.isNull():
            return QPixmap()
        key = self.pixmap_cache_key(raw_image)
        cached = self.pixmap_cache.get(key)
        if cached is not None:
            self.pixmap_cache.move_to_end(key)
            return cached
        pixmap = QPixmap.fromImage(display_image)
        self.pixmap_cache[key] = pixmap
        while len(self.pixmap_cache) > self.pixmap_cache_limit:
            self.pixmap_cache.popitem(last=False)
        return pixmap

    def pixmap_cache_key(self, raw_image: QImage) -> tuple[int, int, bool, bool]:
        return (
            int(raw_image.cacheKey()),
            self.display_rotation % 360,
            self.display_flip_horizontal,
            self.display_flip_vertical,
        )

    def set_pixmap_cache_limit(self, limit: int) -> None:
        self.pixmap_cache_limit = max(24, int(limit))
        while len(self.pixmap_cache) > self.pixmap_cache_limit:
            self.pixmap_cache.popitem(last=False)

    def queue_pixmap_prefetch(self, items: list[tuple[object, QImage]]) -> None:
        for stable_key, image in items:
            if image.isNull():
                continue
            if stable_key in self.pixmap_prefetch_done_keys or stable_key in self.pixmap_prefetch_keys:
                continue
            self.pixmap_prefetch_queue.append((stable_key, image))
            self.pixmap_prefetch_keys.add(stable_key)
        if self.pixmap_prefetch_queue and not self.pixmap_prefetch_timer.isActive():
            self.pixmap_prefetch_timer.start(1)

    def clear_pixmap_prefetch_state(self) -> None:
        self.pixmap_prefetch_queue.clear()
        self.pixmap_prefetch_keys.clear()
        self.pixmap_prefetch_done_keys.clear()
        self.pixmap_prefetch_timer.stop()

    def process_pixmap_prefetch(self) -> None:
        started = time.perf_counter()
        warmed = 0
        budget = 1
        while self.pixmap_prefetch_queue and warmed < budget:
            stable_key, image = self.pixmap_prefetch_queue.popleft()
            self.pixmap_prefetch_keys.discard(stable_key)
            if image.isNull() or stable_key in self.pixmap_prefetch_done_keys:
                continue
            self.pixmap_for_image(image, self.transformed_image(image))
            self.pixmap_prefetch_done_keys.add(stable_key)
            warmed += 1
        if warmed:
            self.pixmapPrefetchProgress.emit(
                warmed,
                len(self.pixmap_prefetch_queue),
                len(self.pixmap_cache),
                (time.perf_counter() - started) * 1000,
            )
        if self.pixmap_prefetch_queue:
            self.pixmap_prefetch_timer.start(1)

    def rotate_display(self, degrees: int) -> None:
        self.display_rotation = (self.display_rotation + degrees) % 360
        self.rebuild_display_images()
        self.clear_resample_cache()
        self.reset_view(update=False)
        self.update()

    def flip_display(self, horizontal: bool) -> None:
        if horizontal:
            self.display_flip_horizontal = not self.display_flip_horizontal
        else:
            self.display_flip_vertical = not self.display_flip_vertical
        self.rebuild_display_images()
        self.clear_resample_cache()
        self.update()

    def set_background(self, color: str) -> None:
        self.background = QColor(color)
        self.update()

    def set_compare(self, enabled: bool, split: int, line_color: str, line_width: int, swap_sides: bool, shift_boundary: bool) -> None:
        self.compare_enabled = enabled
        self.compare_split = int(split)
        self.compare_line_color = QColor(line_color)
        self.compare_line_width = int(line_width)
        self.compare_swap_sides = bool(swap_sides)
        self.compare_shift_drag_moves_boundary = bool(shift_boundary)
        self.update()

    def set_horizontal_wheel_options(self, enabled: bool, inverted: bool) -> None:
        self.horizontal_wheel_navigation = bool(enabled)
        self.horizontal_wheel_inverted = bool(inverted)

    def set_resample_options(self, enabled: bool, algorithm: str) -> None:
        algorithm = algorithm if algorithm in RESAMPLE_ALGORITHMS else DEFAULT_RESAMPLE_ALGORITHM
        if self.cpu_resample_cache_enabled != enabled or self.cpu_resample_algorithm != algorithm:
            self.cpu_resample_cache_enabled = enabled
            self.cpu_resample_algorithm = algorithm
            self.resample_interaction_active = False
            self.resample_debounce_timer.stop()
            self.clear_resample_cache()
            self.update()

    def set_tone_curve_options(self, enabled: bool, curve: ToneCurve | None) -> None:
        self.tone_curve_enabled = bool(enabled and curve is not None)
        self.tone_curve_luts = {channel: curve.lut(channel) for channel in CURVE_CHANNELS} if self.tone_curve_enabled and curve is not None else None
        self.pixmap_cache.clear()
        self.clear_pixmap_prefetch_state()
        self.rebuild_display_images()
        self.clear_resample_cache()
        self.update()

    def clear_resample_cache(self) -> None:
        self.resample_cache.clear()

    def begin_interactive_resample_delay(self) -> None:
        if not self.cpu_resample_cache_enabled:
            return
        self.resample_interaction_active = True
        self.resample_debounce_timer.start(self.resample_debounce_ms)

    def finish_interactive_resample_delay(self) -> None:
        self.resample_interaction_active = False
        self.update()

    def current_display_image(self) -> QImage:
        if self.compare_enabled and not self.processed_image.isNull():
            return self.processed_image
        if not self.processed_image.isNull():
            return self.processed_image
        return self.source_image

    def display_page_entries(self) -> list[tuple[QImage, QImage, QPixmap, QPixmap]]:
        entries: list[tuple[QImage, QImage, QPixmap, QPixmap]] = []
        if not self.source_image.isNull():
            entries.append((self.source_image, self.processed_image, self.source_pixmap, self.processed_pixmap))
        if self.dual_page_enabled and not self.secondary_source_image.isNull():
            entries.append((
                self.secondary_source_image,
                self.secondary_processed_image,
                self.secondary_source_pixmap,
                self.secondary_processed_pixmap,
            ))
        if self.dual_page_reversed and len(entries) > 1:
            entries.reverse()
        return entries

    def current_content_size(self) -> QSize:
        entries = self.display_page_entries()
        if not entries:
            return QSize()
        width = 0
        height = 0
        for source, processed, _source_pixmap, _processed_pixmap in entries:
            image = processed if not processed.isNull() else source
            if image.isNull():
                continue
            width += image.width()
            height = max(height, image.height())
        return QSize(width, height) if width > 0 and height > 0 else QSize()

    def image_rect(self) -> QRect:
        content_size = self.current_content_size()
        if content_size.isEmpty():
            return QRect()
        scale = self.current_scale()
        width = max(1, round(content_size.width() * scale))
        height = max(1, round(content_size.height() * scale))
        x = (self.width() - width) // 2 + self.offset.x()
        y = (self.height() - height) // 2 + self.offset.y()
        return QRect(x, y, width, height)

    def current_scale(self) -> float:
        content_size = self.current_content_size()
        if content_size.isEmpty():
            return 1.0
        size_key = (content_size.width(), content_size.height())
        if self.fit_scale_anchor is None or self.fit_image_size != size_key:
            self.fit_scale_anchor = min(self.width() / content_size.width(), self.height() / content_size.height())
            self.fit_image_size = size_key
        return max(0.01, min(MAX_DISPLAY_SCALE, self.fit_scale_anchor * self.zoom))

    def clamp_zoom_factor(self, zoom: float) -> float:
        content_size = self.current_content_size()
        if content_size.isEmpty():
            return max(0.05, min(1.0, zoom))
        if self.fit_scale_anchor is None or self.fit_scale_anchor <= 0:
            self.fit_scale_anchor = min(self.width() / content_size.width(), self.height() / content_size.height())
            self.fit_image_size = (content_size.width(), content_size.height())
        max_zoom = MAX_DISPLAY_SCALE / max(self.fit_scale_anchor, 0.000001)
        return max(0.05, min(max_zoom, zoom))

    def reset_view(self, update: bool = True) -> None:
        self.offset = QPoint(0, 0)
        self.fit_scale_anchor = None
        self.fit_image_size = None
        self.clear_resample_cache()
        content_size = self.current_content_size()
        if not content_size.isEmpty() and self.width() > 0 and self.height() > 0:
            self.fit_scale_anchor = min(self.width() / content_size.width(), self.height() / content_size.height())
            self.fit_image_size = (content_size.width(), content_size.height())
        self.zoom = 1.0
        self.zoomChanged.emit(self.current_scale())
        if update:
            self.update()
            QTimer.singleShot(0, self.update)

    def reset_display_state(self) -> None:
        self.display_rotation = 0
        self.display_flip_horizontal = False
        self.display_flip_vertical = False
        self.rebuild_display_images()
        self.reset_view()

    def set_actual_zoom_percent(self, percent: int) -> None:
        content_size = self.current_content_size()
        if content_size.isEmpty():
            return
        if self.fit_scale_anchor is None or self.fit_scale_anchor <= 0:
            self.fit_scale_anchor = min(self.width() / content_size.width(), self.height() / content_size.height())
            self.fit_image_size = (content_size.width(), content_size.height())
        actual_scale = max(0.01, min(MAX_DISPLAY_SCALE, percent / 100.0))
        self.zoom = self.clamp_zoom_factor(actual_scale / self.fit_scale_anchor)
        self.zoomChanged.emit(self.current_scale())
        self.begin_interactive_resample_delay()
        self.update()

    def resizeGL(self, width: int, height: int) -> None:
        if abs(self.zoom - 1.0) > 0.0001:
            return
        content_size = self.current_content_size()
        if content_size.isEmpty() or width <= 0 or height <= 0:
            return
        self.fit_scale_anchor = min(width / content_size.width(), height / content_size.height())
        self.fit_image_size = (content_size.width(), content_size.height())
        self.zoomChanged.emit(self.current_scale())

    def zoom_to_actual_size(self) -> None:
        content_size = self.current_content_size()
        if content_size.isEmpty() or self.fit_scale_anchor is None or self.fit_scale_anchor <= 0:
            return
        self.zoom = self.clamp_zoom_factor(1.0 / self.fit_scale_anchor)
        self.zoomChanged.emit(self.current_scale())
        self.begin_interactive_resample_delay()
        self.update()

    def resampled_pixmap(self, image: QImage, target: QRect) -> QPixmap | None:
        if not self.cpu_resample_cache_enabled or image.isNull() or target.width() <= 0 or target.height() <= 0:
            return None
        if self.resample_interaction_active:
            return None
        device_pixel_ratio = max(1.0, float(self.devicePixelRatioF()))
        physical_width = max(1, round(target.width() * device_pixel_ratio))
        physical_height = max(1, round(target.height() * device_pixel_ratio))
        if physical_width == image.width() and physical_height == image.height():
            return None
        ratio_key = max(1, round(device_pixel_ratio * 1000))
        key = (int(image.cacheKey()), physical_width, physical_height, ratio_key, self.cpu_resample_algorithm)
        cached = self.resample_cache.get(key)
        if cached is not None:
            self.resample_cache.move_to_end(key)
            return cached
        scaled = self.resample_qimage(image, physical_width, physical_height)
        if scaled.isNull():
            return None
        pixmap = QPixmap.fromImage(scaled)
        pixmap.setDevicePixelRatio(device_pixel_ratio)
        self.resample_cache[key] = pixmap
        while len(self.resample_cache) > 24:
            self.resample_cache.popitem(last=False)
        return pixmap

    def resample_qimage(self, image: QImage, width: int, height: int) -> QImage:
        if PILImage is None:
            return image.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        source = image.convertToFormat(QImage.Format_RGBA8888)
        size = source.sizeInBytes()
        data = bytes(source.bits()[:size])
        pil = PILImage.frombytes("RGBA", (source.width(), source.height()), data)
        algorithm = self.cpu_resample_algorithm
        if algorithm == "lanczos4" and cv2 is not None and np is not None:
            array = np.array(pil)
            resized = cv2.resize(array, (width, height), interpolation=cv2.INTER_LANCZOS4)
            pil = PILImage.fromarray(resized, "RGBA")
        else:
            filters = {
                "area": PILImage.Resampling.BOX,
                "bicubic": PILImage.Resampling.BICUBIC,
                "lanczos3": PILImage.Resampling.LANCZOS,
                "lanczos4": PILImage.Resampling.LANCZOS,
            }
            pil = pil.resize((width, height), resample=filters.get(algorithm, PILImage.Resampling.LANCZOS))
        output = pil.convert("RGBA")
        output_data = output.tobytes()
        return QImage(output_data, output.width, output.height, QImage.Format_RGBA8888).copy()

    def apply_tone_curve_image(self, image: QImage) -> QImage:
        if image.isNull() or not self.tone_curve_enabled or not self.tone_curve_luts or np is None:
            return image
        source = image.convertToFormat(QImage.Format_RGBA8888)
        size = source.sizeInBytes()
        data = bytes(source.bits()[:size])
        array = np.frombuffer(data, dtype=np.uint8).reshape((source.height(), source.width(), 4)).copy()
        luminance = ((array[:, :, 0].astype(np.uint16) * 77 + array[:, :, 1].astype(np.uint16) * 150 + array[:, :, 2].astype(np.uint16) * 29) >> 8).astype(np.uint8)
        value_lut = np.array(self.tone_curve_luts.get("value", list(range(256))), dtype=np.uint8)
        red_lut = np.array(self.tone_curve_luts.get("red", list(range(256))), dtype=np.uint8)
        green_lut = np.array(self.tone_curve_luts.get("green", list(range(256))), dtype=np.uint8)
        blue_lut = np.array(self.tone_curve_luts.get("blue", list(range(256))), dtype=np.uint8)
        alpha_lut = np.array(self.tone_curve_luts.get("alpha", list(range(256))), dtype=np.uint8)
        mapped = value_lut[luminance]
        array[:, :, 0] = red_lut[mapped]
        array[:, :, 1] = green_lut[mapped]
        array[:, :, 2] = blue_lut[mapped]
        array[:, :, 3] = alpha_lut[array[:, :, 3]]
        output_data = array.tobytes()
        return QImage(output_data, source.width(), source.height(), QImage.Format_RGBA8888).copy()

    def draw_image(self, painter: QPainter, target: QRect, image: QImage, pixmap: QPixmap) -> None:
        if image.isNull() or pixmap.isNull():
            return
        resampled = self.resampled_pixmap(image, target)
        if resampled is not None:
            painter.drawPixmap(target.topLeft(), resampled)
        else:
            painter.drawPixmap(target, pixmap)

    def paintGL(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), self.background)
        target = self.image_rect()
        if target.isNull():
            painter.end()
            return

        entries = self.display_page_entries()
        if self.dual_page_enabled and len(entries) > 1:
            scale = self.current_scale()
            x = target.x()
            for source, processed, source_pixmap, processed_pixmap in entries:
                image = processed if not processed.isNull() else source
                pixmap = processed_pixmap if not processed_pixmap.isNull() else source_pixmap
                if image.isNull() or pixmap.isNull():
                    continue
                width = max(1, round(image.width() * scale))
                height = max(1, round(image.height() * scale))
                page_target = QRect(x, target.y() + (target.height() - height) // 2, width, height)
                self.draw_image(painter, page_target, image, pixmap)
                x += width
            painter.end()
            return

        source = self.source_image
        processed = self.processed_image
        if self.compare_enabled and not source.isNull():
            split_x = round(target.width() * self.compare_split / 1000)
            left_target = QRect(target.x(), target.y(), split_x, target.height())
            right_target = QRect(target.x() + split_x, target.y(), target.width() - split_x, target.height())
            processed_pixmap = self.processed_pixmap if not self.processed_pixmap.isNull() else self.source_pixmap
            left_pixmap, right_pixmap = (
                (processed_pixmap, self.source_pixmap)
                if self.compare_swap_sides
                else (self.source_pixmap, processed_pixmap)
            )
            left_image, right_image = (
                (processed if not processed.isNull() else source, source)
                if self.compare_swap_sides
                else (source, processed if not processed.isNull() else source)
            )
            if left_target.width() > 0 and not left_pixmap.isNull():
                painter.save()
                painter.setClipRect(left_target)
                self.draw_image(painter, target, left_image, left_pixmap)
                painter.restore()
            if right_target.width() > 0 and not right_pixmap.isNull():
                painter.save()
                painter.setClipRect(right_target)
                self.draw_image(painter, target, right_image, right_pixmap)
                painter.restore()
            pen = QPen(self.compare_line_color)
            pen.setWidth(max(1, self.compare_line_width))
            painter.setPen(pen)
            painter.drawLine(target.x() + split_x, target.y(), target.x() + split_x, target.y() + target.height())
        else:
            pixmap = self.processed_pixmap if not self.processed_pixmap.isNull() else self.source_pixmap
            image = self.processed_image if not self.processed_image.isNull() else self.source_image
            if not pixmap.isNull():
                self.draw_image(painter, target, image, pixmap)
        painter.end()

    def matching_mouse_action(self, event, double: bool) -> str | None:
        modifiers = modifier_value(event.modifiers())
        button = int(event.button().value if hasattr(event.button(), "value") else event.button())
        signature = (button, modifiers, double)
        if signature in self.duplicate_mouse_bindings:
            return None
        for action_id, bindings in self.key_bindings.items():
            binding = bindings.get("mouse") if isinstance(bindings, dict) else None
            if not binding:
                continue
            if (
                int(binding.get("button", 0)) == button
                and int(binding.get("modifiers", 0)) == modifiers
                and bool(binding.get("double", False)) == double
            ):
                return action_id
        return None

    def wheelEvent(self, event) -> None:
        angle_delta = event.angleDelta()
        if abs(angle_delta.x()) > abs(angle_delta.y()):
            if not self.horizontal_wheel_navigation or event.modifiers() & Qt.ControlModifier:
                event.ignore()
                return
            delta = angle_delta.x()
            pages = max(1, abs(delta) // 120)
            step = pages if delta > 0 else -pages
            if self.horizontal_wheel_inverted:
                step = -step
            self.pageRequested.emit(step)
            return
        delta = angle_delta.y()
        if delta == 0:
            event.ignore()
            return
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.12 if delta > 0 else 1 / 1.12
            self.zoom = self.clamp_zoom_factor(self.zoom * factor)
            self.zoomChanged.emit(self.current_scale())
            self.begin_interactive_resample_delay()
            self.update()
            return
        pages = max(1, abs(delta) // 120)
        self.pageRequested.emit(pages if delta < 0 else -pages)

    def mousePressEvent(self, event) -> None:
        action_id = self.matching_mouse_action(event, double=False)
        if action_id:
            self.actionRequested.emit(action_id)
            return
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ControlModifier:
                self.zoom_drag_start = event.position().toPoint()
                self.pan_start = None
            elif self._drag_moves_compare_boundary(event):
                self._set_split_from_x(round(event.position().x()))
            else:
                self.pan_start = event.position().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            if event.modifiers() & Qt.ControlModifier:
                pos = event.position().toPoint()
                if self.zoom_drag_start is None:
                    self.zoom_drag_start = pos
                dy = pos.y() - self.zoom_drag_start.y()
                if dy:
                    self.zoom = self.clamp_zoom_factor(self.zoom * (1.01 ** (-dy)))
                    self.zoomChanged.emit(self.current_scale())
                    self.begin_interactive_resample_delay()
                    self.zoom_drag_start = pos
                    self.pan_start = None
                    self.update()
            elif self._drag_moves_compare_boundary(event):
                self._set_split_from_x(round(event.position().x()))
                self.pan_start = None
            elif self.pan_start is not None:
                pos = event.position().toPoint()
                delta = pos - self.pan_start
                self.offset += delta
                self.pan_start = pos
                self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.zoom_drag_start = None
            self.pan_start = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        action_id = self.matching_mouse_action(event, double=True)
        if action_id:
            self.actionRequested.emit(action_id)
            return
        super().mouseDoubleClickEvent(event)

    def _drag_moves_compare_boundary(self, event) -> bool:
        if not self.compare_enabled or self.processed_image.isNull():
            return False
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        return shift if self.compare_shift_drag_moves_boundary else not shift

    def _set_split_from_x(self, x: int) -> None:
        target = self.image_rect()
        if target.isNull() or target.width() <= 0:
            return
        percent = round((x - target.x()) / target.width() * 1000)
        self.compare_split = max(0, min(1000, percent))
        self.splitChanged.emit(self.compare_split)
        self.update()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.initializing = True
        self.config_data = load_config()
        self.duplicate_keyboard_bindings = duplicate_binding_signatures(self.config_data.key_bindings, "keyboard")
        self.show_log_panel = self.config_data.show_log_panel
        if self.config_data.cleanup_temp_on_start:
            self._cleanup_stale_temp_files()
            self.config_data.cleanup_temp_on_start = False
            save_config(self.config_data)

        self.signals = AppSignals()
        self.signals.process_started.connect(self.on_process_started)
        self.signals.process_done.connect(self.on_process_done)
        self.signals.folder_images_ready.connect(self.on_folder_images_ready)
        self.signals.prefetch_done.connect(self.on_prefetch_done)
        self.signals.thumbnail_done.connect(self.on_thumbnail_done)
        self.signals.profile_event.connect(self.record_profile)

        self.image_paths: list[Path] = []
        self.image_path_set: set[Path] = set()
        self.image_path_string_set: set[str] = set()
        self.current_index = -1
        self.dual_page_enabled = bool(self.config_data.dual_page_enabled)
        self.tone_curves: dict[str, ToneCurve] = {}
        self.current_tone_curve: ToneCurve | None = None
        self.last_navigation_step = 1
        self.folder_list_loading = False
        self.deferred_page_steps = 0
        self.original_cache: OrderedDict[Path, QImage] = OrderedDict()
        self.processed_cache: OrderedDict[tuple[str, str, int, int, int, str], QImage] = OrderedDict()
        self.processing_paths: set[Path] = set()
        self.queued_paths: set[Path] = set()
        self.work_queue: queue.Queue[Path | None] = queue.Queue()
        self.prefetch_io_queue: queue.PriorityQueue[tuple[int, int, int, str, object, str, str]] = queue.PriorityQueue()
        self.prefetch_io_sequence = 0
        self.prefetch_io_lock = threading.Lock()
        self.thumbnail_queue: queue.PriorityQueue[tuple[int, int, int, int, str]] = queue.PriorityQueue()
        self.thumbnail_sequence = 0
        self.thumbnail_lock = threading.Lock()
        self.thumbnail_generation = 0
        self.thumbnail_pending: set[int] = set()
        self.thumbnail_ready_indexes: set[int] = set()
        self.thumbnail_items: list[QListWidgetItem | None] = []
        self.thumbnail_overlay_visible = False
        self.thumbnail_height = int(self.config_data.thumbnail_height)
        self.thumbnail_render_size = int(self.config_data.thumbnail_size)
        self.thumbnail_resizing = False
        self.thumbnail_hide_suppressed_until = 0.0
        self.thumbnail_rebuild_index = 0
        self.thumbnail_rebuild_timer = QTimer(self)
        self.thumbnail_rebuild_timer.setSingleShot(True)
        self.thumbnail_rebuild_timer.timeout.connect(self.continue_thumbnail_rebuild)
        self.thumbnail_resize_refresh_timer = QTimer(self)
        self.thumbnail_resize_refresh_timer.setSingleShot(True)
        self.thumbnail_resize_refresh_timer.timeout.connect(self.refresh_thumbnail_icons_for_size)
        self.profile_stats: dict[str, dict[str, float]] = {}
        self.profile_update_timer = QTimer(self)
        self.profile_update_timer.setSingleShot(True)
        self.profile_update_timer.timeout.connect(self.update_profile_panel)
        self.archive_temp_dir: Path | None = None
        self.retired_archive_temp_dirs: list[Path] = []
        self.archive_display_names: dict[Path, str] = {}
        self.archive_source_path: Path | None = None
        self.archive_disabled_scale_options: tuple[bool, bool] | None = None
        self.process_temp_dir = Path(tempfile.mkdtemp(prefix=TEMP_WORK_PREFIX))
        self.write_temp_lock(self.process_temp_dir)

        self.page_scroll_timer = QTimer(self)
        self.page_scroll_timer.timeout.connect(self._drain_page_steps)
        self.pending_page_steps = 0
        self.prefetch_timer = QTimer(self)
        self.prefetch_timer.setSingleShot(True)
        self.prefetch_timer.timeout.connect(self.schedule_prefetch)
        self.prefetch_generation = 0
        self.prefetching_original_paths: set[Path] = set()
        self.prefetching_processed_keys: set[tuple[str, str, int, int, int, str]] = set()
        self.prefetch_viewer_plan: list[Path] = []
        self.prefetch_engine_plan: list[Path] = []
        self.prefetch_engine_done_paths: set[Path] = set()
        self.pixmap_prefetch_log_accum = 0
        self.side_panel_visible_before_fullscreen = True
        self.side_panel_width = int(self.config_data.side_panel_width)
        self.fullscreen_cursor_hidden = False
        self.side_panel_overlay = False
        self.borderless_fullscreen = False
        self.before_fullscreen_geometry = QRect()
        self.before_fullscreen_flags = self.windowFlags()
        self.before_fullscreen_state = Qt.WindowNoState
        self.fullscreen_enforce_pending = False
        self.overlay_resizing = False
        self.overlay_modal_guard = False
        self.overlay_hide_suppressed_until = 0.0
        self.adjusting_splitter = False
        self.closing = False

        self.setWindowTitle(APP_NAME)
        self.setAcceptDrops(True)
        if APP_ICON_ICO.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_ICO)))
        elif APP_ICON_PNG.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PNG)))

        self.viewer_host = QWidget()
        self.viewer_host.setMouseTracking(True)
        self.viewer_host.installEventFilter(self)
        self.viewer = GLImageView()
        self.viewer.setParent(self.viewer_host)
        self.viewer.pageRequested.connect(self.queue_page_steps)
        self.viewer.firstRequested.connect(self.show_first_image)
        self.viewer.lastRequested.connect(self.show_last_image)
        self.viewer.zoomChanged.connect(self.update_zoom_label)
        self.viewer.splitChanged.connect(self.on_viewer_split_changed)
        self.viewer.fullscreenRequested.connect(self.toggle_fullscreen)
        self.viewer.resetRequested.connect(self.viewer.reset_display_state)
        self.viewer.actualSizeRequested.connect(self.viewer.zoom_to_actual_size)
        self.viewer.actionRequested.connect(self.perform_action)
        self.viewer.pixmapPrefetchProgress.connect(self.on_pixmap_prefetch_progress)
        self.viewer.installEventFilter(self)
        self.thumbnail_panel = self.build_thumbnail_panel()
        self.thumbnail_panel.setParent(self.viewer_host)
        self.thumbnail_panel.installEventFilter(self)
        self.thumbnail_list.installEventFilter(self)
        self.thumbnail_list.viewport().installEventFilter(self)

        self.side_panel = self._build_side_panel()
        self.side_panel.installEventFilter(self)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.viewer_host)
        self.splitter.addWidget(self.side_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.splitterMoved.connect(self.on_splitter_moved)
        self.setCentralWidget(self.splitter)

        self._restore_geometry()
        self._apply_settings_to_viewer()
        self.initializing = False

        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()
        self.prefetch_io_workers = [
            threading.Thread(target=self._prefetch_io_worker_loop, daemon=True)
            for _index in range(2)
        ]
        for worker in self.prefetch_io_workers:
            worker.start()
        self.thumbnail_worker = threading.Thread(target=self._thumbnail_worker_loop, daemon=True)
        self.thumbnail_worker.start()

    def build_thumbnail_panel(self) -> QWidget:
        panel = QWidget(self.viewer_host)
        panel.setObjectName("thumbnailPanel")
        panel.setAutoFillBackground(True)
        panel.setStyleSheet("#thumbnailPanel { background: palette(window); border-top: 1px solid palette(mid); }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 4, 6, 4)
        self.thumbnail_list = QListWidget(panel)
        self.thumbnail_list.setViewMode(QListView.IconMode)
        self.thumbnail_list.setFlow(QListView.LeftToRight)
        self.thumbnail_list.setWrapping(False)
        self.thumbnail_list.setMovement(QListView.Static)
        self.thumbnail_list.setResizeMode(QListView.Adjust)
        self.thumbnail_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.thumbnail_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.thumbnail_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.thumbnail_list.setStyleSheet(
            "QListWidget::item:selected { border: 3px solid #2f80ff; background: rgba(47, 128, 255, 70); }"
            "QListWidget::item { margin: 2px; padding: 2px; }"
        )
        self.thumbnail_list.itemClicked.connect(self.on_thumbnail_clicked)
        layout.addWidget(self.thumbnail_list)
        return panel

    def thumbnail_panel_height(self) -> int:
        return self.clamped_thumbnail_height()

    def clamped_thumbnail_height(self, height: int | None = None) -> int:
        value = int(self.thumbnail_height if height is None else height)
        return max(THUMBNAIL_MIN_HEIGHT, min(THUMBNAIL_MAX_HEIGHT, value))

    def thumbnail_icon_size(self, height: int | None = None) -> int:
        panel_height = self.clamped_thumbnail_height(height)
        return max(48, min(256, panel_height - 48))

    def thumbnails_enabled(self) -> bool:
        check = getattr(self, "thumbnail_enabled_check", None)
        return bool(check.isChecked() if check is not None else self.config_data.thumbnail_enabled)

    def thumbnails_pinned(self) -> bool:
        check = getattr(self, "thumbnail_pinned_check", None)
        return bool(check.isChecked() if check is not None else self.config_data.thumbnail_pinned)

    def layout_viewer_host(self) -> None:
        if not hasattr(self, "viewer_host"):
            return
        rect = self.viewer_host.rect()
        if rect.isNull():
            return
        enabled = self.thumbnails_enabled()
        pinned = enabled and self.thumbnails_pinned()
        strip_height = self.thumbnail_panel_height() if enabled else 0
        if pinned:
            viewer_height = max(1, rect.height() - strip_height)
            self.viewer.setGeometry(0, 0, rect.width(), viewer_height)
            self.thumbnail_panel.setGeometry(0, viewer_height, rect.width(), strip_height)
            self.thumbnail_panel.show()
            self.thumbnail_overlay_visible = False
        else:
            self.viewer.setGeometry(rect)
            self.thumbnail_panel.setGeometry(0, max(0, rect.height() - strip_height), rect.width(), strip_height)
            self.thumbnail_panel.setVisible(enabled and self.thumbnail_overlay_visible)
            if self.thumbnail_panel.isVisible():
                self.thumbnail_panel.raise_()
        self.update_thumbnail_metrics()
        self.thumbnail_height = strip_height if enabled else self.thumbnail_height

    def show_thumbnail_overlay(self) -> None:
        if not self.thumbnails_enabled() or self.thumbnails_pinned():
            return
        if not self.thumbnail_overlay_visible:
            self.thumbnail_overlay_visible = True
            self.layout_viewer_host()
        self.thumbnail_panel.raise_()

    def hide_thumbnail_overlay(self) -> None:
        if self.thumbnails_pinned() or not self.thumbnail_overlay_visible:
            return
        if self.thumbnail_resizing or time.monotonic() < self.thumbnail_hide_suppressed_until:
            return
        if self.is_cursor_over_thumbnail_panel():
            return
        self.thumbnail_overlay_visible = False
        self.layout_viewer_host()

    def is_cursor_over_thumbnail_panel(self) -> bool:
        if not hasattr(self, "thumbnail_panel") or not self.thumbnail_panel.isVisible():
            return False
        local = self.thumbnail_panel.mapFromGlobal(QCursor.pos())
        return self.thumbnail_panel.rect().adjusted(0, -THUMBNAIL_HIDE_MARGIN, 0, THUMBNAIL_HIDE_MARGIN).contains(local)

    def _build_side_panel(self) -> QWidget:
        root = QWidget()
        root.setMinimumWidth(240)
        root.setAutoFillBackground(True)
        root.setObjectName("sidePanel")
        root.setStyleSheet("#sidePanel { background: palette(window); }")
        layout = QVBoxLayout(root)
        header = QHBoxLayout()
        header.addWidget(QLabel("設定"))
        header.addStretch(1)
        self.pin_button = QPushButton("固定")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(self.config_data.side_panel_pinned)
        self.pin_button.toggled.connect(self.on_side_panel_pin_changed)
        header.addWidget(self.pin_button)
        layout.addLayout(header)
        self.pin_button.setText("固定中" if self.config_data.side_panel_pinned else "自動表示")

        tabs = QTabWidget()
        self.tabs = tabs
        realcugan_tab = QScrollArea()
        general_tab = QScrollArea()
        image_adjust_tab = QScrollArea()
        other_tab = QScrollArea()
        keyconfig_tab = QScrollArea()
        realcugan_tab.setWidgetResizable(True)
        general_tab.setWidgetResizable(True)
        image_adjust_tab.setWidgetResizable(True)
        other_tab.setWidgetResizable(True)
        keyconfig_tab.setWidgetResizable(True)
        tabs.addTab(realcugan_tab, "エンジン設定")
        tabs.addTab(general_tab, "全般")
        tabs.addTab(image_adjust_tab, "画像調整")
        tabs.addTab(other_tab, "その他")
        tabs.addTab(keyconfig_tab, "キーコンフィグ")
        tabs.currentChanged.connect(self.on_settings_tab_changed)
        layout.addWidget(tabs)

        realcugan_content = QWidget()
        realcugan_layout = QVBoxLayout(realcugan_content)
        form = QFormLayout()
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(list(ENGINE_LABELS.values()))
        self.engine_combo.setCurrentText(ENGINE_LABELS.get(self.config_data.engine, ENGINE_LABELS[ENGINE_REALCUGAN]))
        self.engine_combo.currentTextChanged.connect(self.on_engine_changed)
        form.addRow("エンジン", self.engine_combo)
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["2", "3", "4"])
        self.scale_combo.setCurrentText(str(self.config_data.scale))
        self.scale_combo.currentTextChanged.connect(self.on_processing_settings_changed)
        form.addRow("倍率", self.scale_combo)

        self.denoise_combo = QComboBox()
        self.denoise_combo.addItems(["-1", "0", "1", "2", "3"])
        self.denoise_combo.setCurrentText(str(self.config_data.denoise))
        self.denoise_combo.currentTextChanged.connect(self.on_processing_settings_changed)
        form.addRow("ノイズ", self.denoise_combo)
        self.realesrgan_model_combo = QComboBox()
        self.realesrgan_model_combo.addItems(REALESRGAN_MODELS)
        self.realesrgan_model_combo.setCurrentText(self.config_data.realesrgan_model)
        self.realesrgan_model_combo.currentTextChanged.connect(self.on_processing_settings_changed)
        form.addRow("Real-ESRGANモデル", self.realesrgan_model_combo)
        self.tile_spin = QSpinBox()
        self.tile_spin.setRange(0, 16)
        self.tile_spin.setValue(self.config_data.tile)
        self.tile_spin.valueChanged.connect(self.on_processing_settings_changed)
        form.addRow("tile", self.tile_spin)
        realcugan_layout.addLayout(form)
        self.denoise_help = self.help_label("ノイズ: Real-CUGAN専用。-1 はノイズ除去なし。0/1/2/3 は数値が大きいほど強く除去します。")
        realcugan_layout.addWidget(self.denoise_help)
        self.realesrgan_model_help = self.help_label("Real-ESRGANはノイズ値を使わず、モデルで画風や復元傾向を選びます。")
        realcugan_layout.addWidget(self.realesrgan_model_help)
        self.realesrgan_model_detail = self.help_label(
            "realesr-animevideov3: アニメ/イラスト向けの軽量標準モデル。"
            " realesrgan-x4plus: 写真や一般画像向け。"
            " realesrgan-x4plus-anime: アニメ/イラスト向けのx4plus派生モデル。"
            " RAIVではReal-ESRGAN選択中、倍率は4倍固定として処理します。"
        )
        realcugan_layout.addWidget(self.realesrgan_model_detail)

        realcugan_layout.addWidget(self.help_label("tile: 0 は自動。小さめの値はGPUメモリ使用量を抑えますが、遅くなることがあります。"))

        form3 = QFormLayout()
        self.realcugan_prefetch_spin = QSpinBox()
        self.realcugan_prefetch_spin.setRange(0, 99999)
        self.realcugan_prefetch_spin.setValue(self.config_data.realcugan_prefetch_count)
        self.realcugan_prefetch_spin.valueChanged.connect(self.on_processing_settings_changed)
        form3.addRow("エンジン先読み", self.realcugan_prefetch_spin)
        form3.addRow(self.help_label("選択中の拡大エンジンで処理を先に進める枚数。大きいほど待ち時間を減らせますが、GPU負荷と一時ファイル作成が増えます。"))
        self.skip_tall_check = QCheckBox("縦サイズが閾値以上なら拡大処理しない")
        self.skip_tall_check.setChecked(self.config_data.skip_realcugan_for_tall_images)
        self.skip_tall_check.stateChanged.connect(self.on_processing_settings_changed)
        self.skip_height_spin = QSpinBox()
        self.skip_height_spin.setRange(1, 99999)
        self.skip_height_spin.setValue(self.config_data.skip_realcugan_height_threshold)
        self.skip_height_spin.valueChanged.connect(self.on_processing_settings_changed)
        form3.addRow(self.skip_tall_check)
        form3.addRow("縦サイズ閾値(px)", self.skip_height_spin)
        form3.addRow(self.help_label("モニタ解像度以上の画像をさらに拡大しても表示上の効果は小さく、処理時間とメモリ使用量が増えます。普段使うモニタの縦解像度に合わせる設定が目安です。"))
        realcugan_layout.addLayout(form3)

        self.save_scale_check = QCheckBox("拡大結果を倍率フォルダに保存")
        self.save_scale_check.setChecked(self.config_data.save_upscaled_to_scale_folder)
        self.save_scale_check.stateChanged.connect(self.on_processing_settings_changed)
        self.use_scale_cache_check = QCheckBox("倍率フォルダがあれば表示に使う")
        self.use_scale_cache_check.setChecked(self.config_data.use_scale_folder_cache)
        self.use_scale_cache_check.stateChanged.connect(self.on_processing_settings_changed)
        realcugan_layout.addWidget(self.save_scale_check)
        realcugan_layout.addWidget(self.use_scale_cache_check)
        self.archive_help = self.help_label("アーカイブ表示中は保存先フォルダがないため、倍率フォルダ保存と倍率フォルダ読み込みは無効です。")
        self.archive_help.hide()
        realcugan_layout.addWidget(self.archive_help)
        rerun_button = QPushButton("再実行")
        rerun_button.clicked.connect(self.force_reprocess)
        realcugan_layout.addWidget(rerun_button)
        realcugan_layout.addWidget(self.separator())

        realcugan_layout.addWidget(QLabel("コマンドテンプレート"))
        self.command_edit = QLineEdit(self.config_data.command_template)
        realcugan_layout.addWidget(self.command_edit)
        exe_button = QPushButton("エンジンexeを選択")
        exe_button.clicked.connect(self.choose_engine_exe)
        realcugan_layout.addWidget(exe_button)
        realcugan_layout.addWidget(self.help_label("使用できる置換: {input} {output} {scale} {denoise} {tile} {model}"))
        realcugan_layout.addStretch(1)
        realcugan_tab.setWidget(realcugan_content)

        general_content = QWidget()
        general_layout = QVBoxLayout(general_content)

        viewer_form = QFormLayout()
        self.viewer_prefetch_spin = QSpinBox()
        self.viewer_prefetch_spin.setRange(0, 99999)
        self.viewer_prefetch_spin.setValue(self.config_data.viewer_prefetch_count)
        self.viewer_prefetch_spin.valueChanged.connect(self.on_viewer_prefetch_changed)
        viewer_form.addRow("ビューアー先読み", self.viewer_prefetch_spin)
        general_layout.addLayout(viewer_form)
        general_layout.addWidget(self.help_label("表示用に画像をメモリへ先読みする枚数。大きいほどページ送りは速くなりますが、メモリ使用量が増えます。"))

        background_form = QFormLayout()
        bg_row = QHBoxLayout()
        self.background_edit = QLineEdit(self.config_data.background_color)
        bg_button = QPushButton("選択")
        bg_button.clicked.connect(self.choose_background_color)
        bg_row.addWidget(bg_button)
        bg_row.addWidget(self.background_edit)
        background_form.addRow("背景色", bg_row)
        self.background_edit.editingFinished.connect(self.on_background_changed)
        general_layout.addLayout(background_form)

        general_layout.addWidget(self.separator())
        self.compare_check = QCheckBox("比較モード")
        self.compare_check.setChecked(self.config_data.compare_enabled)
        self.compare_check.stateChanged.connect(self.on_compare_changed)
        self.dual_page_check = QCheckBox("見開き表示")
        self.dual_page_check.setChecked(self.dual_page_enabled)
        self.dual_page_check.stateChanged.connect(self.on_dual_page_check_changed)
        general_layout.addWidget(self.dual_page_check)
        self.dual_page_landscape_check = QCheckBox("横長画像は1枚表示にする")
        self.dual_page_landscape_check.setChecked(self.config_data.dual_page_landscape_single)
        self.dual_page_landscape_check.stateChanged.connect(self.on_dual_page_landscape_changed)
        general_layout.addWidget(self.dual_page_landscape_check)
        general_layout.addWidget(self.help_label("横長画像を既に見開きのページとして扱い、隣の画像と並べずに表示します。"))
        general_layout.addWidget(self.help_label("見開き表示時は比較モードは無効です。"))
        general_layout.addWidget(self.compare_check)
        compare_form = QFormLayout()
        self.compare_slider = QSlider(Qt.Horizontal)
        self.compare_slider.setRange(0, 1000)
        self.compare_slider.setValue(self.config_data.compare_split)
        self.compare_slider.valueChanged.connect(self.on_compare_changed)
        compare_form.addRow("比較スライダー", self.compare_slider)
        self.compare_center_button = QPushButton("中央に戻す")
        self.compare_center_button.clicked.connect(self.reset_compare_split)
        compare_form.addRow("", self.compare_center_button)
        compare_color_row = QHBoxLayout()
        self.compare_line_edit = QLineEdit(self.config_data.compare_line_color)
        self.compare_color_button = QPushButton("選択")
        self.compare_color_button.clicked.connect(self.choose_compare_line_color)
        compare_color_row.addWidget(self.compare_color_button)
        compare_color_row.addWidget(self.compare_line_edit)
        compare_form.addRow("境界線色", compare_color_row)
        self.compare_line_edit.editingFinished.connect(self.on_compare_changed)
        self.compare_line_width_spin = QSpinBox()
        self.compare_line_width_spin.setRange(1, 20)
        self.compare_line_width_spin.setValue(self.config_data.compare_line_width)
        self.compare_line_width_spin.valueChanged.connect(self.on_compare_changed)
        compare_form.addRow("境界線の太さ(px)", self.compare_line_width_spin)
        general_layout.addLayout(compare_form)
        self.compare_swap_check = QCheckBox("比較の左右を入れ替える")
        self.compare_swap_check.setChecked(self.config_data.compare_swap_sides)
        self.compare_swap_check.stateChanged.connect(self.on_compare_changed)
        general_layout.addWidget(self.compare_swap_check)
        self.compare_shift_check = QCheckBox("比較中はShift+ドラッグで境界線を動かす")
        self.compare_shift_check.setChecked(self.config_data.compare_shift_drag_moves_boundary)
        self.compare_shift_check.stateChanged.connect(self.on_compare_changed)
        general_layout.addWidget(self.compare_shift_check)

        view_form = QFormLayout()
        self.zoom_label = QLabel("ズーム: 100%")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        view_form.addRow(self.zoom_label, self.zoom_slider)
        reset_button = QPushButton("表示を中央へリセット")
        reset_button.clicked.connect(self.viewer.reset_display_state)
        view_form.addRow("", reset_button)

        self.page_interval_spin = QSpinBox()
        self.page_interval_spin.setRange(0, 100)
        self.page_interval_spin.setValue(self.config_data.page_scroll_interval_ms)
        self.page_interval_spin.valueChanged.connect(self.on_general_settings_changed)
        view_form.addRow("ページ送り間隔(ms)", self.page_interval_spin)
        general_layout.addLayout(view_form)
        general_layout.addWidget(self.help_label("ホイールやキー操作で連続ページ送りする時の間隔。0 は最短です。"))
        page_position_form = QFormLayout()
        self.page_position_slider = QSlider(Qt.Horizontal)
        self.page_position_slider.setRange(0, 0)
        self.page_position_slider.setEnabled(False)
        self.page_position_slider.setInvertedAppearance(self.config_data.invert_page_position_slider)
        self.page_position_slider.valueChanged.connect(self.on_page_position_slider_changed)
        page_position_row = QHBoxLayout()
        self.page_position_count_label = QLabel("0/0")
        self.page_position_count_label.setMinimumWidth(52)
        self.page_position_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        page_position_row.addWidget(self.page_position_slider, 1)
        page_position_row.addWidget(self.page_position_count_label)
        page_position_form.addRow("ページ位置", page_position_row)
        general_layout.addLayout(page_position_form)
        self.invert_page_position_check = QCheckBox("ページ位置スライダーの左右を入れ替える（右綴じにする）")
        self.invert_page_position_check.setChecked(self.config_data.invert_page_position_slider)
        self.invert_page_position_check.stateChanged.connect(self.on_page_position_slider_direction_changed)
        general_layout.addWidget(self.invert_page_position_check)
        general_layout.addWidget(self.help_label("オンにすると、ページ位置スライダーとサムネイル列の左右方向が連動して入れ替わります。"))
        self.thumbnail_enabled_check = QCheckBox("画面下部にサムネイルを表示する")
        self.thumbnail_enabled_check.setChecked(self.config_data.thumbnail_enabled)
        self.thumbnail_enabled_check.stateChanged.connect(self.on_thumbnail_settings_changed)
        general_layout.addWidget(self.thumbnail_enabled_check)
        general_layout.addWidget(self.help_label("オフにするとサムネイル生成処理も停止します。大量の画像を開く時に、初期表示や先読みを軽くできます。"))
        self.thumbnail_pinned_check = QCheckBox("サムネイル列を固定表示する")
        self.thumbnail_pinned_check.setChecked(self.config_data.thumbnail_pinned)
        self.thumbnail_pinned_check.stateChanged.connect(self.on_thumbnail_settings_changed)
        self.thumbnail_pinned_check.setEnabled(self.thumbnail_enabled_check.isChecked())
        general_layout.addWidget(self.thumbnail_pinned_check)
        self.wrap_page_check = QCheckBox("最後/最初でページ送りしたら反対側へ移動")
        self.wrap_page_check.setChecked(self.config_data.wrap_page_navigation)
        self.wrap_page_check.stateChanged.connect(self.on_general_settings_changed)
        general_layout.addWidget(self.wrap_page_check)
        self.preserve_view_check = QCheckBox("ページ送り時にズームと表示位置を維持")
        self.preserve_view_check.setChecked(self.config_data.preserve_view_on_page_navigation)
        self.preserve_view_check.stateChanged.connect(self.on_general_settings_changed)
        general_layout.addWidget(self.preserve_view_check)
        self.horizontal_wheel_check = QCheckBox("マウス横スクロールでページ送り")
        self.horizontal_wheel_check.setChecked(self.config_data.horizontal_wheel_navigation)
        self.horizontal_wheel_check.stateChanged.connect(self.on_general_settings_changed)
        general_layout.addWidget(self.horizontal_wheel_check)
        self.horizontal_wheel_invert_check = QCheckBox("横スクロールのページ送り方向を反転")
        self.horizontal_wheel_invert_check.setChecked(self.config_data.horizontal_wheel_inverted)
        self.horizontal_wheel_invert_check.stateChanged.connect(self.on_general_settings_changed)
        general_layout.addWidget(self.horizontal_wheel_invert_check)
        self.hide_cursor_fullscreen_check = QCheckBox("全画面表示時にマウスカーソルを非表示")
        self.hide_cursor_fullscreen_check.setChecked(self.config_data.hide_cursor_in_fullscreen)
        self.hide_cursor_fullscreen_check.stateChanged.connect(self.on_general_settings_changed)
        general_layout.addWidget(self.hide_cursor_fullscreen_check)
        self.status_label = QLabel("画像またはフォルダ/アーカイブをドロップしてください")
        self.status_label.setWordWrap(True)
        general_layout.addWidget(QLabel("状態"))
        general_layout.addWidget(self.status_label)
        general_layout.addWidget(self.separator())
        self.show_log_check = QCheckBox("ログを表示")
        self.show_log_check.setChecked(self.config_data.show_log_panel)
        self.show_log_check.stateChanged.connect(self.on_log_visibility_changed)
        general_layout.addWidget(self.show_log_check)
        self.log_container = QWidget()
        log_layout = QVBoxLayout(self.log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.prefetch_progress_panel = QWidget()
        progress_layout = QFormLayout(self.prefetch_progress_panel)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.original_prefetch_bar = QProgressBar()
        self.upscale_progress_bar = QProgressBar()
        self.processed_prefetch_bar = QProgressBar()
        self.pixmap_prefetch_bar = QProgressBar()
        for bar in (self.original_prefetch_bar, self.upscale_progress_bar, self.processed_prefetch_bar, self.pixmap_prefetch_bar):
            bar.setRange(0, 1)
            bar.setValue(0)
            bar.setTextVisible(True)
        progress_layout.addRow("拡大前メモリ読込", self.original_prefetch_bar)
        progress_layout.addRow("拡大画像生成", self.upscale_progress_bar)
        progress_layout.addRow("拡大後メモリ読込", self.processed_prefetch_bar)
        progress_layout.addRow("表示用QPixmap", self.pixmap_prefetch_bar)
        log_layout.addWidget(self.prefetch_progress_panel)
        self.log_label = QLabel("ログ")
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(160)
        self.log_edit.setSizePolicy(self.log_edit.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        self.log_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        log_layout.addWidget(self.log_label)
        log_layout.addWidget(self.log_edit)
        general_layout.addWidget(self.log_container)
        self.show_profile_check = QCheckBox("内部プロファイリングを表示")
        self.show_profile_check.setChecked(self.config_data.show_profile_panel)
        self.show_profile_check.stateChanged.connect(self.on_profile_visibility_changed)
        general_layout.addWidget(self.show_profile_check)
        self.profile_panel = QLabel()
        self.profile_panel.setWordWrap(True)
        self.profile_panel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        general_layout.addWidget(self.profile_panel)
        general_layout.addStretch(1)
        self.apply_log_visibility()
        general_tab.setWidget(general_content)

        image_adjust_content = QWidget()
        image_adjust_content.setMinimumWidth(0)
        image_adjust_layout = QVBoxLayout(image_adjust_content)
        self.tone_curve_check = QCheckBox("トーンカーブ補正を使う")
        self.tone_curve_check.setChecked(self.config_data.tone_curve_enabled)
        self.tone_curve_check.stateChanged.connect(self.on_tone_curve_settings_changed)
        image_adjust_layout.addWidget(self.tone_curve_check)
        image_adjust_layout.addWidget(self.help_label("GIMP .curファイルを使い、輝度に応じてRGBを割り当てます。モノクロ漫画を疑似4色刷りのように表示できます。"))
        curve_form = QFormLayout()
        self.tone_curve_combo = QComboBox()
        self.tone_curve_combo.setMinimumWidth(0)
        self.tone_curve_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.tone_curve_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.tone_curve_combo.currentTextChanged.connect(self.on_tone_curve_selected)
        reload_curve_button = QPushButton("再読み込み")
        reload_curve_button.clicked.connect(self.reload_tone_curves)
        open_curve_dir_button = QPushButton("フォルダ")
        open_curve_dir_button.setToolTip("curフォルダを開く")
        open_curve_dir_button.clicked.connect(self.open_curve_dir)
        curve_form.addRow("トーンカーブ", self.tone_curve_combo)
        curve_buttons = QHBoxLayout()
        curve_buttons.addWidget(reload_curve_button)
        curve_buttons.addWidget(open_curve_dir_button)
        curve_form.addRow("", curve_buttons)
        self.tone_curve_channel_combo = QComboBox()
        for channel in CURVE_CHANNELS:
            self.tone_curve_channel_combo.addItem(CURVE_CHANNEL_LABELS[channel], channel)
        self.tone_curve_channel_combo.currentIndexChanged.connect(self.on_tone_curve_channel_changed)
        curve_form.addRow("チャンネル", self.tone_curve_channel_combo)
        image_adjust_layout.addLayout(curve_form)
        self.tone_curve_graph = ToneCurveGraph()
        self.tone_curve_graph.curveChanged.connect(self.on_tone_curve_graph_changed)
        image_adjust_layout.addWidget(self.tone_curve_graph)
        save_curve_button = QPushButton("保存")
        save_curve_button.clicked.connect(self.save_tone_curve_dialog)
        image_adjust_layout.addWidget(save_curve_button)
        image_adjust_layout.addWidget(self.help_label("選択中の曲線をドラッグして調整できます。保存するとcurフォルダへGIMP旧形式.curとして出力します。"))
        image_adjust_layout.addStretch(1)
        image_adjust_tab.setWidget(image_adjust_content)
        self.reload_tone_curves(select_configured=True)

        other_content = QWidget()
        other_layout = QVBoxLayout(other_content)
        language_form = QFormLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItem("日本語", "ja")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(0 if self.config_data.ui_language == "ja" else 1)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.language_label = QLabel("Language")
        self.language_label.setObjectName("languageLabel")
        language_form.addRow(self.language_label, self.language_combo)
        other_layout.addLayout(language_form)
        other_layout.addWidget(self.separator())
        self.cpu_resample_check = QCheckBox("拡大縮小を高品質に補完する")
        self.cpu_resample_check.setChecked(self.config_data.cpu_resample_cache_enabled)
        self.cpu_resample_check.stateChanged.connect(self.on_resample_settings_changed)
        other_layout.addWidget(self.cpu_resample_check)
        resample_form = QFormLayout()
        self.cpu_resample_combo = QComboBox()
        self.cpu_resample_combo.addItems(RESAMPLE_ALGORITHMS.values())
        self.cpu_resample_combo.setCurrentText(RESAMPLE_ALGORITHMS.get(self.config_data.cpu_resample_algorithm, RESAMPLE_ALGORITHMS[DEFAULT_RESAMPLE_ALGORITHM]))
        self.cpu_resample_combo.currentTextChanged.connect(self.on_resample_settings_changed)
        self.cpu_resample_combo.setEnabled(self.cpu_resample_check.isChecked())
        resample_form.addRow("表示リサンプル方式", self.cpu_resample_combo)
        other_layout.addLayout(resample_form)
        other_layout.addWidget(self.help_label("原寸と異なる表示サイズの画像を、よりきれいに見えるよう作成して保持します。オフにすると標準の高速表示になります。"))
        other_layout.addWidget(self.help_label("Lanczos3: 精細で標準的。Lanczos4: より鋭いがリンギングが出ることがあります。Bicubic: やや柔らかく自然。Area: 大きく縮小する時に安定し、ジャギーを抑えやすい方式です。"))
        other_layout.addWidget(self.help_label("Lanczos4はOpenCVがある環境ではLanczos4、ない環境ではLanczos3相当で処理します。"))
        other_layout.addWidget(self.separator())
        self.single_instance_check = QCheckBox("アプリの二重起動を禁止する")
        self.single_instance_check.setChecked(self.config_data.single_instance_enabled)
        self.single_instance_check.stateChanged.connect(self.on_general_settings_changed)
        other_layout.addWidget(self.single_instance_check)
        self.cleanup_check = QCheckBox("次回起動時に古い一時ファイルを削除")
        self.cleanup_check.setChecked(self.config_data.cleanup_temp_on_start)
        self.cleanup_check.stateChanged.connect(self.on_cleanup_changed)
        other_layout.addWidget(self.cleanup_check)
        other_layout.addStretch(1)
        other_tab.setWidget(other_content)

        keyconfig_tab.setWidget(self.build_keyconfig_tab())

        self.normalize_form_labels(form, form3, viewer_form, background_form, compare_form, view_form, page_position_form, curve_form, language_form, resample_form)

        tab_index = {"realcugan": 0, "general": 1, "image_adjust": 2, "other": 3, "keyconfig": 4}.get(self.config_data.settings_tab, 0)
        self.tabs.setCurrentIndex(tab_index)
        self.apply_engine_ui()
        QTimer.singleShot(0, self.apply_language)
        return root

    def build_keyconfig_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.help_label("設定値をクリックすると割当を変更できます。Escを入力すると未割当に戻ります。Spaceは次ページ、Backspaceは前ページとして固定です。"))
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 0)
        grid.addWidget(QLabel("機能"), 0, 0)
        grid.addWidget(QLabel("キーボード"), 0, 1)
        grid.addWidget(QLabel("マウス"), 0, 2)
        self.key_binding_buttons: dict[tuple[str, str], QPushButton] = {}
        for row, (action_id, label) in enumerate(ACTION_DEFS, start=1):
            grid.addWidget(QLabel(label), row, 0)
            for column, kind in ((1, "keyboard"), (2, "mouse")):
                button = QPushButton()
                button.setMinimumWidth(132)
                button.clicked.connect(lambda _checked=False, aid=action_id, k=kind: self.edit_key_binding(aid, k))
                self.key_binding_buttons[(action_id, kind)] = button
                grid.addWidget(button, row, column)
        layout.addLayout(grid)
        reset_button = QPushButton("キーコンフィグを初期値に戻す")
        reset_button.clicked.connect(self.reset_key_bindings)
        layout.addWidget(reset_button)
        layout.addStretch(1)
        self.refresh_keyconfig_buttons()
        return content

    def help_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #666;")
        return label

    def normalize_form_labels(self, *forms: QFormLayout) -> None:
        for form in forms:
            form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
            form.setHorizontalSpacing(8)
            for row in range(form.rowCount()):
                item = form.itemAt(row, QFormLayout.LabelRole)
                if item is None:
                    continue
                widget = item.widget()
                if widget is not None:
                    widget.setFixedWidth(FORM_LABEL_WIDTH)

    def separator(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.HLine)
        frame.setFrameShadow(QFrame.Sunken)
        return frame

    def ui_language(self) -> str:
        combo = getattr(self, "language_combo", None)
        if combo is not None:
            return combo.currentData() or "ja"
        return self.config_data.ui_language if self.config_data.ui_language in {"ja", "en"} else "ja"

    def tr_ui(self, text: str) -> str:
        if self.ui_language() == "en":
            return UI_TEXT_EN.get(text, text)
        return UI_TEXT_JA.get(text, text)

    def apply_language(self) -> None:
        if not hasattr(self, "side_panel"):
            return
        self._translate_widget_tree(self.side_panel)
        if hasattr(self, "tabs"):
            for index in range(self.tabs.count()):
                self.tabs.setTabText(index, self.tr_ui(self.tabs.tabText(index)))
        if hasattr(self, "pin_button"):
            self.pin_button.setText(self.tr_ui("固定中" if self.pin_button.isChecked() else "自動表示"))
        if hasattr(self, "language_label"):
            self.language_label.setText("Language")
        if hasattr(self, "tone_curve_channel_combo"):
            current = self.tone_curve_channel_combo.currentData() or "value"
            self.tone_curve_channel_combo.blockSignals(True)
            self.tone_curve_channel_combo.clear()
            for channel in CURVE_CHANNELS:
                self.tone_curve_channel_combo.addItem(self.tr_ui(CURVE_CHANNEL_LABELS[channel]), channel)
            index = self.tone_curve_channel_combo.findData(current)
            self.tone_curve_channel_combo.setCurrentIndex(max(0, index))
            self.tone_curve_channel_combo.blockSignals(False)
        self.update_zoom_label(self.viewer.current_scale() if hasattr(self, "viewer") else 1.0)
        self.update_page_position_slider()
        self.refresh_keyconfig_buttons()

    def _translate_widget_tree(self, widget: QWidget) -> None:
        for child in widget.findChildren(QWidget):
            if child.objectName() == "languageLabel":
                continue
            if isinstance(child, QLabel):
                child.setText(self.tr_ui(child.text()))
            elif isinstance(child, QCheckBox):
                child.setText(self.tr_ui(child.text()))
            elif isinstance(child, QPushButton):
                child.setText(self.tr_ui(child.text()))

    def binding_text(self, kind: str, binding: dict | None) -> str:
        text = key_binding_text(binding) if kind == "keyboard" else mouse_binding_text(binding)
        if self.ui_language() == "en":
            for source, target in UI_TEXT_EN.items():
                text = text.replace(source, target)
        else:
            for source, target in UI_TEXT_JA.items():
                text = text.replace(source, target)
        return text

    def state_text(self, state: str) -> str:
        if self.ui_language() != "en":
            return state
        return {
            "表示中": "Displaying",
            "対象外": "Skipped",
            "処理済み": "Processed",
            "処理中": "Processing",
            "処理対象外": "Skipped",
        }.get(state, state.replace("待ち", " waiting"))

    def _restore_geometry(self) -> None:
        if not self._restore_window_rect(self.config_data.window_rect):
            self.resize(1200, 760)
            self._center_on_available_screen()
        if self.config_data.window_maximized:
            self.setWindowState(self.windowState() | Qt.WindowMaximized)
        self._apply_splitter_panel_width()
        if self.config_data.side_panel_pinned:
            self.attach_side_panel_to_splitter(visible=self.config_data.side_panel_visible)
        else:
            self.detach_side_panel_for_overlay(visible=False)

    def _available_virtual_geometry(self) -> QRect:
        available = QRect()
        for screen in QApplication.screens():
            available = screen.availableGeometry() if available.isNull() else available.united(screen.availableGeometry())
        if available.isNull() and QApplication.primaryScreen():
            available = QApplication.primaryScreen().availableGeometry()
        return available

    def _restore_window_rect(self, values: list[int] | None) -> bool:
        if not values or len(values) != 4:
            return False
        available = self._available_virtual_geometry()
        if available.isNull():
            return False
        try:
            x, y, width, height = [int(value) for value in values]
        except (TypeError, ValueError):
            return False
        width = max(640, min(width, max(640, available.width())))
        height = max(480, min(height, max(480, available.height())))
        x = max(available.left(), min(x, available.right() - width + 1))
        y = max(available.top(), min(y, available.bottom() - height + 1))
        self.setGeometry(x, y, width, height)
        return True

    def _center_on_available_screen(self) -> None:
        available = self._available_virtual_geometry()
        if available.isNull():
            return
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def persist_config(self, log: bool = False) -> None:
        if getattr(self, "initializing", False):
            return
        self.save_active_command_template()
        self.config_data.engine = self.current_engine()
        self.config_data.command_template = self.config_data.realcugan_command_template
        self.config_data.scale = int(self.scale_combo.currentText())
        self.config_data.denoise = int(self.denoise_combo.currentText())
        self.config_data.tile = self.tile_spin.value()
        self.config_data.realesrgan_model = self.realesrgan_model_combo.currentText()
        self.config_data.realcugan_prefetch_count = self.realcugan_prefetch_spin.value()
        self.config_data.viewer_prefetch_count = self.viewer_prefetch_spin.value()
        if not self.archive_mode_active():
            self.config_data.save_upscaled_to_scale_folder = self.save_scale_check.isChecked()
            self.config_data.use_scale_folder_cache = self.use_scale_cache_check.isChecked()
        self.config_data.skip_realcugan_for_tall_images = self.skip_tall_check.isChecked()
        self.config_data.skip_realcugan_height_threshold = self.skip_height_spin.value()
        self.config_data.background_color = self.background_edit.text().strip() or "#000000"
        self.config_data.cpu_resample_cache_enabled = self.cpu_resample_check.isChecked()
        self.config_data.cpu_resample_algorithm = self.current_resample_algorithm()
        self.config_data.compare_enabled = self.compare_check.isChecked()
        self.config_data.compare_split = self.compare_slider.value()
        self.config_data.compare_line_color = self.compare_line_edit.text().strip() or "#ffffff"
        self.config_data.compare_line_width = self.compare_line_width_spin.value()
        self.config_data.compare_swap_sides = self.compare_swap_check.isChecked()
        self.config_data.compare_shift_drag_moves_boundary = self.compare_shift_check.isChecked()
        self.config_data.dual_page_enabled = bool(getattr(self, "dual_page_enabled", False))
        self.config_data.dual_page_landscape_single = self.dual_page_landscape_check.isChecked()
        self.config_data.tone_curve_enabled = self.tone_curve_check.isChecked()
        self.config_data.tone_curve_file = self.current_tone_curve.path if self.current_tone_curve is not None else ""
        self.config_data.page_scroll_interval_ms = self.page_interval_spin.value()
        self.config_data.wrap_page_navigation = self.wrap_page_check.isChecked()
        self.config_data.preserve_view_on_page_navigation = self.preserve_view_check.isChecked()
        self.config_data.invert_page_position_slider = self.invert_page_position_check.isChecked()
        self.config_data.horizontal_wheel_navigation = self.horizontal_wheel_check.isChecked()
        self.config_data.horizontal_wheel_inverted = self.horizontal_wheel_invert_check.isChecked()
        self.config_data.hide_cursor_in_fullscreen = self.hide_cursor_fullscreen_check.isChecked()
        self.config_data.show_log_panel = self.show_log_check.isChecked()
        self.config_data.show_profile_panel = self.show_profile_check.isChecked()
        if hasattr(self, "language_combo"):
            self.config_data.ui_language = self.language_combo.currentData() or "ja"
        self.config_data.thumbnail_enabled = self.thumbnail_enabled_check.isChecked()
        self.config_data.thumbnail_pinned = self.thumbnail_pinned_check.isChecked()
        self.config_data.thumbnail_height = self.clamped_thumbnail_height()
        self.config_data.thumbnail_size = self.thumbnail_icon_size()
        self.config_data.single_instance_enabled = self.single_instance_check.isChecked()
        self.config_data.cleanup_temp_on_start = self.cleanup_check.isChecked()
        self.config_data.settings_tab = ["realcugan", "general", "image_adjust", "other", "keyconfig"][max(0, min(4, self.tabs.currentIndex()))]
        if not self.is_app_fullscreen():
            rect = self.normalGeometry() if self.isMaximized() else self.geometry()
            if rect.isValid():
                self.config_data.window_rect = [rect.x(), rect.y(), rect.width(), rect.height()]
                self.config_data.window_maximized = self.isMaximized()
        self.config_data.window_geometry = ""
        side_panel = getattr(self, "side_panel", None)
        pin_button = getattr(self, "pin_button", None)
        self.config_data.side_panel_visible = (
            self.side_panel_visible_before_fullscreen
            if self.is_app_fullscreen()
            else side_panel.isVisible() if side_panel is not None else self.config_data.side_panel_visible
        )
        self.config_data.side_panel_pinned = pin_button.isChecked() if pin_button is not None else self.config_data.side_panel_pinned
        splitter = getattr(self, "splitter", None)
        if side_panel is not None:
            self.config_data.side_panel_width = int(self.side_panel_width)
        if splitter is not None and not self.side_panel_overlay:
            sizes = self.splitter.sizes()
            if len(sizes) >= 2 and sizes[1] >= 80:
                self.config_data.splitter_sizes = sizes
        save_config(self.config_data)
        if log:
            self.append_log(f"Saved settings: {CONFIG_PATH}")

    def _apply_settings_to_viewer(self) -> None:
        self.viewer.set_background(self.config_data.background_color)
        self.viewer.set_resample_options(self.config_data.cpu_resample_cache_enabled, self.config_data.cpu_resample_algorithm)
        self.viewer.set_key_bindings(self.config_data.key_bindings)
        self.viewer.set_pixmap_cache_limit(self.viewer_prefetch_spin.value() * 2 + 8)
        self.viewer.set_horizontal_wheel_options(
            self.config_data.horizontal_wheel_navigation,
            self.config_data.horizontal_wheel_inverted,
        )
        self.viewer.set_tone_curve_options(self.config_data.tone_curve_enabled, self.current_tone_curve)
        self.update_thumbnail_metrics()
        self.layout_viewer_host()
        self.on_compare_changed()

    def current_resample_algorithm(self) -> str:
        label = self.cpu_resample_combo.currentText() if hasattr(self, "cpu_resample_combo") else RESAMPLE_ALGORITHMS[DEFAULT_RESAMPLE_ALGORITHM]
        for key, value in RESAMPLE_ALGORITHMS.items():
            if label == value:
                return key
        return DEFAULT_RESAMPLE_ALGORITHM

    def refresh_keyconfig_buttons(self) -> None:
        buttons = getattr(self, "key_binding_buttons", {})
        self.duplicate_keyboard_bindings = duplicate_binding_signatures(self.config_data.key_bindings, "keyboard")
        keyboard_duplicates = self.duplicate_keyboard_bindings
        mouse_duplicates = duplicate_binding_signatures(self.config_data.key_bindings, "mouse")
        for action_id, _label in ACTION_DEFS:
            bindings = self.config_data.key_bindings.get(action_id, {"keyboard": None, "mouse": None})
            keyboard_button = buttons.get((action_id, "keyboard"))
            mouse_button = buttons.get((action_id, "mouse"))
            if keyboard_button is not None:
                binding = bindings.get("keyboard")
                duplicate = keyboard_signature(binding) in keyboard_duplicates
                keyboard_button.setText((("Duplicate: " if self.ui_language() == "en" else "重複: ") if duplicate else "") + self.binding_text("keyboard", binding))
                keyboard_button.setStyleSheet("background-color: #7a2020; color: white;" if duplicate else "")
                keyboard_button.setToolTip(self.tr_ui("重複しているため、この割当は無効です。") if duplicate else "")
            if mouse_button is not None:
                binding = bindings.get("mouse")
                duplicate = mouse_signature(binding) in mouse_duplicates
                mouse_button.setText((("Duplicate: " if self.ui_language() == "en" else "重複: ") if duplicate else "") + self.binding_text("mouse", binding))
                mouse_button.setStyleSheet("background-color: #7a2020; color: white;" if duplicate else "")
                mouse_button.setToolTip(self.tr_ui("重複しているため、この割当は無効です。") if duplicate else "")

    def edit_key_binding(self, action_id: str, kind: str) -> None:
        bindings = self.config_data.key_bindings.setdefault(action_id, {"keyboard": None, "mouse": None})
        action_label = dict(ACTION_DEFS).get(action_id, action_id)
        action_label = self.tr_ui(action_label)
        title = f"{action_label} - {self.tr_ui('キーボード' if kind == 'keyboard' else 'マウス')}"
        dialog = KeyBindingDialog(self, title, kind, bindings.get(kind))
        if dialog.exec() == QDialog.Accepted:
            bindings[kind] = dialog.binding
            self.config_data.key_bindings = normalize_key_bindings(self.config_data.key_bindings)
            self.viewer.set_key_bindings(self.config_data.key_bindings)
            self.refresh_keyconfig_buttons()
            self.persist_config()

    def reset_key_bindings(self) -> None:
        self.config_data.key_bindings = default_key_bindings()
        self.viewer.set_key_bindings(self.config_data.key_bindings)
        self.refresh_keyconfig_buttons()
        self.persist_config()

    def update_thumbnail_metrics(self) -> None:
        if not hasattr(self, "thumbnail_list"):
            return
        size = self.thumbnail_icon_size()
        size_changed = size != getattr(self, "thumbnail_render_size", size)
        self.thumbnail_render_size = size
        self.config_data.thumbnail_size = size
        self.thumbnail_list.setIconSize(QSize(size, size))
        self.thumbnail_list.setGridSize(QSize(size + 28, size + 34))
        self.thumbnail_list.setFixedHeight(max(THUMBNAIL_MIN_HEIGHT - 8, self.thumbnail_panel_height() - 8))
        self.thumbnail_list.setLayoutDirection(Qt.RightToLeft if self.invert_page_position_check.isChecked() else Qt.LeftToRight)
        if size_changed and self.thumbnail_items and self.thumbnails_enabled():
            self.thumbnail_resize_refresh_timer.start(120 if self.thumbnail_resizing else 1)

    def refresh_thumbnail_icons_for_size(self) -> None:
        if not self.thumbnails_enabled() or not self.thumbnail_items:
            return
        self.thumbnail_generation += 1
        self.clear_thumbnail_queue()
        self.thumbnail_ready_indexes.clear()
        for item in self.thumbnail_items:
            if item is not None:
                item.setIcon(QIcon())
        self.schedule_thumbnail_prefetch()

    def clear_thumbnail_queue(self) -> None:
        with self.thumbnail_queue.mutex:
            self.thumbnail_queue.queue.clear()
        self.thumbnail_pending.clear()

    def rebuild_thumbnail_items(self) -> None:
        if not hasattr(self, "thumbnail_list"):
            return
        self.thumbnail_generation += 1
        self.thumbnail_rebuild_timer.stop()
        self.clear_thumbnail_queue()
        self.thumbnail_ready_indexes.clear()
        self.thumbnail_list.clear()
        self.thumbnail_items = []
        if not self.thumbnails_enabled() or not self.image_paths:
            self.layout_viewer_host()
            return
        self.update_thumbnail_metrics()
        self.thumbnail_items = [None] * len(self.image_paths)
        self.thumbnail_rebuild_index = 0
        self.continue_thumbnail_rebuild()
        self.schedule_thumbnail_prefetch()
        self.layout_viewer_host()

    def continue_thumbnail_rebuild(self) -> None:
        if not self.thumbnails_enabled() or not self.image_paths:
            return
        started = time.perf_counter()
        batch = 0
        while self.thumbnail_rebuild_index < len(self.image_paths) and batch < 160:
            index = self.thumbnail_rebuild_index
            path = self.image_paths[index]
            item = QListWidgetItem(str(index + 1))
            item.setData(Qt.UserRole, index)
            item.setToolTip(self.display_name(path))
            self.thumbnail_list.addItem(item)
            self.thumbnail_items[index] = item
            self.thumbnail_rebuild_index += 1
            batch += 1
        self.update_thumbnail_selection(scroll=False, schedule=False)
        self.record_profile("サムネイル項目生成(UI)", (time.perf_counter() - started) * 1000)
        if self.thumbnail_rebuild_index < len(self.image_paths):
            self.thumbnail_rebuild_timer.start(1)

    def schedule_thumbnail_prefetch(self) -> None:
        if not self.thumbnails_enabled() or not self.image_paths:
            return
        self.thumbnail_generation += 1
        self.clear_thumbnail_queue()
        current = max(0, self.current_index)
        limit = min(len(self.image_paths), max(80, self.viewer_prefetch_spin.value() * 2 + 20))
        ordered: list[int] = []
        for distance in range(len(self.image_paths)):
            candidates = [current] if distance == 0 else [current + distance, current - distance]
            for index in candidates:
                if 0 <= index < len(self.image_paths):
                    ordered.append(index)
                    if len(ordered) >= limit:
                        break
            if len(ordered) >= limit:
                break
        for index in ordered:
            if index in self.thumbnail_ready_indexes:
                continue
            with self.thumbnail_lock:
                self.thumbnail_sequence += 1
                sequence = self.thumbnail_sequence
            priority = abs(index - current)
            self.thumbnail_pending.add(index)
            self.thumbnail_queue.put((priority, sequence, self.thumbnail_generation, index, str(self.image_paths[index])))

    def _thumbnail_worker_loop(self) -> None:
        while True:
            priority, sequence, generation, index, path_text = self.thumbnail_queue.get()
            if getattr(self, "closing", False):
                return
            if generation != self.thumbnail_generation:
                continue
            started = time.perf_counter()
            image = QImage(path_text)
            size = int(self.config_data.thumbnail_size)
            if not image.isNull():
                image = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.signals.profile_event.emit("サムネイル生成", (time.perf_counter() - started) * 1000)
            self.signals.thumbnail_done.emit(generation, index, image)

    def on_thumbnail_done(self, generation: int, index: int, image: QImage) -> None:
        self.thumbnail_pending.discard(index)
        if generation != self.thumbnail_generation or index < 0 or index >= len(self.thumbnail_items):
            return
        item = self.thumbnail_items[index]
        if item is None:
            return
        if not image.isNull():
            started = time.perf_counter()
            item.setIcon(QIcon(QPixmap.fromImage(image)))
            self.record_profile("サムネイル反映(UI)", (time.perf_counter() - started) * 1000)
        self.thumbnail_ready_indexes.add(index)

    def on_thumbnail_clicked(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.UserRole)
        if not isinstance(index, int) or index < 0 or index >= len(self.image_paths) or index == self.current_index:
            return
        scroll_bar = self.thumbnail_list.horizontalScrollBar()
        scroll_value = scroll_bar.value()
        self.last_navigation_step = 1 if index > self.current_index else -1
        self.current_index = index
        self.display_current_image(preserve_view=self.preserve_view_check.isChecked(), navigation=True, scroll_thumbnail=False)
        scroll_bar.setValue(scroll_value)

    def update_thumbnail_selection(self, scroll: bool = True, schedule: bool = True) -> None:
        if not hasattr(self, "thumbnail_list") or self.current_index < 0 or self.current_index >= len(self.thumbnail_items):
            return
        item = self.thumbnail_items[self.current_index]
        if item is None:
            return
        scroll_bar = self.thumbnail_list.horizontalScrollBar()
        scroll_value = scroll_bar.value() if not scroll else None
        self.thumbnail_list.blockSignals(True)
        self.thumbnail_list.setCurrentItem(item)
        self.thumbnail_list.blockSignals(False)
        if scroll:
            self.thumbnail_list.scrollToItem(item, QAbstractItemView.EnsureVisible)
        elif scroll_value is not None:
            scroll_bar.setValue(scroll_value)
            QTimer.singleShot(0, lambda bar=scroll_bar, value=scroll_value: bar.setValue(value))
        if schedule and self.thumbnails_enabled():
            self.schedule_thumbnail_prefetch()

    def on_thumbnail_settings_changed(self) -> None:
        enabled = self.thumbnail_enabled_check.isChecked()
        self.thumbnail_pinned_check.setEnabled(enabled)
        self.config_data.thumbnail_enabled = enabled
        self.config_data.thumbnail_pinned = self.thumbnail_pinned_check.isChecked()
        self.thumbnail_height = self.clamped_thumbnail_height()
        self.config_data.thumbnail_size = self.thumbnail_icon_size()
        self.update_thumbnail_metrics()
        if enabled:
            self.rebuild_thumbnail_items()
        else:
            self.thumbnail_generation += 1
            self.thumbnail_rebuild_timer.stop()
            self.clear_thumbnail_queue()
            self.thumbnail_list.clear()
            self.thumbnail_items.clear()
            self.thumbnail_ready_indexes.clear()
        self.layout_viewer_host()
        self.persist_config()

    def update_page_position_slider(self) -> None:
        slider = getattr(self, "page_position_slider", None)
        if slider is None:
            return
        label = getattr(self, "page_position_count_label", None)
        slider.blockSignals(True)
        if self.image_paths and self.current_index >= 0:
            slider.setEnabled(True)
            total = len(self.image_paths)
            if slider.minimum() != 1 or slider.maximum() != total:
                slider.setRange(1, total)
            value = self.current_index + 1
            if slider.value() != value:
                slider.setValue(value)
            if label is not None:
                label.setText(f"{value}/{total}")
        else:
            if slider.value() != 0:
                slider.setValue(0)
            if slider.minimum() != 0 or slider.maximum() != 0:
                slider.setRange(0, 0)
            slider.setEnabled(False)
            if label is not None:
                label.setText("0/0")
        slider.blockSignals(False)

    def on_page_position_slider_changed(self, value: int) -> None:
        if not self.image_paths or value <= 0:
            return
        index = max(0, min(len(self.image_paths) - 1, value - 1))
        if index == self.current_index:
            return
        self.last_navigation_step = 1 if index > self.current_index else -1
        self.current_index = index
        self.display_current_image(preserve_view=self.preserve_view_check.isChecked(), navigation=True)

    def on_page_position_slider_direction_changed(self) -> None:
        self.page_position_slider.setInvertedAppearance(self.invert_page_position_check.isChecked())
        self.update_thumbnail_metrics()
        if self.dual_page_enabled and self.image_paths:
            self.display_current_image(preserve_view=True)
        self.persist_config()

    def current_engine(self) -> str:
        label = self.engine_combo.currentText() if hasattr(self, "engine_combo") else ENGINE_LABELS[ENGINE_REALCUGAN]
        for engine, engine_label in ENGINE_LABELS.items():
            if label == engine_label:
                return engine
        return ENGINE_REALCUGAN

    def default_template_for_engine(self, engine: str) -> str:
        return DEFAULT_REALESRGAN_TEMPLATE if engine == ENGINE_REALESRGAN else DEFAULT_REALCUGAN_TEMPLATE

    def active_command_template(self) -> str:
        return self.config_data.realesrgan_command_template if self.current_engine() == ENGINE_REALESRGAN else self.config_data.realcugan_command_template

    def engine_label(self) -> str:
        return ENGINE_LABELS.get(self.current_engine(), ENGINE_LABELS[ENGINE_REALCUGAN])

    def effective_scale(self) -> int:
        return REALESRGAN_FIXED_SCALE if self.current_engine() == ENGINE_REALESRGAN else int(self.scale_combo.currentText())

    def save_active_command_template(self) -> None:
        if not hasattr(self, "command_edit"):
            return
        text = self.command_edit.text().strip() or self.default_template_for_engine(self.current_engine())
        if self.current_engine() == ENGINE_REALESRGAN:
            self.config_data.realesrgan_command_template = text
        else:
            self.config_data.realcugan_command_template = text

    def apply_engine_ui(self) -> None:
        if not hasattr(self, "engine_combo"):
            return
        engine = self.current_engine()
        self.scale_combo.setEnabled(engine == ENGINE_REALCUGAN)
        self.denoise_combo.setEnabled(engine == ENGINE_REALCUGAN)
        self.denoise_help.setEnabled(engine == ENGINE_REALCUGAN)
        self.realesrgan_model_combo.setEnabled(engine == ENGINE_REALESRGAN)
        self.realesrgan_model_help.setEnabled(engine == ENGINE_REALESRGAN)
        self.realesrgan_model_detail.setEnabled(engine == ENGINE_REALESRGAN)
        self.command_edit.blockSignals(True)
        self.command_edit.setText(self.active_command_template())
        self.command_edit.blockSignals(False)

    def append_log(self, text: str) -> None:
        self.log_edit.append(text)

    def append_log_if_visible(self, text: str) -> None:
        if getattr(self, "closing", False):
            return
        if self.show_log_panel:
            self.append_log(text)

    def record_profile(self, name: str, elapsed_ms: float) -> None:
        if getattr(self, "closing", False):
            return
        if elapsed_ms < 0:
            return
        stats = self.profile_stats.setdefault(name, {"count": 0.0, "total": 0.0, "last": 0.0, "max": 0.0})
        stats["count"] += 1.0
        stats["total"] += float(elapsed_ms)
        stats["last"] = float(elapsed_ms)
        stats["max"] = max(stats["max"], float(elapsed_ms))
        profile_check = getattr(self, "show_profile_check", None)
        if profile_check is not None and profile_check.isChecked() and not self.profile_update_timer.isActive():
            self.profile_update_timer.start(PROFILE_UPDATE_INTERVAL_MS)

    def update_profile_panel(self) -> None:
        if not hasattr(self, "profile_panel"):
            return
        profile_check = getattr(self, "show_profile_check", None)
        if profile_check is None or not profile_check.isChecked():
            self.profile_panel.hide()
            return
        lines = []
        for name, stats in sorted(self.profile_stats.items()):
            count = max(1.0, stats["count"])
            avg = stats["total"] / count
            lines.append(f"{name}: last {stats['last']:.1f} ms / avg {avg:.1f} ms / max {stats['max']:.1f} ms")
        empty = "Profile: no measurements yet" if self.ui_language() == "en" else "プロファイル: まだ計測値がありません"
        self.profile_panel.setText("\n".join(lines[-8:]) if lines else empty)
        self.profile_panel.show()

    def set_progress_bar(self, bar: QProgressBar, value: int, total: int, label: str) -> None:
        if not self.show_log_panel:
            return
        if getattr(self, "closing", False):
            return
        total = max(0, int(total))
        value = max(0, min(int(value), total))
        if total <= 0:
            bar.setRange(0, 1)
            bar.setValue(0)
            bar.setFormat("0/0")
            return
        bar.setRange(0, total)
        bar.setValue(value)
        bar.setFormat(f"{value}/{total}")

    def update_prefetch_progress_bars(self, viewer_plan: list[Path] | None = None, engine_plan: list[Path] | None = None) -> None:
        if not self.show_log_panel:
            return
        engine_plan = engine_plan if engine_plan is not None else self.prefetch_engine_plan
        original_done = len(self.original_cache)
        original_pending = sum(1 for path in self.prefetching_original_paths if path not in self.original_cache)
        original_total = original_done + original_pending
        self.set_progress_bar(self.original_prefetch_bar, original_done, original_total, "拡大前メモリ読込")

        engine_total = len(engine_plan)
        engine_done = sum(1 for path in engine_plan if self.normalized_path(path) in self.prefetch_engine_done_paths)
        self.set_progress_bar(self.upscale_progress_bar, engine_done, engine_total, "拡大画像生成")

        processed_done = len(self.processed_cache)
        processed_pending = sum(1 for key in self.prefetching_processed_keys if key not in self.processed_cache)
        processed_total = processed_done + processed_pending
        self.set_progress_bar(self.processed_prefetch_bar, processed_done, processed_total, "拡大後メモリ読込")

        pixmap_done = len(self.viewer.pixmap_cache)
        pixmap_total = pixmap_done + len(self.viewer.pixmap_prefetch_keys)
        self.set_progress_bar(self.pixmap_prefetch_bar, pixmap_done, pixmap_total, "表示用QPixmap")

    def pixmap_progress_key(self, kind: str, path: Path) -> tuple:
        return (
            kind,
            self.normalized_path_text(path),
            self.current_engine(),
            self.effective_scale(),
            int(self.denoise_combo.currentText()) if self.current_engine() == ENGINE_REALCUGAN else 0,
            self.tile_spin.value(),
            self.realesrgan_model_combo.currentText() if self.current_engine() == ENGINE_REALESRGAN else "",
            self.viewer.display_rotation % 360,
            self.viewer.display_flip_horizontal,
            self.viewer.display_flip_vertical,
        )

    def on_pixmap_prefetch_progress(self, warmed: int, remaining: int, cache_count: int, elapsed_ms: float) -> None:
        self.record_profile("QPixmap生成(UI)", elapsed_ms)
        if not self.show_log_panel:
            return
        self.pixmap_prefetch_log_accum += warmed
        self.update_prefetch_progress_bars()
        if remaining == 0 or self.pixmap_prefetch_log_accum >= 25:
            self.append_log(
                f"Pixmap prefetch: warmed +{self.pixmap_prefetch_log_accum}, remaining={remaining}, pixmaps={cache_count}"
            )
            self.pixmap_prefetch_log_accum = 0

    def apply_log_visibility(self) -> None:
        log_visible = bool(self.show_log_panel)
        profile_visible = bool(self.show_profile_check.isChecked())
        self.log_container.setVisible(log_visible)
        self.log_container.setMaximumHeight(16777215 if log_visible else 0)
        self.log_container.setMinimumHeight(0)
        if hasattr(self, "profile_panel"):
            self.profile_panel.setVisible(profile_visible)
        if hasattr(self, "prefetch_progress_panel"):
            self.prefetch_progress_panel.setVisible(log_visible)
        if hasattr(self, "log_label"):
            self.log_label.setVisible(log_visible)
        if hasattr(self, "log_edit"):
            self.log_edit.setVisible(log_visible)
        if profile_visible:
            self.update_profile_panel()
        if log_visible:
            self.update_prefetch_progress_bars()
            if self.image_paths:
                self.request_schedule_prefetch(0)

    def on_log_visibility_changed(self) -> None:
        self.show_log_panel = self.show_log_check.isChecked()
        self.apply_log_visibility()
        self.persist_config()

    def on_profile_visibility_changed(self) -> None:
        self.update_profile_panel()
        self.apply_log_visibility()
        self.persist_config()

    def open_path(self, path: Path) -> None:
        path = path.resolve()
        if path.is_file() and path.suffix.lower() in ARCHIVE_EXTENSIONS:
            self.open_archive(path)
            return
        self.leave_archive_mode()
        if path.is_dir():
            images = self.collect_images(path)
            index = 0
        elif path.is_file() and self.is_image(path):
            images = [path]
            index = 0
        else:
            QMessageBox.information(self, APP_NAME, self.tr_ui("画像ファイル、画像フォルダ、またはアーカイブを指定してください。"))
            return
        if not images:
            QMessageBox.information(self, APP_NAME, self.tr_ui("対応画像がありません。"))
            return
        self.set_image_list(images, index)
        self.config_data.last_dir = str(images[index].parent)
        self.persist_config()
        if path.is_file() and self.is_image(path):
            self.folder_list_loading = True
            self.deferred_page_steps = 0
            self.collect_folder_images_async(path.parent, path)

    def open_path_deferred(self, path: Path) -> None:
        path = path.resolve()
        if path.is_file() and self.is_image(path):
            self.leave_archive_mode()
            self.set_image_list([path], 0, defer_work=True)
            self.folder_list_loading = True
            self.deferred_page_steps = 0
            self.config_data.last_dir = str(path.parent)
            QTimer.singleShot(0, lambda p=path: self.collect_folder_images_async(p.parent, p))
            QTimer.singleShot(0, self.persist_config)
            return
        QTimer.singleShot(0, lambda p=path: self.open_path(p))

    def set_image_list(self, images: list[Path], index: int, defer_work: bool = False) -> None:
        self.image_paths = images
        self.refresh_image_path_sets()
        self.current_index = index
        self.pending_page_steps = 0
        self.folder_list_loading = False
        self.deferred_page_steps = 0
        self.original_cache.clear()
        self.processed_cache.clear()
        self.viewer.pixmap_cache.clear()
        self.viewer.clear_pixmap_prefetch_state()
        self.prefetching_original_paths.clear()
        self.prefetching_processed_keys.clear()
        self.prefetch_viewer_plan = []
        self.prefetch_engine_plan = []
        self.prefetch_engine_done_paths.clear()
        self.prefetch_generation += 1
        self.update_prefetch_progress_bars()
        self.rebuild_thumbnail_items()
        if defer_work:
            self.display_current_image(defer_work=True)
        else:
            self.display_current_image()

    def collect_folder_images_async(self, folder: Path, selected_path: Path) -> None:
        def worker() -> None:
            started = time.perf_counter()
            images = self.collect_images(folder)
            self.signals.profile_event.emit("フォルダ画像列挙", (time.perf_counter() - started) * 1000)
            self.signals.folder_images_ready.emit(images, selected_path.resolve())

        threading.Thread(target=worker, daemon=True).start()

    def on_folder_images_ready(self, images: list[Path], selected_path: Path) -> None:
        if not images:
            self.folder_list_loading = False
            return
        try:
            selected_index = images.index(selected_path)
        except ValueError:
            self.folder_list_loading = False
            return
        if not self.image_paths or self.normalized_path(self.image_paths[self.current_index]) != selected_path:
            self.folder_list_loading = False
            return
        self.image_paths = images
        self.refresh_image_path_sets()
        self.current_index = selected_index
        self.folder_list_loading = False
        state = "Displaying" if self.ui_language() == "en" else "表示中"
        self.status_label.setText(f"{self.current_index + 1}/{len(self.image_paths)} {state}: {self.display_name(selected_path)}")
        self.update_page_position_slider()
        self.update_window_title()
        self.rebuild_thumbnail_items()
        if self.dual_page_enabled:
            self.display_current_image(preserve_view=False, navigation=True)
        self.schedule_prefetch()
        if self.deferred_page_steps:
            steps = self.deferred_page_steps
            self.deferred_page_steps = 0
            QTimer.singleShot(0, lambda s=steps: self.queue_page_steps(s))

    def refresh_image_path_sets(self) -> None:
        self.image_path_set = set()
        for path in self.image_paths:
            self.image_path_set.add(self.normalized_path(path))
        self.image_path_string_set = {str(path) for path in self.image_path_set}

    def normalized_path(self, path: Path) -> Path:
        return path if path.is_absolute() else path.resolve()

    def normalized_path_text(self, path: Path) -> str:
        return str(self.normalized_path(path))

    def display_current_image(
        self,
        defer_work: bool = False,
        preserve_view: bool = False,
        navigation: bool = False,
        scroll_thumbnail: bool = True,
    ) -> None:
        if not self.image_paths or self.current_index < 0:
            return
        profile_start = time.perf_counter()
        path = self.image_paths[self.current_index]
        source, processed, state, skipped = self.image_state_for_display(path, front=True)
        secondary_source = QImage()
        secondary_processed = None
        secondary_index = self.secondary_page_index()
        if secondary_index is not None:
            secondary_path = self.image_paths[secondary_index]
            secondary_source, secondary_processed, _secondary_state, _secondary_skipped = self.image_state_for_display(secondary_path)
        if navigation:
            self.viewer.begin_interactive_resample_delay()
        self.viewer.set_images(
            source,
            processed,
            preserve_view=preserve_view,
            secondary_source=secondary_source,
            secondary_processed=secondary_processed,
            dual_page=self.dual_page_enabled,
            dual_page_reversed=self.dual_page_reversed(),
        )
        self.viewer.pixmap_prefetch_done_keys.add(self.pixmap_progress_key("original", path))
        if processed is not None and not processed.isNull():
            self.viewer.pixmap_prefetch_done_keys.add(self.pixmap_progress_key("processed", path))
        if secondary_index is not None:
            secondary_path = self.image_paths[secondary_index]
            self.viewer.pixmap_prefetch_done_keys.add(self.pixmap_progress_key("original", secondary_path))
            if secondary_processed is not None and not secondary_processed.isNull():
                self.viewer.pixmap_prefetch_done_keys.add(self.pixmap_progress_key("processed", secondary_path))
        display_entries = self.current_display_index_entries()
        if len(display_entries) > 1:
            page_text = f"{self.current_index + 1}-{secondary_index + 1}/{len(self.image_paths)}"
            name_text = " / ".join(self.display_name(entry_path) for _entry_index, entry_path in display_entries)
        else:
            page_text = f"{self.current_index + 1}/{len(self.image_paths)}"
            name_text = self.display_name(path)
        self.status_label.setText(f"{page_text} {self.state_text(state)}: {name_text}")
        self.update_page_position_slider()
        self.update_window_title(source=source, processed=processed, skipped=skipped)
        self.update_thumbnail_selection(scroll=scroll_thumbnail)
        self.request_borderless_fullscreen_enforce()
        self.request_schedule_prefetch(0 if defer_work else PREFETCH_DEBOUNCE_MS)
        self.record_profile("表示切替", (time.perf_counter() - profile_start) * 1000)

    def update_window_title(self, source: QImage | None = None, processed: QImage | None = None, skipped: bool | None = None) -> None:
        if not self.image_paths:
            self.setWindowTitle(APP_NAME)
            return
        path = self.image_paths[self.current_index]
        display_entries = self.current_display_index_entries()
        if len(display_entries) > 1:
            names: list[str] = []
            before_parts: list[str] = []
            after_parts: list[str] = []
            for _index, entry_path in display_entries:
                entry_source = source if entry_path == path and source is not None else self.load_original(entry_path)
                entry_processed = (
                    processed
                    if entry_path == path and processed is not None
                    else self.processed_cache.get(self.processing_key(entry_path))
                )
                names.append(self.display_name(entry_path))
                before_parts.append(f"{entry_source.width()}x{entry_source.height()}")
                if entry_processed and not entry_processed.isNull():
                    after_parts.append(f"{entry_processed.width()}x{entry_processed.height()}")
                elif self.should_skip_realcugan(entry_path):
                    after_parts.append("Skipped" if self.ui_language() == "en" else "拡大処理対象外")
                else:
                    after_parts.append("Processing" if self.ui_language() == "en" else "処理中")
            secondary_index = self.secondary_page_index()
            page_text = f"{self.current_index + 1}-{secondary_index + 1} / {len(self.image_paths)}" if secondary_index is not None else f"{self.current_index + 1} / {len(self.image_paths)}"
            self.setWindowTitle(
                f"{' / '.join(names)} ({page_text}) "
                f"[{' + '.join(before_parts)}] -> [{' + '.join(after_parts)}] - {APP_NAME}"
            )
            return
        if source is None:
            source = self.load_original(path)
        if processed is None:
            processed = self.processed_cache.get(self.processing_key(path))
        is_skipped = skipped if skipped is not None else self.should_skip_realcugan(path)
        if processed and not processed.isNull():
            after = f"{processed.width()}x{processed.height()}"
        elif is_skipped:
            after = "Skipped" if self.ui_language() == "en" else "拡大処理対象外"
        else:
            after = "Processing" if self.ui_language() == "en" else "処理中"
        self.setWindowTitle(
            f"{self.display_name(path)} ({self.current_index + 1} / {len(self.image_paths)}) "
            f"[{source.width()}x{source.height()}] -> [{after}] - {APP_NAME}"
        )

    def load_original(self, path: Path) -> QImage:
        path = self.normalized_path(path)
        cached = self.original_cache.get(path)
        if cached is not None:
            self.original_cache.move_to_end(path)
            return cached
        started = time.perf_counter()
        image = QImage(str(path))
        self.record_profile("元画像読込(UI)", (time.perf_counter() - started) * 1000)
        self.original_cache[path] = image
        while len(self.original_cache) > max(6, self.config_data.viewer_prefetch_count * 2 + 3):
            self.original_cache.popitem(last=False)
        return image

    def should_skip_realcugan(self, path: Path) -> bool:
        return self.skip_tall_check.isChecked() and self.load_original(path).height() >= self.skip_height_spin.value()

    def dual_page_reversed(self) -> bool:
        check = getattr(self, "invert_page_position_check", None)
        return bool(check.isChecked() if check is not None else self.config_data.invert_page_position_slider)

    def secondary_page_index(self) -> int | None:
        if not self.dual_page_enabled or self.current_index < 0:
            return None
        if self.dual_page_landscape_single_enabled(self.current_index):
            return None
        index = self.current_index + 1
        if index < len(self.image_paths) and self.dual_page_landscape_single_enabled(index):
            return None
        return index if index < len(self.image_paths) else None

    def dual_page_landscape_single_enabled(self, index: int) -> bool:
        if not getattr(self, "dual_page_landscape_check", None) or not self.dual_page_landscape_check.isChecked():
            return False
        if index < 0 or index >= len(self.image_paths):
            return False
        image = self.load_original(self.image_paths[index])
        return not image.isNull() and image.width() > image.height()

    def current_display_index_entries(self) -> list[tuple[int, Path]]:
        if not self.image_paths or self.current_index < 0:
            return []
        entries = [(self.current_index, self.image_paths[self.current_index])]
        secondary_index = self.secondary_page_index()
        if secondary_index is not None:
            entries.append((secondary_index, self.image_paths[secondary_index]))
        if self.dual_page_reversed() and len(entries) > 1:
            entries.reverse()
        return entries

    def image_state_for_display(self, path: Path, front: bool = False) -> tuple[QImage, QImage | None, str, bool]:
        source = self.load_original(path)
        cache_key = self.processing_key(path)
        processed = self.processed_cache.get(cache_key)
        skipped = False
        if processed is None:
            existing = self.existing_processed_path(path)
            if existing is not None:
                processed = QImage(str(existing))
                if not processed.isNull():
                    self.processed_cache[cache_key] = processed
        if processed is None or processed.isNull():
            if self.should_skip_realcugan(path):
                skipped = True
                state = "対象外"
            else:
                self.enqueue_realcugan(path, front=front)
                state = f"{self.engine_label()}待ち"
            processed = None
        else:
            state = "処理済み"
        return source, processed, state, skipped

    def queue_page_steps(self, steps: int) -> None:
        if not self.image_paths or steps == 0:
            return
        if self.folder_list_loading and len(self.image_paths) <= 1:
            self.deferred_page_steps = max(-999, min(999, self.deferred_page_steps + steps))
            return
        self.pending_page_steps = steps
        if not self.page_scroll_timer.isActive():
            self._drain_page_steps()

    def _drain_page_steps(self) -> None:
        if self.pending_page_steps == 0:
            self.page_scroll_timer.stop()
            return
        step = 1 if self.pending_page_steps > 0 else -1
        index_step = step * self.page_navigation_span()
        if self.show_relative_image(index_step):
            self.pending_page_steps -= step
            if self.pending_page_steps:
                self.page_scroll_timer.start(max(0, self.page_interval_spin.value()))
        else:
            self.pending_page_steps = 0

    def page_navigation_span(self) -> int:
        if not self.dual_page_enabled:
            return 1
        return 2 if self.secondary_page_index() is not None else 1

    def show_relative_image(self, step: int) -> bool:
        next_index = self.current_index + step
        if next_index < 0 or next_index >= len(self.image_paths):
            if not self.wrap_page_check.isChecked():
                return False
            next_index %= len(self.image_paths)
        self.last_navigation_step = 1 if step > 0 else -1
        self.current_index = next_index
        self.display_current_image(preserve_view=self.preserve_view_check.isChecked(), navigation=True)
        return True

    def show_first_image(self) -> None:
        if self.image_paths:
            self.current_index = 0
            self.last_navigation_step = -1
            self.display_current_image(preserve_view=self.preserve_view_check.isChecked(), navigation=True)

    def show_last_image(self) -> None:
        if self.image_paths:
            self.current_index = len(self.image_paths) - 1
            self.last_navigation_step = 1
            self.display_current_image(preserve_view=self.preserve_view_check.isChecked(), navigation=True)

    def matching_key_action(self, event) -> str | None:
        key = event.key()
        modifiers = modifier_value(event.modifiers())
        signature = (key, modifiers)
        if signature in self.duplicate_keyboard_bindings:
            return None
        for action_id, bindings in self.config_data.key_bindings.items():
            binding = bindings.get("keyboard") if isinstance(bindings, dict) else None
            if not binding:
                continue
            if int(binding.get("key", 0)) == key and int(binding.get("modifiers", 0)) == modifiers:
                return action_id
        return None

    def perform_action(self, action_id: str) -> None:
        actions = {
            "open_image": self.open_image_dialog,
            "open_folder": self.open_folder_dialog,
            "next_page": lambda: self.queue_page_steps(1),
            "previous_page": lambda: self.queue_page_steps(-1),
            "last_page": self.show_last_image,
            "first_page": self.show_first_image,
            "toggle_fullscreen": self.toggle_fullscreen,
            "toggle_thumbnail_panel": self.toggle_thumbnail_panel,
            "toggle_side_panel": self.toggle_side_panel,
            "toggle_compare": self.toggle_compare_mode,
            "toggle_dual_page": self.toggle_dual_page_mode,
            "dual_page_shift_forward": lambda: self.shift_dual_page_alignment(True),
            "dual_page_shift_backward": lambda: self.shift_dual_page_alignment(False),
            "toggle_tone_curve": self.toggle_tone_curve_mode,
            "actual_size": self.viewer.zoom_to_actual_size,
            "fit_view": self.viewer.reset_display_state,
            "rotate_right": lambda: self.viewer.rotate_display(90),
            "rotate_left": lambda: self.viewer.rotate_display(-90),
            "flip_horizontal": lambda: self.viewer.flip_display(True),
            "flip_vertical": lambda: self.viewer.flip_display(False),
        }
        action = actions.get(action_id)
        if action is not None:
            action()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Space:
            self.queue_page_steps(1)
        elif event.key() == Qt.Key_Backspace:
            self.queue_page_steps(-1)
        else:
            action_id = self.matching_key_action(event)
            if action_id:
                self.perform_action(action_id)
            else:
                super().keyPressEvent(event)

    def toggle_compare_mode(self) -> None:
        if self.dual_page_enabled:
            return
        self.compare_check.setChecked(not self.compare_check.isChecked())
        self.on_compare_changed()

    def toggle_dual_page_mode(self) -> None:
        self.set_dual_page_enabled(not self.dual_page_enabled)

    def on_dual_page_check_changed(self) -> None:
        self.set_dual_page_enabled(self.dual_page_check.isChecked())

    def on_dual_page_landscape_changed(self) -> None:
        if self.image_paths and self.dual_page_enabled:
            self.display_current_image(preserve_view=False, navigation=True)
        self.persist_config()

    def set_dual_page_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        changed = self.dual_page_enabled != enabled
        self.dual_page_enabled = enabled
        if hasattr(self, "dual_page_check") and self.dual_page_check.isChecked() != enabled:
            self.dual_page_check.blockSignals(True)
            self.dual_page_check.setChecked(enabled)
            self.dual_page_check.blockSignals(False)
        if not changed:
            return
        if enabled and self.compare_check.isChecked():
            self.compare_check.blockSignals(True)
            self.compare_check.setChecked(False)
            self.compare_check.blockSignals(False)
        self.update_compare_controls_enabled()
        self.on_compare_changed()
        if self.image_paths:
            self.display_current_image(preserve_view=False, navigation=True)
        self.persist_config()

    def shift_dual_page_alignment(self, forward: bool) -> None:
        direction = 1 if self.dual_page_reversed() else -1
        self.show_relative_image(direction if forward else -direction)

    def toggle_tone_curve_mode(self) -> None:
        self.tone_curve_check.setChecked(not self.tone_curve_check.isChecked())
        self.on_tone_curve_settings_changed()

    def reload_tone_curves(self, select_configured: bool = False) -> None:
        CURVE_DIR.mkdir(exist_ok=True)
        curves: dict[str, ToneCurve] = {}
        for path in windows_logical_sorted(list(CURVE_DIR.glob("*.cur")), lambda item: item.name):
            curve = load_tone_curve(path)
            if curve is not None:
                curves[path.name] = curve
        if not curves:
            linear = default_tone_curve("linear")
            linear.path = ""
            curves["linear"] = linear
        self.tone_curves = curves
        combo = getattr(self, "tone_curve_combo", None)
        if combo is None:
            return
        selected_path = self.config_data.tone_curve_file if select_configured else (self.current_tone_curve.path if self.current_tone_curve else "")
        combo.blockSignals(True)
        combo.clear()
        for name, curve in curves.items():
            combo.addItem(name, curve.path)
        target_index = 0
        for index in range(combo.count()):
            if selected_path and combo.itemData(index) == selected_path:
                target_index = index
                break
        combo.setCurrentIndex(target_index)
        combo.blockSignals(False)
        self.on_tone_curve_selected()

    def on_tone_curve_selected(self) -> None:
        combo = getattr(self, "tone_curve_combo", None)
        if combo is None:
            return
        name = combo.currentText()
        self.current_tone_curve = self.tone_curves.get(name)
        if self.current_tone_curve is not None:
            self.tone_curve_graph.set_curve(self.current_tone_curve)
        self.on_tone_curve_settings_changed()

    def on_tone_curve_channel_changed(self) -> None:
        channel = self.tone_curve_channel_combo.currentData() or "value"
        self.tone_curve_graph.set_channel(channel)

    def on_tone_curve_graph_changed(self) -> None:
        self.current_tone_curve = self.tone_curve_graph.curve.copy()
        self.current_tone_curve.name = self.tone_curve_combo.currentText()
        self.current_tone_curve.path = self.tone_curve_combo.currentData() or ""
        self.on_tone_curve_settings_changed()

    def on_tone_curve_settings_changed(self) -> None:
        if getattr(self, "initializing", False) or not hasattr(self, "tone_curve_check"):
            return
        self.viewer.set_tone_curve_options(self.tone_curve_check.isChecked(), self.current_tone_curve)
        self.persist_config()

    def save_tone_curve_dialog(self) -> None:
        CURVE_DIR.mkdir(exist_ok=True)
        start = CURVE_DIR / ((self.current_tone_curve.name if self.current_tone_curve else "curve") + ".cur")
        path, _filter = QFileDialog.getSaveFileName(self, "トーンカーブを保存", str(start), "GIMP Curve (*.cur);;All files (*.*)")
        if not path:
            return
        save_path = Path(path)
        curve = self.tone_curve_graph.curve.copy()
        curve.name = save_path.stem
        curve.path = str(save_path)
        save_legacy_cur(save_path, curve)
        self.config_data.tone_curve_file = str(save_path)
        self.reload_tone_curves(select_configured=True)
        self.persist_config()

    def open_curve_dir(self) -> None:
        CURVE_DIR.mkdir(exist_ok=True)
        if os.name == "nt":
            subprocess.Popen(["explorer", str(CURVE_DIR)])

    def open_image_dialog(self) -> None:
        start = self.config_data.last_dir or str(Path.home())
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "画像を開く",
            start,
            "Images/Archives (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.zip *.cbz *.rar *.cbr *.7z *.cb7);;All files (*.*)",
        )
        if path:
            self.open_path(Path(path))

    def open_folder_dialog(self) -> None:
        start = self.config_data.last_dir or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "フォルダを開く", start)
        if path:
            self.open_path(Path(path))

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            event.acceptProposedAction()
            self.activateWindow()
            self.raise_()
            self.open_path_deferred(Path(urls[0].toLocalFile()))

    def hide_side_panel(self) -> None:
        self.side_panel.hide()
        self.persist_config()

    def show_side_panel(self) -> None:
        if self.pin_button.isChecked():
            return
        if not self.side_panel.isVisible():
            self.overlay_hide_suppressed_until = time.monotonic() + SIDE_PANEL_HIDE_GRACE_SEC
            self.detach_side_panel_for_overlay(visible=True)
            self.side_panel.show()
            self.position_overlay_side_panel()
            self.side_panel.raise_()
            self.request_borderless_fullscreen_enforce()
            self.persist_config()

    def toggle_side_panel(self) -> None:
        self.pin_button.setChecked(not self.pin_button.isChecked())

    def toggle_thumbnail_panel(self) -> None:
        if not self.thumbnails_enabled():
            self.thumbnail_enabled_check.setChecked(True)
        self.thumbnail_pinned_check.setChecked(not self.thumbnail_pinned_check.isChecked())

    def is_cursor_over_side_panel(self) -> bool:
        if not self.side_panel.isVisible():
            return False
        local = self.side_panel.mapFromGlobal(QCursor.pos())
        return self.side_panel.rect().contains(local)

    def should_hide_overlay_panel(self) -> bool:
        if self.overlay_resizing or self.overlay_modal_guard or self.pin_button.isChecked() or not self.side_panel_overlay:
            return False
        if QApplication.activePopupWidget() is not None:
            return False
        if time.monotonic() < self.overlay_hide_suppressed_until:
            return False
        local = self.side_panel.mapFromGlobal(QCursor.pos())
        rect = self.side_panel.rect()
        if not rect.adjusted(-SIDE_PANEL_HIDE_MARGIN, 0, SIDE_PANEL_HIDE_MARGIN, 0).contains(local):
            return True
        if not rect.contains(local):
            return False
        return local.x() > SIDE_PANEL_HIDE_MARGIN

    def _ensure_side_panel_width(self) -> None:
        self._apply_splitter_panel_width()

    def current_side_panel_width(self) -> int:
        if self.side_panel_overlay:
            return int(self.side_panel_width)
        sizes = self.splitter.sizes()
        if len(sizes) >= 2 and sizes[1] > 0:
            self.side_panel_width = self.clamped_side_panel_width(sizes[1])
            return self.side_panel_width
        return self.clamped_side_panel_width()

    def clamped_side_panel_width(self, width: int | None = None) -> int:
        total = max(1, self.splitter.width() if hasattr(self, "splitter") else self.width())
        maximum = max(1, total // 2)
        minimum = min(max(240, self.side_panel.minimumWidth()), maximum)
        value = int(self.side_panel_width if width is None else width)
        return max(minimum, min(value, maximum))

    def _apply_splitter_panel_width(self) -> None:
        total = self.splitter.width() or sum(self.splitter.sizes()) or self.width()
        if total <= 0:
            return
        panel_width = self.clamped_side_panel_width()
        self.adjusting_splitter = True
        self.splitter.setSizes([max(1, total - panel_width), panel_width])
        self.adjusting_splitter = False

    def attach_side_panel_to_splitter(self, visible: bool = True) -> None:
        if self.side_panel_overlay:
            self.side_panel.hide()
            self.side_panel.setParent(None)
            self.splitter.addWidget(self.side_panel)
            self.side_panel.installEventFilter(self)
            self.side_panel_overlay = False
        self.side_panel.setVisible(visible)
        if visible:
            self._apply_splitter_panel_width()
            QTimer.singleShot(0, self._apply_splitter_panel_width)

    def detach_side_panel_for_overlay(self, visible: bool = False) -> None:
        if not self.side_panel_overlay:
            if not getattr(self, "initializing", False):
                self.side_panel_width = self.current_side_panel_width()
            self.config_data.side_panel_width = self.side_panel_width
            self.side_panel.hide()
            self.side_panel.setParent(self)
            self.side_panel.installEventFilter(self)
            self.side_panel_overlay = True
            self.adjusting_splitter = True
            self.splitter.setSizes([max(1, self.splitter.width()), 0])
            self.adjusting_splitter = False
        self.position_overlay_side_panel()
        self.side_panel.setVisible(visible)

    def position_overlay_side_panel(self) -> None:
        if not self.side_panel_overlay:
            return
        central = self.centralWidget().geometry()
        width = min(self.clamped_side_panel_width(), max(1, central.width() // 2))
        self.side_panel.setGeometry(central.right() - width + 1, central.top(), width, central.height())

    def on_splitter_moved(self, _pos: int, _index: int) -> None:
        if self.adjusting_splitter or self.side_panel_overlay:
            return
        sizes = self.splitter.sizes()
        if len(sizes) < 2:
            return
        total = sum(sizes)
        max_panel = max(self.side_panel.minimumWidth(), total // 2)
        panel = min(sizes[1], max_panel)
        panel = max(self.side_panel.minimumWidth(), panel)
        if panel != sizes[1]:
            self.adjusting_splitter = True
            self.splitter.setSizes([max(1, total - panel), panel])
            self.adjusting_splitter = False
        self.side_panel_width = panel
        self.config_data.side_panel_width = panel
        self.persist_config()

    def toggle_fullscreen(self) -> None:
        if self.is_app_fullscreen():
            self._show_fullscreen_cursor()
            self.borderless_fullscreen = False
            self.fullscreen_enforce_pending = False
            self.setWindowState(Qt.WindowNoState)
            self.setWindowFlags(self.before_fullscreen_flags)
            if self.before_fullscreen_geometry.isValid():
                self.setGeometry(self.before_fullscreen_geometry)
            self.setStyleSheet("")
            self.show()
            restore_state = self.before_fullscreen_state & ~Qt.WindowFullScreen
            if restore_state != Qt.WindowNoState:
                self.setWindowState(restore_state)
            if self.pin_button.isChecked():
                self.attach_side_panel_to_splitter(visible=True)
            else:
                self.detach_side_panel_for_overlay(visible=False)
        else:
            self.before_fullscreen_geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
            self.before_fullscreen_flags = self.windowFlags()
            self.before_fullscreen_state = self.windowState() & ~Qt.WindowFullScreen
            pinned = self.pin_button.isChecked()
            self.side_panel_visible_before_fullscreen = self.side_panel.isVisible() or pinned
            if pinned:
                self.attach_side_panel_to_splitter(visible=True)
            else:
                self.detach_side_panel_for_overlay(visible=False)
                self.side_panel.hide()
                self.side_panel.setParent(None)
            self.borderless_fullscreen = True
            self.setWindowState(Qt.WindowNoState)
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self.setStyleSheet("QMainWindow { background: #000000; }")
            target = self.borderless_fullscreen_geometry()
            if target.isValid():
                self.setGeometry(target)
            self.show()
            if pinned:
                self.attach_side_panel_to_splitter(visible=True)
            else:
                self.side_panel.setParent(self)
                self.side_panel.installEventFilter(self)
                self.side_panel_overlay = True
                self.position_overlay_side_panel()
            self.raise_()
            self.request_borderless_fullscreen_enforce()
            self._apply_fullscreen_cursor()

    def borderless_fullscreen_geometry(self) -> QRect:
        screen = self.screen() or QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return QRect()
        geometry = QRect(screen.geometry())
        if os.name == "nt":
            overscan = BORDERLESS_FULLSCREEN_OVERSCAN
            geometry.adjust(-overscan, -overscan, overscan, overscan)
        return geometry

    def request_borderless_fullscreen_enforce(self) -> None:
        if not self.is_app_fullscreen() or self.fullscreen_enforce_pending:
            return
        self.fullscreen_enforce_pending = True
        QTimer.singleShot(0, self.enforce_borderless_fullscreen)

    def enforce_borderless_fullscreen(self) -> None:
        self.fullscreen_enforce_pending = False
        if not self.is_app_fullscreen():
            return
        changed_flags = False
        state = self.windowState()
        if state & Qt.WindowFullScreen:
            self.setWindowState(state & ~Qt.WindowFullScreen)
        desired_flags = Qt.Window | Qt.FramelessWindowHint
        if self.windowFlags() != desired_flags:
            self.setWindowFlags(desired_flags)
            changed_flags = True
        target = self.borderless_fullscreen_geometry()
        if target.isValid() and self.geometry() != target:
            self.setGeometry(target)
        if changed_flags or not self.isVisible():
            self.show()
        if self.side_panel_overlay:
            self.position_overlay_side_panel()

    def eventFilter(self, watched, event) -> bool:
        if watched is getattr(self, "viewer_host", None):
            if event.type() == QEvent.Resize:
                self.layout_viewer_host()
        if watched is getattr(self, "thumbnail_panel", None) or watched is getattr(self, "thumbnail_list", None) or watched is getattr(getattr(self, "thumbnail_list", None), "viewport", lambda: None)():
            if event.type() in {QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.MouseButtonRelease}:
                global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
                panel_pos = self.thumbnail_panel.mapFromGlobal(global_pos)
                if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton and panel_pos.y() <= THUMBNAIL_RESIZE_GRIP:
                    self.thumbnail_resizing = True
                    self.thumbnail_panel.setCursor(Qt.SizeVerCursor)
                    return True
                if event.type() == QEvent.MouseMove:
                    if self.thumbnail_resizing:
                        host_pos = self.viewer_host.mapFromGlobal(global_pos)
                        self.thumbnail_height = self.clamped_thumbnail_height(self.viewer_host.height() - host_pos.y())
                        self.config_data.thumbnail_height = self.thumbnail_height
                        self.config_data.thumbnail_size = self.thumbnail_icon_size()
                        self.thumbnail_hide_suppressed_until = time.monotonic() + THUMBNAIL_HIDE_GRACE_SEC
                        self.layout_viewer_host()
                        return True
                    self.thumbnail_panel.setCursor(Qt.SizeVerCursor if panel_pos.y() <= THUMBNAIL_RESIZE_GRIP else Qt.ArrowCursor)
                if event.type() == QEvent.MouseButtonRelease and self.thumbnail_resizing:
                    self.thumbnail_resizing = False
                    self.thumbnail_panel.unsetCursor()
                    self.thumbnail_hide_suppressed_until = time.monotonic() + THUMBNAIL_HIDE_GRACE_SEC
                    self.thumbnail_resize_refresh_timer.start(1)
                    self.persist_config()
                    return True
            if event.type() in {QEvent.Leave, QEvent.Hide} and not self.thumbnails_pinned():
                QTimer.singleShot(THUMBNAIL_HIDE_DELAY_MS, self.hide_thumbnail_overlay)
            elif event.type() == QEvent.MouseMove and not self.thumbnails_pinned():
                self.show_thumbnail_overlay()
        if watched is getattr(self, "side_panel", None):
            if self.side_panel_overlay and not self.pin_button.isChecked():
                if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton and event.position().x() <= 18:
                    self.overlay_resizing = True
                    self.side_panel.setCursor(Qt.SizeHorCursor)
                    return True
                if event.type() == QEvent.MouseMove:
                    if self.overlay_resizing:
                        local = self.mapFromGlobal(event.globalPosition().toPoint())
                        right = self.side_panel.geometry().right()
                        self.side_panel_width = self.clamped_side_panel_width(right - local.x() + 1)
                        self.config_data.side_panel_width = self.side_panel_width
                        self.position_overlay_side_panel()
                        return True
                    self.side_panel.setCursor(Qt.SizeHorCursor if event.position().x() <= 18 else Qt.ArrowCursor)
                if event.type() == QEvent.MouseButtonRelease and self.overlay_resizing:
                    self.overlay_resizing = False
                    self.side_panel.unsetCursor()
                    self.persist_config()
                    return True
                if event.type() in {QEvent.Leave, QEvent.Hide}:
                    QTimer.singleShot(SIDE_PANEL_HIDE_DELAY_MS, self.hide_overlay_side_panel_if_needed)
        elif watched is self.viewer and event.type() == QEvent.MouseMove:
            if self.thumbnails_enabled() and not self.thumbnails_pinned():
                trigger_margin = min(self.viewer.height(), self.thumbnail_panel_height())
                if event.position().y() >= self.viewer.height() - trigger_margin:
                    self.show_thumbnail_overlay()
                elif self.thumbnail_overlay_visible and not self.is_cursor_over_thumbnail_panel():
                    self.hide_thumbnail_overlay()
            if not self.pin_button.isChecked():
                trigger_width = min(self.clamped_side_panel_width(), max(1, self.viewer.width() // 2))
                x = event.position().x()
                if x >= self.viewer.width() - trigger_width:
                    self.show_side_panel()
                elif self.side_panel_overlay and self.side_panel.isVisible() and self.should_hide_overlay_panel():
                    self.side_panel.hide()
                    self.persist_config()
            if self.is_app_fullscreen() and self.fullscreen_cursor_hidden:
                self._show_fullscreen_cursor()
                QTimer.singleShot(1200, self._apply_fullscreen_cursor)
        return super().eventFilter(watched, event)

    def hide_overlay_side_panel_if_needed(self) -> None:
        if self.should_hide_overlay_panel():
            self.side_panel.hide()
            self.persist_config()

    def on_side_panel_pin_changed(self, pinned: bool) -> None:
        self.pin_button.setText(self.tr_ui("固定中" if pinned else "自動表示"))
        if pinned:
            self.attach_side_panel_to_splitter(visible=True)
        else:
            keep_visible = self.is_cursor_over_side_panel()
            self.overlay_hide_suppressed_until = time.monotonic() + SIDE_PANEL_HIDE_GRACE_SEC
            self.detach_side_panel_for_overlay(visible=keep_visible)
            if self.side_panel.isVisible():
                self.side_panel.raise_()
        self.persist_config()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.layout_viewer_host()
        if self.side_panel_overlay:
            self.position_overlay_side_panel()
        elif hasattr(self, "splitter"):
            self._apply_splitter_panel_width()
        self.request_borderless_fullscreen_enforce()

    def _apply_fullscreen_cursor(self) -> None:
        if self.is_app_fullscreen() and self.hide_cursor_fullscreen_check.isChecked() and not self.fullscreen_cursor_hidden:
            QApplication.setOverrideCursor(QCursor(Qt.BlankCursor))
            self.fullscreen_cursor_hidden = True

    def _show_fullscreen_cursor(self) -> None:
        if self.fullscreen_cursor_hidden:
            QApplication.restoreOverrideCursor()
            self.fullscreen_cursor_hidden = False

    def is_app_fullscreen(self) -> bool:
        return self.borderless_fullscreen

    def update_zoom_label(self, scale: float) -> None:
        percent = max(1, round(scale * 100))
        prefix = "Zoom" if self.ui_language() == "en" else "ズーム"
        self.zoom_label.setText(f"{prefix}: {percent}%")
        if hasattr(self, "zoom_slider") and not self.zoom_slider.isSliderDown():
            self.zoom_slider.blockSignals(True)
            self.zoom_slider.setValue(max(self.zoom_slider.minimum(), min(self.zoom_slider.maximum(), percent)))
            self.zoom_slider.blockSignals(False)

    def on_zoom_slider_changed(self, value: int) -> None:
        self.viewer.set_actual_zoom_percent(value)

    def on_viewer_split_changed(self, value: int) -> None:
        self.compare_slider.blockSignals(True)
        self.compare_slider.setValue(value)
        self.compare_slider.blockSignals(False)
        self.config_data.compare_split = value

    def reset_compare_split(self) -> None:
        self.compare_slider.setValue(500)
        self.on_compare_changed()

    def update_compare_controls_enabled(self) -> None:
        enabled = not bool(getattr(self, "dual_page_enabled", False))
        for widget in (
            getattr(self, "compare_check", None),
            getattr(self, "compare_slider", None),
            getattr(self, "compare_center_button", None),
            getattr(self, "compare_color_button", None),
            getattr(self, "compare_line_edit", None),
            getattr(self, "compare_line_width_spin", None),
            getattr(self, "compare_swap_check", None),
            getattr(self, "compare_shift_check", None),
        ):
            if widget is not None:
                widget.setEnabled(enabled)

    def on_compare_changed(self) -> None:
        if getattr(self, "dual_page_enabled", False) and self.compare_check.isChecked():
            self.compare_check.blockSignals(True)
            self.compare_check.setChecked(False)
            self.compare_check.blockSignals(False)
        line_color = self.compare_line_edit.text().strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", line_color):
            return
        self.viewer.set_compare(
            self.compare_check.isChecked() and not getattr(self, "dual_page_enabled", False),
            self.compare_slider.value(),
            line_color,
            self.compare_line_width_spin.value(),
            self.compare_swap_check.isChecked(),
            self.compare_shift_check.isChecked(),
        )
        self.update_compare_controls_enabled()
        self.persist_config()

    def on_background_changed(self) -> None:
        color = self.background_edit.text().strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            return
        self.viewer.set_background(color)
        self.persist_config()

    def on_resample_settings_changed(self) -> None:
        self.cpu_resample_combo.setEnabled(self.cpu_resample_check.isChecked())
        self.viewer.set_resample_options(self.cpu_resample_check.isChecked(), self.current_resample_algorithm())
        self.persist_config()

    def choose_background_color(self) -> None:
        color = self.choose_simple_color(self.background_edit.text(), "Select background color" if self.ui_language() == "en" else "背景色を選択")
        if color:
            self.background_edit.setText(color)
            self.on_background_changed()

    def choose_compare_line_color(self) -> None:
        color = self.choose_simple_color(self.compare_line_edit.text(), "Select compare divider color" if self.ui_language() == "en" else "比較境界線の色を選択")
        if color:
            self.compare_line_edit.setText(color)
            self.on_compare_changed()

    def choose_simple_color(self, current: str, title: str) -> str | None:
        self.overlay_modal_guard = True
        self.overlay_hide_suppressed_until = time.monotonic() + 3600
        if self.side_panel_overlay and not self.pin_button.isChecked() and not self.side_panel.isVisible():
            self.show_side_panel()
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        red = QSpinBox()
        green = QSpinBox()
        blue = QSpinBox()
        for spin in (red, green, blue):
            spin.setRange(0, 255)
        color = QColor(current if re.fullmatch(r"#[0-9a-fA-F]{6}", current or "") else "#000000")
        red.setValue(color.red())
        green.setValue(color.green())
        blue.setValue(color.blue())
        preview = QLabel()
        preview.setFixedHeight(40)
        hex_edit = QLineEdit(color.name().upper())

        def update_from_rgb() -> None:
            value = QColor(red.value(), green.value(), blue.value()).name().upper()
            hex_edit.blockSignals(True)
            hex_edit.setText(value)
            hex_edit.blockSignals(False)
            preview.setStyleSheet(f"background: {value}; border: 1px solid palette(mid);")

        def update_from_hex() -> None:
            value = hex_edit.text().strip()
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                return
            qcolor = QColor(value)
            for spin, component in ((red, qcolor.red()), (green, qcolor.green()), (blue, qcolor.blue())):
                spin.blockSignals(True)
                spin.setValue(component)
                spin.blockSignals(False)
            preview.setStyleSheet(f"background: {qcolor.name().upper()}; border: 1px solid palette(mid);")

        rgb_labels = (("Red", red), ("Green", green), ("Blue", blue)) if self.ui_language() == "en" else (("赤", red), ("緑", green), ("青", blue))
        for label, spin in rgb_labels:
            spin.valueChanged.connect(update_from_rgb)
            form.addRow(label, spin)
        hex_edit.editingFinished.connect(update_from_hex)
        form.addRow("HEX", hex_edit)
        layout.addWidget(preview)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("OK")
        buttons.button(QDialogButtonBox.Cancel).setText(self.tr_ui("キャンセル"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        update_from_rgb()
        try:
            if dialog.exec() == QDialog.Accepted:
                value = hex_edit.text().strip().upper()
                return value if re.fullmatch(r"#[0-9A-F]{6}", value) else None
            return None
        finally:
            self.overlay_modal_guard = False
            self.overlay_hide_suppressed_until = time.monotonic() + SIDE_PANEL_HIDE_GRACE_SEC

    def on_general_settings_changed(self) -> None:
        self.viewer.set_horizontal_wheel_options(
            self.horizontal_wheel_check.isChecked(),
            self.horizontal_wheel_invert_check.isChecked(),
        )
        self.persist_config()
        if self.is_app_fullscreen():
            if self.hide_cursor_fullscreen_check.isChecked():
                self._apply_fullscreen_cursor()
            else:
                self._show_fullscreen_cursor()

    def on_language_changed(self) -> None:
        self.config_data.ui_language = self.language_combo.currentData() or "ja"
        self.apply_language()
        self.persist_config()

    def on_settings_tab_changed(self, index: int) -> None:
        self.config_data.settings_tab = ["realcugan", "general", "image_adjust", "other", "keyconfig"][max(0, min(4, index))]
        self.persist_config()

    def on_engine_changed(self, *_args) -> None:
        previous_engine = self.config_data.engine
        previous_text = self.command_edit.text().strip()
        if previous_engine == ENGINE_REALESRGAN:
            self.config_data.realesrgan_command_template = previous_text or DEFAULT_REALESRGAN_TEMPLATE
        else:
            self.config_data.realcugan_command_template = previous_text or DEFAULT_REALCUGAN_TEMPLATE
        self.config_data.engine = self.current_engine()
        self.apply_engine_ui()
        self.on_processing_settings_changed()

    def on_cleanup_changed(self) -> None:
        self.persist_config()
        if self.cleanup_check.isChecked():
            QMessageBox.information(
                self,
                APP_NAME,
                f"次回起動時に、{APP_SHORT_NAME} が作成した古い一時フォルダと一時PNGを削除します。\n\n"
                "このチェックをオンのまま終了した場合に実行されます。",
            )

    def on_processing_settings_changed(self) -> None:
        self.persist_config()
        self.processed_cache.clear()
        self.prefetching_processed_keys.clear()
        self.prefetch_engine_done_paths.clear()
        self.prefetch_generation += 1
        if self.image_paths:
            self.display_current_image()

    def on_viewer_prefetch_changed(self) -> None:
        self.persist_config()
        self.viewer.set_pixmap_cache_limit(self.viewer_prefetch_spin.value() * 2 + 8)
        if self.image_paths:
            self.request_schedule_prefetch(0)

    def choose_engine_exe(self) -> None:
        engine = self.current_engine()
        title = f"{ENGINE_LABELS[engine]} exeを選択"
        path, _filter = QFileDialog.getOpenFileName(self, title, self.config_data.last_dir or str(APP_DIR), "Executable (*.exe);;All files (*.*)")
        if path:
            if engine == ENGINE_REALESRGAN:
                self.command_edit.setText(f'"{path}" -i "{{input}}" -o "{{output}}" -s {{scale}} -t {{tile}} -n {{model}}')
            else:
                self.command_edit.setText(f'"{path}" -i "{{input}}" -o "{{output}}" -s {{scale}} -n {{denoise}} -t {{tile}}')
            self.persist_config()

    def force_reprocess(self) -> None:
        if not self.image_paths:
            return
        path = self.image_paths[self.current_index]
        self.processed_cache.pop(self.processing_key(path), None)
        self.viewer.set_processed(None)
        self.enqueue_realcugan(path, front=True, force=True)

    def request_schedule_prefetch(self, delay_ms: int = PREFETCH_DEBOUNCE_MS) -> None:
        if not self.image_paths:
            return
        self.prefetch_timer.start(max(0, delay_ms))

    def clear_prefetch_io_queue(self) -> None:
        with self.prefetch_io_queue.mutex:
            self.prefetch_io_queue.queue.clear()

    def queue_prefetch_io_task(self, generation: int, priority: int, kind: str, key: object, source: str, target: str) -> None:
        with self.prefetch_io_lock:
            self.prefetch_io_sequence += 1
            sequence = self.prefetch_io_sequence
        self.prefetch_io_queue.put((int(priority), sequence, generation, kind, key, source, target))

    def _prefetch_io_worker_loop(self) -> None:
        while True:
            priority, sequence, generation, kind, key, source, target = self.prefetch_io_queue.get()
            if generation != self.prefetch_generation:
                continue
            started = time.perf_counter()
            originals: dict[Path, QImage] = {}
            processed: dict[tuple[str, str, int, int, int, str], QImage] = {}
            attempted_originals: list[Path] = []
            attempted_processed: list[tuple[str, str, int, int, int, str]] = []
            if kind == "original":
                path = self.normalized_path(Path(source))
                attempted_originals.append(path)
                image = QImage(str(path))
                if not image.isNull():
                    originals[path] = image
                self.signals.profile_event.emit("元画像IO", (time.perf_counter() - started) * 1000)
            elif kind == "processed":
                processed_key = key
                if isinstance(processed_key, tuple):
                    attempted_processed.append(processed_key)
                    target_path = Path(target)
                    if target_path.exists():
                        image = QImage(str(target_path))
                        if not image.isNull():
                            processed[processed_key] = image
                    self.signals.profile_event.emit("拡大画像IO", (time.perf_counter() - started) * 1000)
            if originals or processed or attempted_originals or attempted_processed:
                self.signals.prefetch_done.emit(
                    generation,
                    originals,
                    processed,
                    attempted_originals,
                    attempted_processed,
                )

    def schedule_prefetch(self) -> None:
        if not self.image_paths:
            return
        self.prefetch_generation += 1
        self.prefetching_original_paths.clear()
        self.prefetching_processed_keys.clear()
        self.clear_prefetch_io_queue()
        realcugan_plan = self.make_plan(self.realcugan_prefetch_spin.value())
        viewer_plan = self.make_prefetch_plan(self.viewer_prefetch_spin.value())
        self.prefetch_viewer_plan = viewer_plan
        self.prefetch_engine_plan = realcugan_plan[1:]
        self.prefetch_engine_done_paths = {
            self.normalized_path(path)
            for path in self.prefetch_engine_plan
            if self.processing_key(path) in self.processed_cache
        }
        self.start_viewer_prefetch(viewer_plan)
        self.update_prefetch_progress_bars()
        for position, path in enumerate(realcugan_plan):
            self.enqueue_realcugan(path, front=position == 0, check_existing=False, check_skip=False)
        self.reorder_work_queue(realcugan_plan)

    def start_viewer_prefetch(self, viewer_plan: list[Path]) -> None:
        if not viewer_plan:
            self.update_prefetch_progress_bars(viewer_plan)
            return
        generation = self.prefetch_generation
        before_originals = len(self.original_cache)
        before_processed = len(self.processed_cache)
        before_pixmaps = len(self.viewer.pixmap_cache)
        original_paths: list[Path] = []
        for path in viewer_plan:
            resolved = self.normalized_path(path)
            if resolved not in self.original_cache and resolved not in self.prefetching_original_paths:
                original_paths.append(resolved)
        processed_candidates: list[tuple[tuple[str, str, int, int, int, str], Path]] = []
        for path in viewer_plan:
            key = self.processing_key(path)
            if key in self.processed_cache or key in self.prefetching_processed_keys:
                continue
            if self.archive_mode_active() or not self.use_scale_cache_check.isChecked():
                continue
            processed_candidates.append((key, self.cache_output_path(path, create_dir=False)))
        if not original_paths and not processed_candidates:
            self.update_prefetch_progress_bars(viewer_plan)
            self.append_log_if_visible(
                f"Viewer prefetch: ready originals={before_originals}, processed={before_processed}, pixmaps={before_pixmaps}"
            )
            return
        self.prefetching_original_paths.update(original_paths)
        self.prefetching_processed_keys.update(key for key, _path in processed_candidates)
        self.update_prefetch_progress_bars(viewer_plan)
        self.append_log_if_visible(
            "Viewer prefetch start: "
            f"plan={len(viewer_plan)}, original_read={len(original_paths)}, processed_check={len(processed_candidates)}, "
            f"cache originals={before_originals}, processed={before_processed}, pixmaps={before_pixmaps}"
        )

        priority_rank = {self.normalized_path(path): index for index, path in enumerate(viewer_plan)}
        for path in original_paths:
            self.queue_prefetch_io_task(
                generation,
                priority_rank.get(self.normalized_path(path), len(priority_rank)),
                "original",
                path,
                str(path),
                "",
            )
        for key, processed_path in processed_candidates:
            source_path = self.normalized_path(Path(key[0]))
            self.queue_prefetch_io_task(
                generation,
                priority_rank.get(source_path, len(priority_rank)) + 1,
                "processed",
                key,
                key[0],
                str(processed_path),
            )

    def on_prefetch_done(
        self,
        generation: int,
        originals: dict[Path, QImage],
        processed: dict[tuple[str, str, int, int, int, str], QImage],
        attempted_originals: list[Path],
        attempted_processed: list[tuple[str, str, int, int, int, str]],
    ) -> None:
        for path in attempted_originals:
            self.prefetching_original_paths.discard(path)
        for key in attempted_processed:
            self.prefetching_processed_keys.discard(key)
        if generation != self.prefetch_generation:
            return
        started = time.perf_counter()
        current_paths = self.image_path_set
        current_path_strings = self.image_path_string_set
        added_originals = 0
        for path, image in originals.items():
            if path in current_paths and path not in self.original_cache:
                self.original_cache[path] = image
                added_originals += 1
        while len(self.original_cache) > max(6, self.config_data.viewer_prefetch_count * 2 + 3):
            self.original_cache.popitem(last=False)
        added_processed = 0
        engine_plan_paths = {self.normalized_path(path) for path in self.prefetch_engine_plan}
        for key, image in processed.items():
            if self.is_current_processing_key(key, current_path_strings) and key not in self.processed_cache:
                self.processed_cache[key] = image
                added_processed += 1
            processed_source = self.normalized_path(Path(key[0]))
            if processed_source in engine_plan_paths:
                self.prefetch_engine_done_paths.add(processed_source)
        warm_items: list[tuple[object, QImage]] = [
            (self.pixmap_progress_key("original", path), image)
            for path, image in originals.items()
            if path in current_paths and not image.isNull()
        ]
        warm_items.extend(
            (self.pixmap_progress_key("processed", Path(key[0])), image)
            for key, image in processed.items()
            if self.is_current_processing_key(key, current_path_strings) and not image.isNull()
        )
        if warm_items:
            self.viewer.queue_pixmap_prefetch(warm_items)
        self.update_prefetch_progress_bars()
        if not self.prefetching_original_paths and not self.prefetching_processed_keys:
            self.append_log_if_visible(
                "Viewer prefetch done: "
                f"cache originals={len(self.original_cache)}, processed={len(self.processed_cache)}, "
                f"pixmaps={len(self.viewer.pixmap_cache)}"
            )
        self.record_profile("先読み反映(UI)", (time.perf_counter() - started) * 1000)

    def is_current_processing_key(self, key: tuple[str, str, int, int, int, str], current_paths: set[str] | None = None) -> bool:
        if len(key) != 6:
            return False
        current_paths = current_paths or self.image_path_string_set
        return (
            key[0] in current_paths
            and key[1] == self.current_engine()
            and key[2] == self.effective_scale()
            and key[3] == (int(self.denoise_combo.currentText()) if self.current_engine() == ENGINE_REALCUGAN else 0)
            and key[4] == self.tile_spin.value()
            and key[5] == (self.realesrgan_model_combo.currentText() if self.current_engine() == ENGINE_REALESRGAN else "")
        )

    def make_plan(self, count: int) -> list[Path]:
        plan = [self.image_paths[self.current_index]]
        directions = (1, -1) if self.last_navigation_step >= 0 else (-1, 1)
        for offset in range(1, count + 1):
            for direction in directions:
                index = self.current_index + offset * direction
                if 0 <= index < len(self.image_paths):
                    plan.append(self.image_paths[index])
        return plan

    def make_prefetch_plan(self, count: int) -> list[Path]:
        return self.make_plan(count)[1:]

    def enqueue_realcugan(
        self,
        path: Path,
        front: bool = False,
        force: bool = False,
        check_existing: bool = True,
        check_skip: bool = True,
    ) -> None:
        path = self.normalized_path(path)
        if check_existing and not force and self.has_processed_result(path):
            return
        if check_skip and self.should_skip_realcugan(path):
            return
        if path in self.processing_paths:
            return
        if path in self.queued_paths:
            if front:
                self.promote_work_item(path)
            return
        self.queued_paths.add(path)
        if front:
            with self.work_queue.mutex:
                self.work_queue.queue.appendleft(path)
                self.work_queue.unfinished_tasks += 1
                self.work_queue.not_empty.notify()
        else:
            self.work_queue.put(path)

    def promote_work_item(self, path: Path) -> None:
        with self.work_queue.mutex:
            items = [item for item in self.work_queue.queue if item != path]
            self.work_queue.queue.clear()
            self.work_queue.queue.extend(items)
            self.work_queue.queue.appendleft(path)
            self.work_queue.not_empty.notify()

    def reorder_work_queue(self, priority_paths: list[Path]) -> None:
        priority = [self.normalized_path(path) for path in priority_paths]
        priority_rank = {path: index for index, path in enumerate(priority)}
        with self.work_queue.mutex:
            items = [item for item in self.work_queue.queue if item is not None]
            if not items:
                return
            items.sort(key=lambda item: priority_rank.get(self.normalized_path(item), len(priority_rank) + 1))
            self.work_queue.queue.clear()
            self.work_queue.queue.extend(items)
            self.work_queue.not_empty.notify()

    def _worker_loop(self) -> None:
        while True:
            path = self.work_queue.get()
            if path is None or getattr(self, "closing", False):
                return
            self.queued_paths.discard(path)
            if self.has_processed_result(path):
                continue
            if self.should_skip_upscale_in_worker(path):
                continue
            self.processing_paths.add(path)
            self.signals.process_started.emit(str(path))
            result = self.run_upscale_engine(path)
            self.processing_paths.discard(path)
            self.signals.process_done.emit(result)

    def should_skip_upscale_in_worker(self, path: Path) -> bool:
        if not self.config_data.skip_realcugan_for_tall_images:
            return False
        image = QImage(str(path))
        return not image.isNull() and image.height() >= self.config_data.skip_realcugan_height_threshold

    def run_upscale_engine(self, source: Path) -> dict:
        output_path, temporary_output = self.prepare_output_path(source)
        values = {
            "input": str(source),
            "output": str(output_path),
            "scale": self.effective_scale(),
            "denoise": self.denoise_combo.currentText(),
            "tile": self.tile_spin.value(),
            "model": self.realesrgan_model_combo.currentText(),
        }
        command = self.active_command_template().format(**values)
        try:
            started = time.perf_counter()
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                cwd=str(self.command_working_dir(command)),
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
            image = QImage(str(output_path)) if completed.returncode == 0 and output_path.exists() else QImage()
            if temporary_output and output_path.exists():
                output_path.unlink(missing_ok=True)
            return {
                "path": source,
                "code": completed.returncode,
                "output": completed.stdout.strip(),
                "image": image,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
            }
        except Exception as exc:
            return {"path": source, "code": 1, "output": str(exc), "image": QImage()}

    def on_process_started(self, path_text: str) -> None:
        path = Path(path_text)
        self.append_log(f"{self.engine_label()} started: {self.display_name(path)}")
        self.update_window_title()

    def on_process_done(self, result: dict) -> None:
        path: Path = result["path"]
        output = result.get("output") or ""
        if output:
            self.append_log(output)
        if result["code"] == 0 and not result["image"].isNull():
            self.record_profile(f"{self.engine_label()}処理", float(result.get("elapsed_ms", 0.0)))
            self.append_log(f"Done: {self.display_name(path)}")
            key = self.processing_key(path)
            self.processed_cache[key] = result["image"]
            self.prefetch_engine_done_paths.add(self.normalized_path(path))
            self.update_prefetch_progress_bars()
            if self.current_index >= 0:
                normalized = self.normalized_path(path)
                current_normalized = self.normalized_path(self.image_paths[self.current_index])
                secondary_index = self.secondary_page_index()
                secondary_normalized = (
                    self.normalized_path(self.image_paths[secondary_index])
                    if secondary_index is not None
                    else None
                )
                if normalized == current_normalized:
                    self.viewer.set_processed(result["image"], page_slot=0)
                    self.viewer.pixmap_prefetch_done_keys.add(self.pixmap_progress_key("processed", path))
                    if secondary_index is not None:
                        display_entries = self.current_display_index_entries()
                        name_text = " / ".join(self.display_name(entry_path) for _entry_index, entry_path in display_entries)
                        self.status_label.setText(f"{self.current_index + 1}-{secondary_index + 1}/{len(self.image_paths)} {self.state_text('処理済み')}: {name_text}")
                    else:
                        self.status_label.setText(f"{self.current_index + 1}/{len(self.image_paths)} {self.state_text('処理済み')}: {self.display_name(path)}")
                    self.update_window_title()
                elif secondary_normalized is not None and normalized == secondary_normalized:
                    self.viewer.set_processed(result["image"], page_slot=1)
                    self.viewer.pixmap_prefetch_done_keys.add(self.pixmap_progress_key("processed", path))
                    display_entries = self.current_display_index_entries()
                    name_text = " / ".join(self.display_name(entry_path) for _entry_index, entry_path in display_entries)
                    self.status_label.setText(f"{self.current_index + 1}-{secondary_index + 1}/{len(self.image_paths)} {self.state_text('処理済み')}: {name_text}")
                    self.update_window_title()
        else:
            self.append_log(f"Process exited with code {result['code']}: {self.display_name(path)}")
            self.update_prefetch_progress_bars()

    def has_processed_result(self, source: Path) -> bool:
        return self.processing_key(source) in self.processed_cache or self.existing_processed_path(source) is not None

    def existing_processed_path(self, source: Path) -> Path | None:
        if self.archive_mode_active() or not self.use_scale_cache_check.isChecked():
            return None
        path = self.cache_output_path(source, create_dir=False)
        return path if path.exists() else None

    def prepare_output_path(self, source: Path) -> tuple[Path, bool]:
        if self.save_scale_check.isChecked() and not self.archive_mode_active():
            return self.cache_output_path(source, create_dir=True), False
        fd, text_path = tempfile.mkstemp(prefix=TEMP_OUTPUT_PREFIX, suffix=".png", dir=self.process_temp_dir)
        os.close(fd)
        Path(text_path).unlink(missing_ok=True)
        return Path(text_path), True

    def cache_output_path(self, source: Path, create_dir: bool) -> Path:
        engine_model = self.cache_model_name()
        folder_name = f"{engine_model}_x{self.effective_scale()}"
        folder = source.parent / folder_name
        if create_dir:
            folder.mkdir(parents=True, exist_ok=True)
        return folder / source.name

    def processing_key(self, source: Path) -> tuple[str, str, int, int, int, str]:
        return (
            self.normalized_path_text(source),
            self.current_engine(),
            self.effective_scale(),
            int(self.denoise_combo.currentText()) if self.current_engine() == ENGINE_REALCUGAN else 0,
            self.tile_spin.value(),
            self.realesrgan_model_combo.currentText() if self.current_engine() == ENGINE_REALESRGAN else "",
        )

    def cache_model_name(self) -> str:
        if self.current_engine() == ENGINE_REALESRGAN:
            raw = f"realesrgan_{self.realesrgan_model_combo.currentText()}"
        else:
            raw = "realcugan"
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)

    def command_working_dir(self, command: str) -> Path:
        stripped = command.strip()
        exe = stripped[1:stripped.find('"', 1)] if stripped.startswith('"') and stripped.find('"', 1) > 1 else stripped.split(maxsplit=1)[0]
        exe_path = Path(exe)
        if exe_path.is_absolute() and exe_path.is_file():
            return exe_path.parent
        if (APP_DIR / exe_path).is_file():
            return APP_DIR
        return exe_path.parent if exe_path.is_file() else APP_DIR

    def collect_images(self, folder: Path) -> list[Path]:
        folder = folder.resolve()
        images: list[Path] = []
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if not entry.is_file():
                        continue
                    suffix = Path(entry.name).suffix.lower()
                    if suffix in IMAGE_EXTENSIONS:
                        images.append(folder / entry.name)
        except OSError:
            return []
        return windows_logical_sorted(images, lambda path: path.name)

    def is_image(self, path: Path) -> bool:
        return path.suffix.lower() in IMAGE_EXTENSIONS

    def open_archive(self, archive_path: Path) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix=TEMP_ARCHIVE_PREFIX))
        self.write_temp_lock(temp_dir)
        try:
            images, names = self.extract_archive_images(archive_path, temp_dir)
        except Exception as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            QMessageBox.critical(self, APP_NAME, f"アーカイブを開けませんでした。\n{exc}")
            return
        if not images:
            shutil.rmtree(temp_dir, ignore_errors=True)
            QMessageBox.information(self, APP_NAME, "このアーカイブには対応画像がありません。")
            return
        self.leave_archive_mode()
        self.archive_temp_dir = temp_dir
        self.archive_source_path = archive_path
        self.archive_display_names = names
        self.set_archive_options_enabled(False)
        self.set_image_list(images, 0)

    def extract_archive_images(self, archive_path: Path, temp_dir: Path) -> tuple[list[Path], dict[Path, str]]:
        suffix = archive_path.suffix.lower()
        if suffix in {".zip", ".cbz"}:
            return self.extract_zip_images(archive_path, temp_dir)
        if suffix in {".7z", ".cb7"}:
            if py7zr is not None:
                with py7zr.SevenZipFile(archive_path, mode="r") as archive:
                    archive.extractall(path=temp_dir)
                return self.collect_archive_outputs(temp_dir)
            return self.extract_with_7z_command(archive_path, temp_dir)
        if suffix in {".rar", ".cbr"}:
            if rarfile is not None:
                try:
                    return self.extract_rar_images(archive_path, temp_dir)
                except Exception:
                    return self.extract_with_7z_command(archive_path, temp_dir)
            return self.extract_with_7z_command(archive_path, temp_dir)
        raise RuntimeError(f"対応していない形式です: {suffix}")

    def extract_zip_images(self, archive_path: Path, temp_dir: Path) -> tuple[list[Path], dict[Path, str]]:
        images: list[Path] = []
        names: dict[Path, str] = {}
        with zipfile.ZipFile(archive_path) as archive:
            members = windows_logical_sorted(
                [info for info in archive.infolist() if not info.is_dir() and self.is_image(Path(info.filename))],
                lambda item: self.archive_display_name(item.filename),
            )
            for info in members:
                output = self.archive_member_output_path(temp_dir, info.filename)
                if output is None:
                    continue
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                images.append(output.resolve())
                names[output.resolve()] = self.archive_display_name(info.filename)
        return images, names

    def extract_rar_images(self, archive_path: Path, temp_dir: Path) -> tuple[list[Path], dict[Path, str]]:
        images: list[Path] = []
        names: dict[Path, str] = {}
        with rarfile.RarFile(archive_path) as archive:
            members = windows_logical_sorted(
                [info for info in archive.infolist() if not info.isdir() and self.is_image(Path(info.filename))],
                lambda item: self.archive_display_name(item.filename),
            )
            for info in members:
                output = self.archive_member_output_path(temp_dir, info.filename)
                if output is None:
                    continue
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                images.append(output.resolve())
                names[output.resolve()] = self.archive_display_name(info.filename)
        return images, names

    def extract_with_7z_command(self, archive_path: Path, temp_dir: Path) -> tuple[list[Path], dict[Path, str]]:
        tool = self.find_7z()
        if tool is None:
            raise RuntimeError("この形式を開くには py7zr/rarfile または 7z/7za/7zr が必要です。")
        completed = subprocess.run([str(tool), "x", "-y", f"-o{temp_dir}", str(archive_path)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding=locale.getpreferredencoding(False), errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stdout.strip())
        return self.collect_archive_outputs(temp_dir)

    def collect_archive_outputs(self, temp_dir: Path) -> tuple[list[Path], dict[Path, str]]:
        images = windows_logical_sorted(
            [path.resolve() for path in temp_dir.rglob("*") if path.is_file() and self.is_image(path)],
            lambda path: str(path.relative_to(temp_dir)),
        )
        names = {path: self.archive_display_name(str(path.relative_to(temp_dir))) for path in images}
        return images, names

    def find_7z(self) -> Path | None:
        for name in ("7z", "7za", "7zr"):
            found = shutil.which(name)
            if found:
                return Path(found)
        for candidate in (Path(os.environ.get("ProgramFiles", "")) / "7-Zip" / "7z.exe", Path(os.environ.get("ProgramFiles(x86)", "")) / "7-Zip" / "7z.exe"):
            if candidate.is_file():
                return candidate
        return None

    def archive_member_output_path(self, temp_dir: Path, member_name: str) -> Path | None:
        parts = PurePosixPath(self.archive_display_name(member_name)).parts
        safe = []
        for part in parts:
            if part in {"", ".", "/"}:
                continue
            if part == ".." or ":" in part:
                return None
            safe.append(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", part))
        return temp_dir.joinpath(*safe) if safe else None

    def archive_display_name(self, member_name: str) -> str:
        return member_name.replace("\\", "/").lstrip("/")

    def archive_mode_active(self) -> bool:
        return self.archive_temp_dir is not None

    def set_archive_options_enabled(self, enabled: bool) -> None:
        if not enabled and self.archive_disabled_scale_options is None:
            self.archive_disabled_scale_options = (self.save_scale_check.isChecked(), self.use_scale_cache_check.isChecked())
        self.save_scale_check.setEnabled(enabled)
        self.use_scale_cache_check.setEnabled(enabled)
        self.archive_help.setVisible(not enabled)
        if not enabled:
            self.save_scale_check.blockSignals(True)
            self.use_scale_cache_check.blockSignals(True)
            self.save_scale_check.setChecked(False)
            self.use_scale_cache_check.setChecked(False)
            self.save_scale_check.blockSignals(False)
            self.use_scale_cache_check.blockSignals(False)
        elif self.archive_disabled_scale_options is not None:
            save_enabled, cache_enabled = self.archive_disabled_scale_options
            self.archive_disabled_scale_options = None
            self.save_scale_check.blockSignals(True)
            self.use_scale_cache_check.blockSignals(True)
            self.save_scale_check.setChecked(save_enabled)
            self.use_scale_cache_check.setChecked(cache_enabled)
            self.save_scale_check.blockSignals(False)
            self.use_scale_cache_check.blockSignals(False)

    def leave_archive_mode(self) -> None:
        if self.archive_temp_dir:
            self.retired_archive_temp_dirs.append(self.archive_temp_dir)
        self.archive_temp_dir = None
        self.archive_source_path = None
        self.archive_display_names.clear()
        self.set_archive_options_enabled(True)

    def display_name(self, path: Path) -> str:
        return self.archive_display_names.get(path.resolve(), path.name)

    def write_temp_lock(self, temp_dir: Path) -> None:
        try:
            (temp_dir / TEMP_LOCK_FILE).write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            pass

    def _cleanup_stale_temp_files(self) -> None:
        temp_root = Path(tempfile.gettempdir())
        for entry in list(temp_root.iterdir()):
            try:
                if entry.is_dir() and entry.name.startswith((TEMP_ARCHIVE_PREFIX, TEMP_WORK_PREFIX)):
                    shutil.rmtree(entry, ignore_errors=True)
            except OSError:
                pass

    def closeEvent(self, event) -> None:
        self.closing = True
        self._show_fullscreen_cursor()
        self.persist_config()
        self.work_queue.put(None)
        paths = list(self.retired_archive_temp_dirs)
        if self.archive_temp_dir:
            paths.append(self.archive_temp_dir)
        if self.process_temp_dir:
            paths.append(self.process_temp_dir)
        for path in paths:
            shutil.rmtree(path, ignore_errors=True)
        super().closeEvent(event)


def main() -> None:
    enable_high_dpi_awareness()
    set_process_app_user_model_id()
    single_instance_mutex = acquire_single_instance_mutex_if_needed()
    app = QApplication([])
    app.setApplicationName(APP_NAME)
    if APP_ICON_ICO.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_ICO)))
    window = MainWindow()
    window.show()
    try:
        app.exec()
    finally:
        release_single_instance_mutex(single_instance_mutex)


if __name__ == "__main__":
    main()

