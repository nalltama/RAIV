from __future__ import annotations

import base64
import ctypes
import io
import json
import locale
import math
import os
import queue
import random
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from ctypes import byref
from collections import OrderedDict, deque
from ctypes import wintypes
from dataclasses import asdict, dataclass, field
from functools import cmp_to_key
from pathlib import Path, PurePosixPath

try:
    from PySide6.QtCore import QObject, QPoint, QRect, QSize, Qt, QEvent, QTimer, Signal
    from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QImage, QImageReader, QIntValidator, QKeySequence, QPainter, QPalette, QPen, QPixmap, QTransform
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QButtonGroup,
        QCheckBox,
        QComboBox as QtComboBox,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox as QtDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGraphicsOpacityEffect,
        QGridLayout,
        QHBoxLayout,
        QInputDialog,
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
        QSpinBox as QtSpinBox,
        QSplitter,
        QSplitterHandle,
        QTabWidget,
        QTextEdit,
        QTreeWidget,
        QTreeWidgetItem,
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
    from PIL import Image as PILImage, ImageFilter
except ImportError:
    PILImage = None
    ImageFilter = None

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
APP_VERSION = "1.2.3"
APP_ID = "RealtimeAIImageViewer.RAIV"
APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "setting.json"
FOLDER_HISTORY_PATH = APP_DIR / "folder_history.json"
NOVELAI_PROMPT_PRESETS_PATH = APP_DIR / "novelai_prompt_presets.json"
NOVELAI_TOKEN_PATH = APP_DIR / "novelai_token.dat"
LATEST_RELEASE_API_URL = "https://api.github.com/repos/nalltama/RAIV/releases/latest"
RELEASES_PAGE_URL = "https://github.com/nalltama/RAIV/releases"
DEFAULT_COMFYUI_API_URL = "http://127.0.0.1:8000"
COMFYUI_RECOMMENDED_MODEL_NAME = "animagine-xl-4.0-opt.safetensors"
COMFYUI_RECOMMENDED_MODEL_URL = "https://huggingface.co/cagliostrolab/animagine-xl-4.0/resolve/main/animagine-xl-4.0-opt.safetensors"
COMFYUI_RECOMMENDED_CONTROLNET_NAME = "shermang_controlnet_standard_lineart_sdxl.safetensors"
COMFYUI_RECOMMENDED_CONTROLNET_URL = "https://huggingface.co/ShermanG/ControlNet-Standard-Lineart-for-SDXL/resolve/main/diffusion_pytorch_model.safetensors"
COMFYUI_WORKFLOW_DIR = APP_DIR / "comfyui_workflows"
COMFYUI_DEFAULT_WORKFLOW_NAME = "raiv_sdxl_img2img_colorize_api.json"
COMFYUI_INPUT_NODE_ID = "4"
COMFYUI_OUTPUT_NODE_ID = "8"
DEFAULT_COLORIZE_POSITIVE_PROMPT = (
    "high quality manga colorization, tasteful anime coloring, natural skin tone, "
    "soft ambient colors, coherent hair and clothing colors, subtle gradients, "
    "clean black lineart, preserve screentones, readable Japanese text"
)
DEFAULT_COLORIZE_NEGATIVE_PROMPT = (
    "monochrome, grayscale, muddy colors, oversaturated, neon colors, "
    "low quality, blurry, broken lineart, warped text, unreadable text, watermark, logo"
)
DEFAULT_NOVELAI_MODEL = "nai-diffusion-4-5-curated"
THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_OPTIONS = [
    (THEME_SYSTEM, "Windowsの設定に同期"),
    (THEME_LIGHT, "ライトテーマ"),
    (THEME_DARK, "ダークテーマ"),
]
DEFAULT_NOVELAI_SAMPLER = "k_euler_ancestral"
DEFAULT_NOVELAI_SCHEDULER = "karras"
DEFAULT_NOVELAI_GENERATED_DIR = APP_DIR / "RAIV_generated"
MAX_NOVELAI_SEED = 4294967295
NOVELAI_MAX_BATCH_BY_PIXELS = (
    (360448, 8),
    (409600, 6),
    (3145728, 4),
)
NOVELAI_OUTPUT_NAME_TEMPLATES = {
    "seed": "{seed}",
    "date_seed": "{date}/{seed}",
    "date_time": "{date}/{time}",
    "date_time_seed": "{date}/{time}_{seed}",
}
NOVELAI_FURRY_DATASET_TAG = "fur dataset"
NOVELAI_DATASET_MODE_OPTIONS = [
    ("anime", "アニメモード"),
    ("furry", "ケモノモード"),
]
NOVELAI_QUALITY_TAGS_SUFFIX = ", very aesthetic, masterpiece, no text"
NOVELAI_QUALITY_TAGS_SUFFIXES_BY_MODEL = {
    "nai-diffusion-4-5-full": [
        ", very aesthetic, masterpiece, no text",
        ", location, very aesthetic, masterpiece, no text",
    ],
    "nai-diffusion-4-5-curated": [
        ", location, masterpiece, no text, -0.8::feet::, rating:general",
    ],
    "nai-diffusion-4-full": [
        ", no text, best quality, very aesthetic, absurdres",
    ],
    "nai-diffusion-4-curated": [
        ", rating:general, amazing quality, very aesthetic, absurdres",
    ],
    "nai-diffusion-3": [
        ", best quality, amazing quality, very aesthetic, absurdres",
    ],
}
RAIV_DISABLED_PROMPT_START = "<<RAIV_DISABLED_PROMPT>>"
RAIV_DISABLED_PROMPT_END = "<</RAIV_DISABLED_PROMPT>>"
RAIV_PROMPT_FOLDER_START = "<<RAIV_PROMPT_FOLDER:"
RAIV_PROMPT_RANDOM_FOLDER_START = "<<RAIV_PROMPT_RANDOM_FOLDER:"
RAIV_PROMPT_FOLDER_END = "<</RAIV_PROMPT_FOLDER>>"
NOVELAI_UC_PRESET_OPTIONS = [
    ("strong", "強い"),
    ("light", "弱い"),
    ("furry_focus", "ケモノモード"),
    ("human_focus", "人間に重点を置く"),
    ("none", "指定なし"),
]
NOVELAI_UC_PRESET_TEXTS_BY_MODEL = {
    "nai-diffusion-4-5-full": {
        "strong": [
            "nsfw, lowres, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, dithering, halftone, screentone, multiple views, logo, too many watermarks, negative space, blank page",
            "lowres, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, dithering, halftone, screentone, multiple views, logo, too many watermarks, negative space, blank page",
        ],
        "light": [
            "nsfw, lowres, artistic error, scan artifacts, worst quality, bad quality, jpeg artifacts, multiple views, very displeasing, too many watermarks, negative space, blank page",
            "lowres, artistic error, scan artifacts, worst quality, bad quality, jpeg artifacts, multiple views, very displeasing, too many watermarks, negative space, blank page",
        ],
        "furry_focus": [
            "nsfw, {worst quality}, distracting watermark, unfinished, bad quality, {widescreen}, upscale, {sequence}, {{grandfathered content}}, blurred foreground, chromatic aberration, sketch, everyone, [sketch background], simple, [flat colors], ych (character), outline, multiple scenes, [[horror (theme)]], comic",
            "{worst quality}, distracting watermark, unfinished, bad quality, {widescreen}, upscale, {sequence}, {{grandfathered content}}, blurred foreground, chromatic aberration, sketch, everyone, [sketch background], simple, [flat colors], ych (character), outline, multiple scenes, [[horror (theme)]], comic",
        ],
        "human_focus": [
            "nsfw, lowres, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, dithering, halftone, screentone, multiple views, logo, too many watermarks, negative space, blank page, @_@, mismatched pupils, glowing eyes, bad anatomy",
            "lowres, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, dithering, halftone, screentone, multiple views, logo, too many watermarks, negative space, blank page, @_@, mismatched pupils, glowing eyes, bad anatomy",
        ],
    },
    "nai-diffusion-4-5-curated": {
        "strong": [
            "blurry, lowres, upscaled, artistic error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, halftone, multiple views, logo, too many watermarks, negative space, blank page",
        ],
        "light": [
            "blurry, lowres, upscaled, artistic error, scan artifacts, jpeg artifacts, logo, too many watermarks, negative space, blank page",
        ],
        "human_focus": [
            "blurry, lowres, upscaled, artistic error, film grain, scan artifacts, bad anatomy, bad hands, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, halftone, multiple views, logo, too many watermarks, @_@, mismatched pupils, glowing eyes, negative space, blank page",
        ],
    },
    "nai-diffusion-4-full": {
        "strong": [
            "blurry, lowres, error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, multiple views, logo, too many watermarks",
        ],
        "light": [
            "blurry, lowres, error, worst quality, bad quality, jpeg artifacts, very displeasing",
        ],
    },
    "nai-diffusion-4-curated": {
        "strong": [
            "blurry, lowres, error, film grain, scan artifacts, worst quality, bad quality, jpeg artifacts, very displeasing, chromatic aberration, logo, dated, signature, multiple views, gigantic breasts",
        ],
        "light": [
            "blurry, lowres, error, worst quality, bad quality, jpeg artifacts, very displeasing, logo, dated, signature",
        ],
    },
    "nai-diffusion-3": {
        "strong": [
            "lowres, {bad}, error, fewer, extra, missing, worst quality, jpeg artifacts, bad quality, watermark, unfinished, displeasing, chromatic aberration, signature, extra digits, artistic error, username, scan, [abstract],",
        ],
        "light": [
            "lowres, jpeg artifacts, worst quality, watermark, blurry, very displeasing,",
        ],
        "human_focus": [
            "lowres, {bad}, error, fewer, extra, missing, worst quality, jpeg artifacts, bad quality, watermark, unfinished, displeasing, chromatic aberration, signature, extra digits, artistic error, username, scan, [abstract], bad anatomy, bad hands, @_@, mismatched pupils, heart-shaped pupils, glowing eyes,",
        ],
    },
}
NOVELAI_SIZE_PRESETS = {
    "Portrait 832x1216": (832, 1216),
    "Landscape 1216x832": (1216, 832),
    "Square 1024x1024": (1024, 1024),
    "Small Portrait 512x768": (512, 768),
    "Small Landscape 768x512": (768, 512),
    "Small Square 640x640": (640, 640),
}
NOVELAI_MODEL_OPTIONS = [
    "nai-diffusion-4-5-full",
    "nai-diffusion-4-5-curated",
    "nai-diffusion-4-full",
    "nai-diffusion-4-curated",
    "nai-diffusion-3",
]
NOVELAI_SAMPLER_OPTIONS = [
    "k_euler_ancestral",
    "k_euler",
    "k_dpmpp_2m",
    "k_dpmpp_2s_ancestral",
    "k_dpmpp_sde",
    "ddim",
]
NOVELAI_SCHEDULER_OPTIONS = ["karras", "exponential", "polyexponential"]
APP_ICON_ICO = APP_DIR / "assets" / "app_icon.ico"
APP_ICON_PNG = APP_DIR / "assets" / "app_icon.png"
CURVE_DIR = APP_DIR / "cur"
REALESRGAN_FIXED_SCALE = 4
BUNDLED_REALCUGAN_EXE = APP_DIR / "tools" / "realcugan-ncnn-vulkan" / "realcugan-ncnn-vulkan.exe"
BUNDLED_REALESRGAN_EXE = APP_DIR / "tools" / "realesrgan-ncnn-vulkan" / "realesrgan-ncnn-vulkan.exe"
GIGAPIXEL_EXE_CANDIDATES = [
    Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Topaz Labs LLC" / product / "bin" / "gigapixel.exe"
    for product in ("Topaz Gigapixel AI", "Topaz Gigapixel")
]
DEFAULT_GIGAPIXEL_EXE = next((path for path in GIGAPIXEL_EXE_CANDIDATES if path.exists()), GIGAPIXEL_EXE_CANDIDATES[0])
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
DEFAULT_GIGAPIXEL_TEMPLATE = (
    f'"{DEFAULT_GIGAPIXEL_EXE}" -i "{{input}}" -o "{{output_dir}}" --scale {{scale}} --model "{{model}}" '
    '--denoise {denoise} --sharpen {sharpen} --compression {compression} --face-recovery {face_recovery} --image-format png'
    if DEFAULT_GIGAPIXEL_EXE.exists()
    else 'gigapixel.exe -i "{input}" -o "{output_dir}" --scale {scale} --model "{model}" '
    '--denoise {denoise} --sharpen {sharpen} --compression {compression} --face-recovery {face_recovery} --image-format png'
)
LEGACY_GIGAPIXEL_TEMPLATE = (
    'gigapixel.exe -i "{input}" -o "{output}" --scale {scale} --model "{model}" '
    '--denoise {denoise} --sharpen {sharpen} --compression {compression} --face-recovery {face_recovery}'
)
ENGINE_REALCUGAN = "realcugan"
ENGINE_REALESRGAN = "realesrgan"
ENGINE_GIGAPIXEL = "gigapixel"
ENGINE_LABELS = {
    ENGINE_REALCUGAN: "Real-CUGAN",
    ENGINE_REALESRGAN: "Real-ESRGAN",
    ENGINE_GIGAPIXEL: "Gigapixel AI",
}
REALESRGAN_MODELS = ["realesr-animevideov3", "realesrgan-x4plus", "realesrgan-x4plus-anime"]
REALCUGAN_SCALES = [2, 3, 4]
REALESRGAN_MODEL_SCALES = {
    "realesr-animevideov3": [2, 3, 4],
    "realesrgan-x4plus": [4],
    "realesrgan-x4plus-anime": [4],
}
GIGAPIXEL_MODELS = [
    ("Standard", "standard"),
    ("High Fidelity", "high_fidelity"),
    ("Low Resolution", "low_resolution"),
    ("Text & Shapes", "text_and_shapes"),
    ("Art & CG", "art_and_cg"),
]
GIGAPIXEL_MODEL_SCALES = {model: [2, 3, 4, 6] for _label, model in GIGAPIXEL_MODELS}
HDR_IMAGE_EXTENSIONS = {".jxr", ".wdp", ".hdp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"} | HDR_IMAGE_EXTENSIONS
ARCHIVE_EXTENSIONS = {".zip", ".cbz", ".rar", ".cbr", ".7z", ".cb7"}
TEMP_ARCHIVE_PREFIX = "realcugan_qt_archive_"
TEMP_WORK_PREFIX = "realcugan_qt_work_"
TEMP_OUTPUT_PREFIX = "realcugan_"
TEMP_LOCK_FILE = "viewer.lock"
CONFIG_SAVE_DEBOUNCE_MS = 300
NOVELAI_PREVIEW_DEBOUNCE_MS = 120
SINGLE_INSTANCE_MUTEX_NAME = "Local\\RealtimeAIImageViewer_RAIV_SingleInstance"
BORDERLESS_FULLSCREEN_OVERSCAN = 1
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOOWNERZORDER = 0x0200
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
MONITOR_DEFAULTTONEAREST = 2
FO_DELETE = 3
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_ACCESS_DENIED = 5
FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400
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
THUMBNAIL_PREFETCH_DEBOUNCE_MS = 90
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
SETTINGS_TAB_IDS = ["realcugan", "general", "image_adjust", "colorize", "novelai", "other", "keyconfig"]
MODIFIER_MASK = (
    Qt.ControlModifier.value
    | Qt.ShiftModifier.value
    | Qt.AltModifier.value
)


def viewer_pixmap_cache_limit(prefetch_count: int) -> int:
    return max(24, max(0, int(prefetch_count)) * 4 + 8)


class WICGUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.USHORT),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def wic_guid(value: str) -> WICGUID:
    item = uuid.UUID(value)
    return WICGUID(
        item.time_low,
        item.time_mid,
        item.time_hi_version,
        (ctypes.c_ubyte * 8)(
            item.clock_seq_hi_variant,
            item.clock_seq_low,
            *item.node.to_bytes(6, "big"),
        ),
    )


CLSID_WIC_IMAGING_FACTORY = wic_guid("cacaf262-9370-4615-a13b-9f5539da4c0a")
IID_IWIC_IMAGING_FACTORY = wic_guid("ec5ec8a9-c395-4314-9c77-54d7a935ff70")
GUID_WIC_PIXEL_FORMAT_64BPP_RGBA_HALF = wic_guid("6fddc324-4e03-4bfe-b185-3d77768dc93a")
GUID_WIC_PIXEL_FORMAT_32BPP_RGBA = wic_guid("f5c7ad2d-6a8d-43dd-a7a8-a29935261ae9")
COINIT_MULTITHREADED = 0
RPC_E_CHANGED_MODE = ctypes.c_long(0x80010106).value
CLSCTX_INPROC_SERVER = 1
GENERIC_READ = 0x80000000
WIC_DECODE_METADATA_CACHE_ON_DEMAND = 0
WIC_BITMAP_DITHER_TYPE_NONE = 0
WIC_BITMAP_PALETTE_TYPE_CUSTOM = 0


def succeeded(hr: int) -> bool:
    return int(hr) >= 0


def com_method(pointer: ctypes.c_void_p, index: int, restype, *argtypes):
    vtable = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable[index])


def com_release(pointer: ctypes.c_void_p | None) -> None:
    if pointer:
        com_method(pointer, 2, wintypes.ULONG)(pointer)


def is_hdr_image_path(path: Path) -> bool:
    return path.suffix.lower() in HDR_IMAGE_EXTENSIONS


def load_image(path: Path, hdr_tonemap_brightness: float = 1.0) -> QImage:
    if is_hdr_image_path(path):
        image = load_wic_hdr_image(path, hdr_tonemap_brightness)
        if not image.isNull():
            return image
    return QImage(str(path))


def load_thumbnail_image(path: Path, max_size: int, hdr_tonemap_brightness: float = 1.0) -> QImage:
    max_size = max(1, int(max_size))
    if is_hdr_image_path(path):
        image = load_image(path, hdr_tonemap_brightness)
    else:
        reader = QImageReader(str(path))
        source_size = reader.size()
        if source_size.isValid():
            reader.setScaledSize(source_size.scaled(QSize(max_size, max_size), Qt.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            image = load_image(path, hdr_tonemap_brightness)
    if image.isNull():
        return image
    if image.width() != max_size and image.height() != max_size:
        image = image.scaled(max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return image


def read_image_size(path: Path) -> QSize:
    reader = QImageReader(str(path))
    size = reader.size()
    if size.isValid():
        return size
    if PILImage is not None:
        try:
            with PILImage.open(path) as image:
                return QSize(int(image.width), int(image.height))
        except Exception:
            pass
    return QSize()


def load_wic_hdr_image(path: Path, hdr_tonemap_brightness: float = 1.0) -> QImage:
    if os.name != "nt":
        return QImage()
    image = load_wic_half_tonemapped_image(path, hdr_tonemap_brightness)
    if not image.isNull():
        return image
    return load_wic_8bit_image(path)


def create_wic_factory() -> tuple[ctypes.c_void_p | None, bool]:
    initialized = False
    hr = ctypes.windll.ole32.CoInitializeEx(None, COINIT_MULTITHREADED)
    if succeeded(hr):
        initialized = True
    elif int(hr) != RPC_E_CHANGED_MODE:
        return None, False
    factory = ctypes.c_void_p()
    hr = ctypes.windll.ole32.CoCreateInstance(
        ctypes.byref(CLSID_WIC_IMAGING_FACTORY),
        None,
        CLSCTX_INPROC_SERVER,
        ctypes.byref(IID_IWIC_IMAGING_FACTORY),
        ctypes.byref(factory),
    )
    if not succeeded(hr) or not factory:
        if initialized:
            ctypes.windll.ole32.CoUninitialize()
        return None, False
    return factory, initialized


def read_wic_pixels(path: Path, pixel_format: WICGUID, bytes_per_pixel: int) -> tuple[int, int, bytes] | None:
    factory, initialized = create_wic_factory()
    decoder = ctypes.c_void_p()
    frame = ctypes.c_void_p()
    converter = ctypes.c_void_p()
    try:
        if not factory:
            return None
        create_decoder = com_method(
            factory,
            3,
            ctypes.c_long,
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
        )
        hr = create_decoder(
            factory,
            str(path),
            None,
            GENERIC_READ,
            WIC_DECODE_METADATA_CACHE_ON_DEMAND,
            ctypes.byref(decoder),
        )
        if not succeeded(hr) or not decoder:
            return None
        get_frame = com_method(decoder, 13, ctypes.c_long, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p))
        hr = get_frame(decoder, 0, ctypes.byref(frame))
        if not succeeded(hr) or not frame:
            return None
        create_converter = com_method(factory, 10, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p))
        hr = create_converter(factory, ctypes.byref(converter))
        if not succeeded(hr) or not converter:
            return None
        initialize = com_method(
            converter,
            8,
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.POINTER(WICGUID),
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.c_double,
            wintypes.DWORD,
        )
        hr = initialize(
            converter,
            frame,
            ctypes.byref(pixel_format),
            WIC_BITMAP_DITHER_TYPE_NONE,
            None,
            0.0,
            WIC_BITMAP_PALETTE_TYPE_CUSTOM,
        )
        if not succeeded(hr):
            return None
        width = wintypes.UINT()
        height = wintypes.UINT()
        get_size = com_method(converter, 3, ctypes.c_long, ctypes.POINTER(wintypes.UINT), ctypes.POINTER(wintypes.UINT))
        hr = get_size(converter, ctypes.byref(width), ctypes.byref(height))
        if not succeeded(hr) or width.value <= 0 or height.value <= 0:
            return None
        stride = int(width.value) * int(bytes_per_pixel)
        buffer_size = stride * int(height.value)
        buffer = (ctypes.c_ubyte * buffer_size)()
        copy_pixels = com_method(
            converter,
            7,
            ctypes.c_long,
            ctypes.c_void_p,
            wintypes.UINT,
            wintypes.UINT,
            ctypes.POINTER(ctypes.c_ubyte),
        )
        hr = copy_pixels(converter, None, stride, buffer_size, buffer)
        if not succeeded(hr):
            return None
        return int(width.value), int(height.value), bytes(buffer)
    finally:
        com_release(converter)
        com_release(frame)
        com_release(decoder)
        com_release(factory)
        if initialized:
            ctypes.windll.ole32.CoUninitialize()


def load_wic_8bit_image(path: Path) -> QImage:
    result = read_wic_pixels(path, GUID_WIC_PIXEL_FORMAT_32BPP_RGBA, 4)
    if result is None:
        return QImage()
    width, height, data = result
    return QImage(data, width, height, QImage.Format_RGBA8888).copy()


def load_wic_half_tonemapped_image(path: Path, hdr_tonemap_brightness: float = 1.0) -> QImage:
    if np is None:
        return QImage()
    result = read_wic_pixels(path, GUID_WIC_PIXEL_FORMAT_64BPP_RGBA_HALF, 8)
    if result is None:
        return QImage()
    width, height, data = result
    half = np.frombuffer(data, dtype=np.float16).reshape((height, width, 4)).astype(np.float32)
    rgb = np.nan_to_num(half[:, :, :3], nan=0.0, posinf=16.0, neginf=0.0)
    rgb = np.clip(rgb, 0.0, 16.0)
    scene_luminance = rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152 + rgb[:, :, 2] * 0.0722
    valid_luminance = scene_luminance[scene_luminance > 0.000001]
    if valid_luminance.size:
        median_luminance = max(0.000001, float(np.percentile(valid_luminance, 50)))
        highlight_luminance = max(median_luminance, float(np.percentile(valid_luminance, 99)))
    else:
        median_luminance = 0.18
        highlight_luminance = 1.0

    # Adapt the scene to an SDR-like viewing range. The exposure follows the
    # image median, while the white point follows highlights so bright and dark
    # HDR captures both land in a usable SDR range without a per-file preset.
    brightness = max(0.25, min(2.0, float(hdr_tonemap_brightness)))
    exposure = 0.49 * brightness * ((0.77 / median_luminance) ** 0.55)
    exposure = max(0.12, min(2.5, exposure))
    white_point = max(1.1, min(4.0, highlight_luminance * exposure * 1.25))
    gamma = 0.95
    output_white = 0.96
    rgb = rgb * exposure
    luminance = rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152 + rgb[:, :, 2] * 0.0722
    mapped_luminance = luminance * (1.0 + luminance / (white_point * white_point)) / (1.0 + luminance)
    scale = np.divide(mapped_luminance, luminance, out=np.ones_like(luminance), where=luminance > 0.000001)
    rgb = np.clip(rgb * scale[:, :, None], 0.0, 1.0)
    rgb = np.power(rgb, gamma)
    srgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1.0 / 2.4) - 0.055)
    srgb = np.clip(srgb * output_white, 0.0, 1.0)
    alpha = np.nan_to_num(half[:, :, 3:4], nan=1.0, posinf=1.0, neginf=0.0)
    alpha = np.clip(alpha, 0.0, 1.0)
    output = np.concatenate((srgb, alpha), axis=2)
    output = np.clip(output * 255.0 + 0.5, 0.0, 255.0).astype(np.uint8)
    output_data = output.tobytes()
    return QImage(output_data, width, height, QImage.Format_RGBA8888).copy()


ACTION_DEFS = [
    ("open_image", "画像を開く"),
    ("open_folder", "フォルダを開く"),
    ("parent_folder", "親フォルダへ移動"),
    ("next_folder", "次フォルダへ移動"),
    ("child_folder", "子フォルダへ移動"),
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
    ("generate_novelai", "NovelAI画像生成"),
    ("delete_current_image", "現在画像を削除"),
    ("actual_size", "等倍表示"),
    ("fit_view", "画面フィット表示"),
    ("rotate_right", "画像右1度回転"),
    ("rotate_left", "画像左1度回転"),
    ("rotate_right_90", "画像右90度回転"),
    ("rotate_left_90", "画像左90度回転"),
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


def version_tuple(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)*)", text)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def compare_versions(left: str, right: str) -> int:
    left_parts = list(version_tuple(left))
    right_parts = list(version_tuple(right))
    length = max(len(left_parts), len(right_parts))
    left_parts.extend([0] * (length - len(left_parts)))
    right_parts.extend([0] * (length - len(right_parts)))
    return (left_parts > right_parts) - (left_parts < right_parts)


def latest_release_info() -> dict[str, str]:
    request = urllib.request.Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{APP_SHORT_NAME}/{APP_VERSION}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))
    tag_name = str(data.get("tag_name") or "").strip()
    return {"tag_name": tag_name, "html_url": RELEASES_PAGE_URL}


def comfyui_api_url(base_url: str, path: str) -> str:
    return f"{(base_url or DEFAULT_COMFYUI_API_URL).rstrip('/')}/{path.lstrip('/')}"


def comfyui_get_json(base_url: str, path: str, timeout: float = 12) -> dict:
    with urllib.request.urlopen(comfyui_api_url(base_url, path), timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def comfyui_post_json(base_url: str, path: str, payload: dict, timeout: float = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        comfyui_api_url(base_url, path),
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def comfyui_upload_image(base_url: str, image_path: Path, timeout: float = 60) -> dict:
    boundary = f"----RAIVComfyUI{uuid.uuid4().hex}"
    filename = image_path.name
    image_bytes = image_path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("ascii"),
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode("utf-8"),
            b"Content-Type: image/png\r\n\r\n",
            image_bytes,
            b"\r\n",
            f"--{boundary}\r\n".encode("ascii"),
            b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
            f"--{boundary}--\r\n".encode("ascii"),
        ]
    )
    request = urllib.request.Request(
        comfyui_api_url(base_url, "/upload/image"),
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_comfyui_api_workflow(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict) and isinstance(data.get("prompt"), dict):
        data = data["prompt"]
    if not isinstance(data, dict):
        raise ValueError("workflow JSON is not an API-format workflow")
    nodes = {str(key): value for key, value in data.items() if isinstance(value, dict)}
    if not nodes or not all(isinstance(value.get("class_type"), str) for value in nodes.values()):
        raise ValueError("workflow JSON must be saved in ComfyUI API format")
    return nodes


def comfyui_node_choices(workflow: dict[str, dict], class_names: set[str]) -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    for node_id, node in workflow.items():
        class_type = str(node.get("class_type") or "")
        if class_type in class_names:
            title = str(node.get("_meta", {}).get("title") or class_type)
            choices.append((node_id, f"{node_id}: {title} ({class_type})"))
    return choices


def comfyui_base_dir_from_system_stats(stats: dict) -> Path | None:
    system = stats.get("system") if isinstance(stats, dict) else None
    argv = system.get("argv") if isinstance(system, dict) else None
    if not isinstance(argv, list):
        return None
    for index, arg in enumerate(argv):
        if str(arg) == "--base-directory" and index + 1 < len(argv):
            return Path(str(argv[index + 1]))
    return None


def comfyui_checkpoint_names(base_url: str, timeout: float = 12) -> list[str]:
    data = comfyui_get_json(base_url, "/object_info/CheckpointLoaderSimple", timeout=timeout)
    node_info = data.get("CheckpointLoaderSimple") if isinstance(data, dict) else None
    required = node_info.get("input", {}).get("required", {}) if isinstance(node_info, dict) else {}
    ckpt = required.get("ckpt_name") if isinstance(required, dict) else None
    if isinstance(ckpt, list) and ckpt and isinstance(ckpt[0], list):
        return [str(name) for name in ckpt[0]]
    return []


def comfyui_controlnet_names(base_url: str, timeout: float = 12) -> list[str]:
    data = comfyui_get_json(base_url, "/object_info/ControlNetLoader", timeout=timeout)
    node_info = data.get("ControlNetLoader") if isinstance(data, dict) else None
    required = node_info.get("input", {}).get("required", {}) if isinstance(node_info, dict) else {}
    control_net = required.get("control_net_name") if isinstance(required, dict) else None
    if isinstance(control_net, list) and control_net and isinstance(control_net[0], list):
        return [str(name) for name in control_net[0]]
    return []


def default_comfyui_workflow(model_name: str, controlnet_name: str) -> dict[str, dict]:
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": model_name},
            "_meta": {"title": "Checkpoint"},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": DEFAULT_COLORIZE_POSITIVE_PROMPT,
            },
            "_meta": {"title": "Positive Prompt"},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": DEFAULT_COLORIZE_NEGATIVE_PROMPT,
            },
            "_meta": {"title": "Negative Prompt"},
        },
        "4": {
            "class_type": "LoadImage",
            "inputs": {"image": ""},
            "_meta": {"title": "RAIV Input Image"},
        },
        "5": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["4", 0], "vae": ["1", 2]},
            "_meta": {"title": "Encode Input"},
        },
        "9": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": controlnet_name},
            "_meta": {"title": "Lineart ControlNet"},
        },
        "10": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["2", 0],
                "negative": ["3", 0],
                "control_net": ["9", 0],
                "image": ["4", 0],
                "strength": 0.65,
                "start_percent": 0.0,
                "end_percent": 0.65,
                "vae": ["1", 2],
            },
            "_meta": {"title": "Apply Lineart ControlNet"},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["10", 0],
                "negative": ["10", 1],
                "latent_image": ["5", 0],
                "seed": 0,
                "steps": 28,
                "cfg": 5.2,
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "denoise": 0.62,
            },
            "_meta": {"title": "Colorize"},
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
            "_meta": {"title": "Decode"},
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"images": ["7", 0], "filename_prefix": "RAIV_colorized"},
            "_meta": {"title": "RAIV Output"},
        },
}


def save_default_comfyui_workflow(path: Path, model_name: str, controlnet_name: str) -> None:
    atomic_write_text(path, json.dumps(default_comfyui_workflow(model_name, controlnet_name), ensure_ascii=False, indent=2))


def preserve_original_luminance(
    source_path: Path,
    generated_bytes: bytes,
    saturation_boost: float = 1.35,
    luminance_preserve: float = 0.72,
) -> bytes:
    if PILImage is None or ImageFilter is None or np is None:
        return generated_bytes
    with PILImage.open(source_path) as source_image:
        source = source_image.convert("L")
    with PILImage.open(io.BytesIO(generated_bytes)) as generated_image:
        generated = generated_image.convert("RGB")
    if source.size != generated.size:
        source = source.resize(generated.size, PILImage.Resampling.LANCZOS)
    color_source = generated.filter(ImageFilter.GaussianBlur(radius=1.4))
    generated_hsv = color_source.convert("HSV")
    hue, saturation, generated_value = generated_hsv.split()
    source_array = np.asarray(source, dtype=np.float32)
    generated_value_array = np.asarray(generated_value, dtype=np.float32)
    saturation_array = np.asarray(saturation, dtype=np.float32)
    saturation_array *= max(0.0, float(saturation_boost))
    saturation_array[source_array < 40] *= 0.12
    saturation_array[(source_array > 238) & (saturation_array < 135)] = 0
    saturation_image = PILImage.fromarray(np.clip(saturation_array, 0, 255).astype(np.uint8), "L")
    preserve = max(0.0, min(1.0, float(luminance_preserve)))
    value_array = generated_value_array * (1.0 - preserve) + source_array * preserve
    value_image = PILImage.fromarray(np.clip(value_array, 0, 255).astype(np.uint8), "L")
    merged = PILImage.merge("HSV", (hue, saturation_image, value_image)).convert("RGB")
    buffer = io.BytesIO()
    merged.save(buffer, format="PNG")
    return buffer.getvalue()

UI_TEXT_EN = {
    "画像を開く": "Open image",
    "フォルダを開く": "Open folder",
    "親フォルダへ移動": "Move to parent folder",
    "次フォルダへ移動": "Move to next folder",
    "子フォルダへ移動": "Move to child folder",
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
    "NovelAI画像生成": "Generate NovelAI image",
    "現在画像を削除": "Delete current image",
    "等倍表示": "Actual size",
    "画面フィット表示": "Fit to window",
    "画像右1度回転": "Rotate right 1 degree",
    "画像左1度回転": "Rotate left 1 degree",
    "画像右90度回転": "Rotate right 90 degrees",
    "画像左90度回転": "Rotate left 90 degrees",
    "画像左右反転": "Flip horizontal",
    "画像上下反転": "Flip vertical",
    "設定": "Settings",
    "固定": "Pin",
    "固定中": "Pinned",
    "自動表示": "Auto",
    "左へ移動する": "Move left",
    "右へ移動する": "Move right",
    "エンジン設定": "Engine",
    "全般": "General",
    "画像調整": "Image Adjustment",
    "AI彩色(β)": "AI Colorize (beta)",
    "NovelAI生成": "NovelAI Generation",
    "その他": "Other",
    "キーコンフィグ": "Key Config",
    "エンジン": "Engine",
    "モデル": "Model",
    "倍率": "Scale",
    "倍率を自動で決定する": "Choose scale automatically",
    "ノイズ": "Denoise",
    "Real-ESRGANモデル": "Real-ESRGAN model",
    "ノイズ: -1 はノイズ除去なし。0/1/2/3 は数値が大きいほど強く除去します。": "Denoise: -1 disables denoising. 0/1/2/3 remove noise more strongly as the value increases.",
    "Real-ESRGANはノイズ値を使わず、モデルで画風や復元傾向を選びます。": "Real-ESRGAN does not use the denoise value. Choose a model to change image style and restoration behavior.",
    "realesr-animevideov3: アニメ/イラスト向けの軽量標準モデル。 realesrgan-x4plus: 写真や一般画像向け。 realesrgan-x4plus-anime: アニメ/イラスト向けのx4plus派生モデル。 realesr-animevideov3は2倍/3倍/4倍、x4plus系は4倍に対応します。": "realesr-animevideov3: lightweight standard model for anime/illustration. realesrgan-x4plus: for photos and general images. realesrgan-x4plus-anime: x4plus-derived model for anime/illustration. realesr-animevideov3 supports 2x/3x/4x; x4plus models support 4x.",
    "Gigapixel AI CLIはProライセンスが必要です。各補正は0で無効、1～100で強度を指定します。": "Gigapixel AI CLI requires a Pro license. Set each adjustment to 0 to disable it, or 1-100 for its strength.",
    "tile: 0 は自動。内蔵GPUなどでメモリ不足になる場合は 128 や 256 など小さめの値を指定すると安定しやすくなりますが、遅くなることがあります。": "tile: 0 is automatic. If an integrated GPU runs out of memory, smaller values such as 128 or 256 can improve stability, but processing may be slower.",
    "エンジン先読み": "Engine prefetch",
    "選択中の拡大エンジンで処理を先に進める枚数。大きいほど待ち時間を減らせますが、GPU負荷と一時ファイル作成が増えます。": "Number of images to process ahead with the selected engine. Higher values reduce waiting but increase GPU load and temporary files.",
    "AI彩色を先行処理する": "Prefetch AI colorization",
    "彩色結果をフォルダに保存": "Save colorized results to folder",
    "彩色フォルダがあれば表示に使う": "Use colorized folder when available",
    "AI彩色先読み": "AI colorize prefetch",
    "彩色済み画像がないページだけComfyUIへ送ります。既存の彩色結果は上書きせず、手動の「現在画像を彩色」だけ上書きします。": "Sends only pages without colorized images to ComfyUI. Existing colorized results are not overwritten; only the manual Colorize current image action overwrites them.",
    "縦サイズが閾値以上なら拡大処理しない": "Skip processing when height is at or above threshold",
    "縦サイズ閾値(px)": "Height threshold (px)",
    "モニタ解像度以上の画像をさらに拡大しても表示上の効果は小さく、処理時間とメモリ使用量が増えます。普段使うモニタの縦解像度に合わせる設定が目安です。": "Upscaling images already above monitor resolution often has little visible benefit and increases processing time and memory usage. Set this near your usual monitor height.",
    "画像ごとに、現在のエンジンとモデルで選択可能な倍率から、縦サイズ閾値へ届く最小倍率を選びます。届かない場合は最大倍率を使います。": "For each image, chooses the smallest scale available for the current engine and model that reaches the height threshold. If none reaches it, the maximum scale is used.",
    "拡大結果を倍率フォルダに保存": "Save processed results to scale folder",
    "倍率フォルダがあれば表示に使う": "Use scale folder when available",
    "現在選択中のエンジン、モデル、倍率に完全一致する倍率フォルダだけを表示に使います。別エンジンや別倍率の結果にはフォールバックしません。": "Only the scale folder that exactly matches the current engine, model, and scale is used for display. Results from another engine or scale are not used as fallback.",
    "アーカイブ表示中は保存先フォルダがないため、倍率フォルダ保存と倍率フォルダ読み込みは無効です。": "Scale-folder saving/loading is disabled while viewing archives because there is no output folder.",
    "再実行": "Run again",
    "コマンドテンプレート": "Command template",
    "エンジンexeを選択": "Select engine exe",
    "使用できる置換: {input} {output} {output_dir} {scale} {denoise} {tile} {model} {sharpen} {compression} {face_recovery}": "Available placeholders: {input} {output} {output_dir} {scale} {denoise} {tile} {model} {sharpen} {compression} {face_recovery}",
    "次回起動時に古い一時ファイルを削除": "Delete old temporary files on next startup",
    "アプリの二重起動を禁止する": "Prevent multiple app instances",
    "AI彩色を表示しない": "Hide AI Colorize tab",
    "NovelAI生成を表示しない": "Hide NovelAI Generation tab",
    "キーコンフィグを表示しない": "Hide Key Config tab",
    "最後に開いていた画像を次回起動時に開く": "Open the last viewed image on startup",
    "フォルダごとに最後に開いていた画像を記録する": "Remember last viewed image for each folder",
    "フォルダ履歴保存件数": "Folder history limit",
    "0 は無制限。履歴は setting.json ではなく folder_history.json に保存します。": "0 means unlimited. History is saved to folder_history.json, not setting.json.",
    "削除時、拡大結果も削除する": "Also delete processed results when deleting",
    "削除時に確認メッセージを出す": "Show confirmation before deleting",
    "バージョン": "Version",
    "アップデートを確認": "Check for updates",
    "表示言語": "Language",
    "テーマ": "Theme",
    "Windowsの設定に同期": "Follow Windows settings",
    "ライトテーマ": "Light theme",
    "ダークテーマ": "Dark theme",
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
    "回転時に表示全体をフィットし直す": "Refit whole image after rotation",
    "オフの時は回転してもズーム倍率を維持します。オンにすると、回転後の縦横サイズに合わせて画像全体が収まる倍率へ調整します。": "When off, rotation preserves the current zoom. When on, RAIV adjusts zoom so the whole rotated image fits.",
    "マウス横スクロールでページ送り": "Use horizontal mouse wheel for page navigation",
    "横スクロールのページ送り方向を反転": "Reverse horizontal wheel direction",
    "全画面表示時にマウスカーソルを非表示": "Hide mouse cursor in fullscreen",
    "ドラッグして設定ペインの幅を調整": "Drag to resize the settings pane",
    "画像またはフォルダ/アーカイブをドロップしてください": "Drop an image, folder, or archive",
    "トーンカーブ補正を使う": "Use tone curve adjustment",
    "表示操作": "Display controls",
    "左回転": "Rotate left",
    "右回転": "Rotate right",
    "左右反転": "Flip horizontal",
    "上下反転": "Flip vertical",
    "表示リセット": "Reset display",
    "基本表示調整": "Basic display adjustment",
    "明るさ": "Brightness",
    "コントラスト": "Contrast",
    "ガンマ": "Gamma",
    "シャープネス": "Sharpness",
    "調整をリセット": "Reset adjustments",
    "リセット": "Reset",
    "表示上だけの非破壊調整です。元ファイルや拡大処理済みファイルは変更しません。": "These are non-destructive display-only adjustments. Original and processed files are not changed.",
    "HDR互換表示": "HDR compatible display",
    "HDR互換表示の明るさ": "HDR compatible brightness",
    "100%に戻す": "Reset to 100%",
    "HDR画像を表示している時だけ有効です。100%を基準に、SDR互換表示へ変換する時の明るさを調整します。": "Enabled only while displaying an HDR image. Adjusts brightness during SDR-compatible conversion, with 100% as the baseline.",
    "GIMP .curファイルを使い、輝度に応じてRGBを割り当てます。モノクロ漫画を疑似4色刷りのように表示できます。": "Uses a GIMP .cur file to map luminance to RGB, making monochrome manga look like pseudo four-color printing.",
    "トーンカーブ": "Tone curve",
    "再読み込み": "Reload",
    "フォルダ": "Folder",
    "curフォルダを開く": "Open cur folder",
    "チャンネル": "Channel",
    "保存": "Save",
    "選択中の曲線をドラッグして調整できます。保存するとcurフォルダへGIMP旧形式.curとして出力します。": "Drag the selected curve to adjust it. Save writes a GIMP legacy-format .cur file into the cur folder.",
    "ComfyUI API URL": "ComfyUI API URL",
    "ComfyUIを使用し、表示画像を加工する開発中機能です。主にモノクロ画像のAI彩色を想定しています。IN/OUT制御は実装済みのため、モデルやプロンプトを調整すればユーザー側で目的に近づけられますが、開発者側では画質調整はまだ十分ではありません。": "This is an in-development feature that processes the displayed image using ComfyUI. It is mainly intended for AI colorization of monochrome images. IN/OUT control is implemented, so users can approach their target result by adjusting models and prompts, but image-quality tuning is not yet complete on the developer side.",
    "ComfyUI base directory": "ComfyUI base directory",
    "接続確認": "Check connection",
    "初期設定": "Initial setup",
    "推奨モデルをダウンロード": "Download recommended model",
    "推奨モデル/ControlNetをダウンロード": "Download recommended model / ControlNet",
    "workflow JSON": "Workflow JSON",
    "参照": "Browse",
    "ノード検出": "Detect nodes",
    "入力画像ノード": "Input image node",
    "出力画像ノード": "Output image node",
    "現在画像を彩色": "Colorize current image",
    "ComfyUIを起動しておき、初期設定を実行してください。推奨モデルがある場合はRAIV用workflowを自動生成します。": "Start ComfyUI first, then run initial setup. If the recommended model exists, RAIV generates its workflow automatically.",
    "NovelAIの永続APIトークンを使い、テキストから画像を生成してRAIVへ取り込みます。バイブストランスファー、画像から画像生成、インペイントは未対応です。": "Generate text2img images with a NovelAI Persistent API Token and import them into RAIV. Vibe Transfer, img2img, and inpaint are not supported yet.",
    "永続APIトークン": "Persistent API Token",
    "保存先": "Output folder",
    "日付": "Date",
    "ファイル名": "Filename",
    "日付_時刻": "Date_Time",
    "時刻": "Time only",
    "日付/シード値": "Date/Seed",
    "日付/時刻": "Date/Time",
    "日付/時刻_シード値": "Date/Time_Seed",
    "カスタム": "Custom",
    "使用できる変数:\n{YYYY}: 年（4桁）\n{MM}: 月（2桁）\n{DD}: 日（2桁）\n{HH}: 時（2桁）\n{mm}: 分（2桁）\n{ss}: 秒（2桁）\n{date}: 日付まとめ（YYYYMMDD）\n{time}: 時刻まとめ（HHMMSS）\n{seed}: 生成シード値\n/ または \\: フォルダ区切り（入れ子可能）\n末尾がフォルダ区切りの場合、ファイル名に {seed} を補います。\n例: {date}/{time}_{seed}": "Available variables:\n{YYYY}: Year (4 digits)\n{MM}: Month (2 digits)\n{DD}: Day (2 digits)\n{HH}: Hour (2 digits)\n{mm}: Minute (2 digits)\n{ss}: Second (2 digits)\n{date}: Full date (YYYYMMDD)\n{time}: Full time (HHMMSS)\n{seed}: Generation seed\n/ or \\: Folder separator (nested folders supported)\nIf the template ends with a folder separator, {seed} is appended as the filename.\nExample: {date}/{time}_{seed}",
    "プロンプトを分解する": "Split prompts into tags",
    "再構築したプロンプトを表示する": "Show reconstructed prompts",
    "プロンプト": "Prompt",
    "プロンプト >": "Prompt >",
    "プロンプト v": "Prompt v",
    "除外したい要素 >": "Undesired Content >",
    "除外したい要素 v": "Undesired Content v",
    "タグプリセット": "Tag preset",
    "読込": "Load",
    "追加": "Add",
    "フォルダ追加": "Add folder",
    "フォルダ名": "Folder name",
    "新しいフォルダ": "New folder",
    "開く / 閉じる": "Expand / Collapse",
    "ランダム": "Random",
    "フォルダ内からランダムに選択": "Randomly select from this folder",
    "タグプリセット名": "Tag preset name",
    "有効 / 無効": "Enable / Disable",
    "移動": "Move",
    "上へ": "Move up",
    "下へ": "Move down",
    "強調": "Boost",
    "強調：全体を{ }で囲み、強度を1.05倍（重ね掛け可）": "Boost: Wraps the entire prompt in { } and multiplies strength by 1.05 (stackable)",
    "抑制": "Weak",
    "抑制：全体を[ ]で囲み、強度を1/1.05倍（重ね掛け可）": "Suppress: Wraps the entire prompt in [ ] and multiplies strength by 1/1.05 (stackable)",
    "削除": "Delete",
    "連続生成中": "Continuous generation",
    "停止中": "Stopping",
    "連続生成間隔": "Continuous interval",
    "秒": "sec",
    "サイズ": "Size",
    "プロンプト": "Prompt",
    "先頭に追加する": "Add at top",
    "除外したい要素": "Undesired Content",
    "モデル": "Model",
    "サンプラー": "Sampler",
    "ノイズスケジュール": "Noise Schedule",
    "画像解像度": "Image Resolution",
    "幅 / 高さ": "Width / Height",
    "ステップ数": "Steps",
    "プロンプトガイダンス": "Prompt Guidance",
    "プロンプトガイダンスの再調整": "Prompt Guidance Rescale",
    "多様性": "Variety",
    "生成枚数": "Number of Images",
    "ランダムシード": "Random Seed",
    "シード値": "Seed",
    "Enterで生成する（改行はShift+Enter）": "Generate with Enter (Shift+Enter inserts a line break)",
    "フォルダ削除時、中身ごと消す": "Delete folder contents with folder",
    "品質タグを追加する": "Add quality tags",
    "除外プリセット": "Undesired Content preset",
    "モード": "Mode",
    "アニメモード": "Anime mode",
    "ケモノモード": "Furry mode",
    "詳細設定 >": "Advanced Settings >",
    "詳細設定 v": "Advanced Settings v",
    "強い": "Strong",
    "弱い": "Light",
    "ケモノモード": "Furry Focus",
    "人間に重点を置く": "Human Focus",
    "指定なし": "None",
    "OpusプランとしてAnlasを推定": "Estimate Anlas as Opus plan",
    "生成後に自動表示": "Display after generation",
    "生成後に拡大処理キューへ投入": "Enqueue upscaling after generation",
    "生成設定をJSONサイドカーに保存": "Save settings as JSON sidecar",
    "生成": "Generate",
    "生成中": "Generating",
    "メタデータをインポート": "Import metadata",
    "NovelAIメタデータを読み込めませんでした。": "Could not load NovelAI metadata.",
    "NovelAIメタデータをインポートしました。": "Imported NovelAI metadata.",
    "推定消費Anlas: novelai-sdk未インストール、または現在の設定では推定できません。": "Estimated Anlas: novelai-sdk is not installed, or the current settings cannot be estimated.",
    "値": "Value",
    "赤": "Red",
    "緑": "Green",
    "青": "Blue",
    "アルファ": "Alpha",
    "状態": "Status",
    "ログを表示": "Show log",
    "拡大前メモリ読込": "Original memory load",
    "AI彩色画像生成": "AI color image generation",
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
    "画像を削除できませんでした。": "Could not delete the image.",
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
        "parent_folder": {"keyboard": key_binding(Qt.Key_Up), "mouse": None},
        "next_folder": {"keyboard": key_binding(Qt.Key_Down), "mouse": None},
        "child_folder": {"keyboard": key_binding(Qt.Key_Down, Qt.ControlModifier.value), "mouse": None},
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
        "rotate_right_90": {"keyboard": key_binding(Qt.Key_R, Qt.ShiftModifier.value), "mouse": None},
        "rotate_left_90": {"keyboard": key_binding(Qt.Key_L, Qt.ShiftModifier.value), "mouse": None},
        "flip_horizontal": {"keyboard": key_binding(Qt.Key_H), "mouse": None},
        "flip_vertical": {"keyboard": key_binding(Qt.Key_V), "mouse": None},
        "generate_novelai": {"keyboard": key_binding(Qt.Key_G), "mouse": None},
        "delete_current_image": {"keyboard": key_binding(Qt.Key_Delete), "mouse": None},
    }


@dataclass
class AppConfig:
    engine: str = ENGINE_REALCUGAN
    command_template: str = DEFAULT_REALCUGAN_TEMPLATE
    realcugan_command_template: str = DEFAULT_REALCUGAN_TEMPLATE
    realesrgan_command_template: str = DEFAULT_REALESRGAN_TEMPLATE
    gigapixel_command_template: str = DEFAULT_GIGAPIXEL_TEMPLATE
    scale: int = 2
    realesrgan_scale: int = 4
    gigapixel_scale: int = 2
    denoise: int = 0
    tile: int = 0
    realesrgan_model: str = "realesr-animevideov3"
    gigapixel_model: str = "standard"
    gigapixel_denoise: int = 0
    gigapixel_sharpen: int = 0
    gigapixel_compression: int = 0
    gigapixel_face_recovery: int = 0
    realcugan_prefetch_count: int = 10
    save_colorized_to_folder: bool = True
    use_colorized_folder_cache: bool = True
    colorize_prefetch_enabled: bool = False
    colorize_prefetch_count: int = 0
    colorize_denoise: float = 0.62
    colorize_controlnet_strength: float = 0.65
    colorize_controlnet_end: float = 0.65
    colorize_saturation_boost: float = 1.35
    colorize_luminance_preserve: float = 0.72
    colorize_positive_prompt: str = DEFAULT_COLORIZE_POSITIVE_PROMPT
    colorize_negative_prompt: str = DEFAULT_COLORIZE_NEGATIVE_PROMPT
    novelai_api_token: str = ""
    novelai_output_dir: str = str(DEFAULT_NOVELAI_GENERATED_DIR)
    novelai_output_name_mode: str = "seed"
    novelai_output_name_template: str = "{seed}"
    novelai_prompt: str = ""
    novelai_negative_prompt: str = ""
    novelai_split_prompts: bool = False
    novelai_show_reconstructed_prompts: bool = False
    novelai_add_prompt_items_at_top: bool = False
    novelai_prompt_items: list[dict[str, object]] = field(default_factory=list)
    novelai_negative_prompt_items: list[dict[str, object]] = field(default_factory=list)
    novelai_prompt_editor_height: int = 260
    novelai_negative_prompt_editor_height: int = 220
    novelai_prompt_expanded: bool = True
    novelai_negative_prompt_expanded: bool = True
    novelai_enter_to_generate: bool = True
    novelai_delete_folder_contents: bool = False
    novelai_quality_tags: bool = True
    novelai_uc_preset: str = "strong"
    novelai_dataset_mode: str = "anime"
    novelai_model: str = DEFAULT_NOVELAI_MODEL
    novelai_sampler: str = DEFAULT_NOVELAI_SAMPLER
    novelai_scheduler: str = DEFAULT_NOVELAI_SCHEDULER
    novelai_seed: int = 0
    novelai_random_seed: bool = True
    novelai_width: int = 832
    novelai_height: int = 1216
    novelai_steps: int = 28
    novelai_scale: float = 5.0
    novelai_cfg_rescale: float = 0.0
    novelai_variety_boost: bool = False
    novelai_batch_count: int = 1
    novelai_is_opus: bool = False
    novelai_auto_open: bool = True
    novelai_auto_upscale: bool = True
    novelai_save_metadata_json: bool = False
    novelai_detail_expanded: bool = True
    novelai_continuous_delay_seconds: float = 3.0
    viewer_prefetch_count: int = 20
    save_upscaled_to_scale_folder: bool = False
    use_scale_folder_cache: bool = True
    skip_realcugan_for_tall_images: bool = True
    skip_realcugan_height_threshold: int = 2160
    auto_realcugan_scale: bool = False
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
    display_brightness: float = 0.0
    display_contrast: float = 1.0
    display_gamma: float = 1.0
    display_sharpness: float = 0.0
    hdr_tonemap_brightness: float = 1.0
    hide_cursor_in_fullscreen: bool = False
    show_log_panel: bool = False
    show_profile_panel: bool = False
    ui_language: str = "ja"
    ui_theme: str = THEME_SYSTEM
    thumbnail_enabled: bool = True
    thumbnail_pinned: bool = False
    thumbnail_size: int = 96
    thumbnail_height: int = 142
    horizontal_wheel_navigation: bool = False
    horizontal_wheel_inverted: bool = False
    wrap_page_navigation: bool = False
    preserve_view_on_page_navigation: bool = False
    refit_view_on_rotation: bool = False
    invert_page_position_slider: bool = True
    page_scroll_interval_ms: int = 1
    arrow_right_next: bool = True
    key_bindings: dict[str, dict[str, dict | None]] = field(default_factory=default_key_bindings)
    cleanup_temp_on_start: bool = False
    single_instance_enabled: bool = False
    restore_last_image_on_start: bool = False
    last_image_path: str = ""
    remember_last_image_per_folder: bool = False
    folder_history_limit: int = 1000
    comfyui_api_url: str = DEFAULT_COMFYUI_API_URL
    comfyui_base_dir: str = ""
    comfyui_workflow_path: str = ""
    comfyui_input_node_id: str = ""
    comfyui_output_node_id: str = ""
    settings_tab: str = "realcugan"
    window_rect: list[int] | None = None
    window_maximized: bool = False
    window_geometry: str = ""
    side_panel_visible: bool = True
    side_panel_pinned: bool = True
    side_panel_width: int = 460
    side_panel_on_left: bool = False
    hide_colorize_tab: bool = False
    hide_novelai_tab: bool = False
    hide_keyconfig_tab: bool = False
    confirm_delete_current_image: bool = True
    delete_processed_with_source: bool = True
    splitter_sizes: list[int] | None = None
    last_dir: str = ""


@dataclass(frozen=True)
class UpscaleTask:
    source: Path
    engine_input: Path
    key: tuple
    engine: str
    engine_label: str
    command_template: str
    scale: int
    denoise: int
    tile: int
    model: str
    sharpen: int
    compression: int
    face_recovery: int
    cache_path: Path | None
    read_cache: bool
    save_to_cache: bool
    force: bool
    skip_tall_images: bool
    skip_height_threshold: int
    hdr_tonemap_brightness: float


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def bytes_to_blob(data: bytes) -> DATA_BLOB:
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    blob._buffer = buffer  # type: ignore[attr-defined]
    return blob


def blob_to_bytes(blob: DATA_BLOB) -> bytes:
    if not blob.pbData or blob.cbData == 0:
        return b""
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob.pbData)


def dpapi_protect(data: bytes) -> bytes:
    input_blob = bytes_to_blob(data)
    output_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(byref(input_blob), None, None, None, None, 0, byref(output_blob)):
        raise OSError(ctypes.get_last_error())
    return blob_to_bytes(output_blob)


def dpapi_unprotect(data: bytes) -> bytes:
    input_blob = bytes_to_blob(data)
    output_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(byref(input_blob), None, None, None, None, 0, byref(output_blob)):
        raise OSError(ctypes.get_last_error())
    return blob_to_bytes(output_blob)


def load_novelai_api_token() -> str:
    if not NOVELAI_TOKEN_PATH.exists():
        return ""
    try:
        return dpapi_unprotect(NOVELAI_TOKEN_PATH.read_bytes()).decode("utf-8")
    except Exception:
        return ""


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        temp_path.write_bytes(data)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def save_novelai_api_token(token: str) -> None:
    token = token.strip()
    if not token:
        if NOVELAI_TOKEN_PATH.exists():
            NOVELAI_TOKEN_PATH.unlink()
        return
    atomic_write_bytes(NOVELAI_TOKEN_PATH, dpapi_protect(token.encode("utf-8")))


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


def apply_application_color_scheme(theme: str) -> None:
    app = QApplication.instance()
    if app is None:
        return
    style_hints = app.styleHints()
    if theme == THEME_LIGHT:
        style_hints.setColorScheme(Qt.ColorScheme.Light)
    elif theme == THEME_DARK:
        style_hints.setColorScheme(Qt.ColorScheme.Dark)
    else:
        style_hints.unsetColorScheme()
    QTimer.singleShot(0, refresh_application_style)


def refresh_application_style() -> None:
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.allWidgets():
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()


class WheelRequiresFocusMixin:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event) -> None:
        focus_widget = QApplication.focusWidget()
        has_focus = focus_widget is self or (focus_widget is not None and self.isAncestorOf(focus_widget))
        if self.window().isActiveWindow() and has_focus:
            super().wheelEvent(event)
            return
        event.ignore()


class QComboBox(WheelRequiresFocusMixin, QtComboBox):
    pass


class QSpinBox(WheelRequiresFocusMixin, QtSpinBox):
    pass


class QDoubleSpinBox(WheelRequiresFocusMixin, QtDoubleSpinBox):
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
        defaults = asdict(AppConfig())
        legacy_prompt_splitter_sizes = data.get("novelai_prompt_splitter_sizes") if isinstance(data, dict) else None
        filtered_data = {key: value for key, value in data.items() if key in defaults} if isinstance(data, dict) else {}
        config = AppConfig(**{**defaults, **filtered_data})
        if (
            "novelai_prompt_editor_height" not in filtered_data
            and "novelai_negative_prompt_editor_height" not in filtered_data
            and isinstance(legacy_prompt_splitter_sizes, list)
            and len(legacy_prompt_splitter_sizes) == 2
            and all(isinstance(size, int) and size > 0 for size in legacy_prompt_splitter_sizes)
        ):
            config.novelai_prompt_editor_height = legacy_prompt_splitter_sizes[0]
            config.novelai_negative_prompt_editor_height = legacy_prompt_splitter_sizes[1]
        if config.command_template == LEGACY_REALCUGAN_TEMPLATE and BUNDLED_REALCUGAN_EXE.exists():
            config.command_template = DEFAULT_REALCUGAN_TEMPLATE
        if config.realcugan_command_template in {LEGACY_REALCUGAN_TEMPLATE, ""} and BUNDLED_REALCUGAN_EXE.exists():
            config.realcugan_command_template = DEFAULT_REALCUGAN_TEMPLATE
        if config.realesrgan_command_template in {LEGACY_REALESRGAN_TEMPLATE, ""} and BUNDLED_REALESRGAN_EXE.exists():
            config.realesrgan_command_template = DEFAULT_REALESRGAN_TEMPLATE
        if not config.gigapixel_command_template or config.gigapixel_command_template == LEGACY_GIGAPIXEL_TEMPLATE:
            config.gigapixel_command_template = DEFAULT_GIGAPIXEL_TEMPLATE
        if "realcugan_command_template" not in data:
            config.realcugan_command_template = config.command_template or DEFAULT_REALCUGAN_TEMPLATE
        if config.engine not in ENGINE_LABELS:
            config.engine = ENGINE_REALCUGAN
        if config.realesrgan_model not in REALESRGAN_MODELS:
            config.realesrgan_model = REALESRGAN_MODELS[0]
        gigapixel_model_ids = {model for _label, model in GIGAPIXEL_MODELS}
        if config.gigapixel_model not in gigapixel_model_ids:
            config.gigapixel_model = GIGAPIXEL_MODELS[0][1]
        config.scale = min(REALCUGAN_SCALES, key=lambda value: abs(value - int(config.scale)))
        realesrgan_scales = REALESRGAN_MODEL_SCALES[config.realesrgan_model]
        config.realesrgan_scale = min(realesrgan_scales, key=lambda value: abs(value - int(config.realesrgan_scale)))
        gigapixel_scales = GIGAPIXEL_MODEL_SCALES[config.gigapixel_model]
        config.gigapixel_scale = min(gigapixel_scales, key=lambda value: abs(value - int(config.gigapixel_scale)))
        config.gigapixel_denoise = max(0, min(100, int(config.gigapixel_denoise)))
        config.gigapixel_sharpen = max(0, min(100, int(config.gigapixel_sharpen)))
        config.gigapixel_compression = max(0, min(100, int(config.gigapixel_compression)))
        config.gigapixel_face_recovery = max(0, min(100, int(config.gigapixel_face_recovery)))
        if config.cpu_resample_algorithm not in RESAMPLE_ALGORITHMS:
            config.cpu_resample_algorithm = DEFAULT_RESAMPLE_ALGORITHM
        if not config.novelai_output_dir:
            config.novelai_output_dir = str(DEFAULT_NOVELAI_GENERATED_DIR)
        if "novelai_output_name_template" not in filtered_data:
            legacy_filename_mode = str(data.get("novelai_filename_mode", "seed"))
            filename_template = str(data.get("novelai_filename_template", "{seed}")).strip() or "{seed}"
            legacy_filename_templates = {
                "time": "{YYYY}{MM}{DD}_{HH}{mm}{ss}",
                "time_only": "{HH}{mm}{ss}",
            }
            if legacy_filename_mode in legacy_filename_templates:
                filename_template = legacy_filename_templates[legacy_filename_mode]
            if bool(data.get("novelai_date_subfolders", False)):
                subfolder_template = str(data.get("novelai_subfolder_template", "{YYYY}-{MM}-{DD}")).strip().rstrip("/\\")
                config.novelai_output_name_template = f"{subfolder_template}/{filename_template}"
            else:
                config.novelai_output_name_template = filename_template
        config.novelai_output_name_template = str(config.novelai_output_name_template).strip() or "{seed}"
        matching_mode = next(
            (mode for mode, template in NOVELAI_OUTPUT_NAME_TEMPLATES.items() if template == config.novelai_output_name_template),
            "custom",
        )
        if "novelai_output_name_mode" not in filtered_data or config.novelai_output_name_mode not in {
            *NOVELAI_OUTPUT_NAME_TEMPLATES,
            "custom",
        }:
            config.novelai_output_name_mode = matching_mode
        if config.novelai_uc_preset not in {key for key, _label in NOVELAI_UC_PRESET_OPTIONS}:
            config.novelai_uc_preset = "strong"
        if config.novelai_dataset_mode not in {key for key, _label in NOVELAI_DATASET_MODE_OPTIONS}:
            config.novelai_dataset_mode = "anime"
        config.novelai_prompt_editor_height = max(0, int(config.novelai_prompt_editor_height))
        config.novelai_negative_prompt_editor_height = max(0, int(config.novelai_negative_prompt_editor_height))
        if not config.novelai_model or config.novelai_model not in NOVELAI_MODEL_OPTIONS:
            config.novelai_model = DEFAULT_NOVELAI_MODEL
        if not config.novelai_sampler or config.novelai_sampler not in NOVELAI_SAMPLER_OPTIONS:
            config.novelai_sampler = DEFAULT_NOVELAI_SAMPLER
        if not config.novelai_scheduler or config.novelai_scheduler not in NOVELAI_SCHEDULER_OPTIONS:
            config.novelai_scheduler = DEFAULT_NOVELAI_SCHEDULER
        config.novelai_seed = max(0, min(MAX_NOVELAI_SEED, int(config.novelai_seed)))
        config.novelai_width = max(64, min(4096, int(config.novelai_width)))
        config.novelai_height = max(64, min(4096, int(config.novelai_height)))
        config.novelai_steps = max(1, min(150, int(config.novelai_steps)))
        config.novelai_scale = max(0.0, min(30.0, float(config.novelai_scale)))
        config.novelai_cfg_rescale = max(0.0, min(1.0, float(config.novelai_cfg_rescale)))
        config.novelai_batch_count = max(1, min(8, int(config.novelai_batch_count)))
        config.novelai_continuous_delay_seconds = max(0.1, min(3600.0, float(config.novelai_continuous_delay_seconds)))
        config.display_brightness = max(-100.0, min(100.0, float(config.display_brightness)))
        config.display_contrast = max(0.0, min(3.0, float(config.display_contrast)))
        config.display_gamma = max(0.1, min(5.0, float(config.display_gamma)))
        config.display_sharpness = max(0.0, min(5.0, float(config.display_sharpness)))
        config.hdr_tonemap_brightness = max(0.25, min(2.0, float(config.hdr_tonemap_brightness)))
        if config.ui_language not in {"ja", "en"}:
            config.ui_language = "ja"
        if config.ui_theme not in {key for key, _label in THEME_OPTIONS}:
            config.ui_theme = THEME_SYSTEM
        config.key_bindings = normalize_key_bindings(getattr(config, "key_bindings", None))
        if BUNDLED_REALCUGAN_EXE.exists() and not command_executable_exists(config.realcugan_command_template):
            config.realcugan_command_template = DEFAULT_REALCUGAN_TEMPLATE
        if BUNDLED_REALESRGAN_EXE.exists() and not command_executable_exists(config.realesrgan_command_template):
            config.realesrgan_command_template = DEFAULT_REALESRGAN_TEMPLATE
        if DEFAULT_GIGAPIXEL_EXE.exists() and not command_executable_exists(config.gigapixel_command_template):
            config.gigapixel_command_template = DEFAULT_GIGAPIXEL_TEMPLATE
        if "compare_split" in data and 0 <= int(data.get("compare_split", 500)) <= 100:
            config.compare_split = int(data["compare_split"]) * 10
        legacy_token = str(config.novelai_api_token or "").strip()
        if legacy_token:
            try:
                if not load_novelai_api_token():
                    save_novelai_api_token(legacy_token)
            except Exception:
                pass
            config.novelai_api_token = ""
        return config
    except Exception:
        return AppConfig()


def save_config(config: AppConfig) -> None:
    data = asdict(config)
    data["novelai_api_token"] = ""
    atomic_write_text(CONFIG_PATH, json.dumps(data, ensure_ascii=False, indent=2))


def load_folder_history() -> dict[str, dict[str, object]]:
    if not FOLDER_HISTORY_PATH.exists():
        return {}
    try:
        data = json.loads(FOLDER_HISTORY_PATH.read_text(encoding="utf-8-sig"))
        entries = data.get("entries", data) if isinstance(data, dict) else {}
        if not isinstance(entries, dict):
            return {}
        normalized: dict[str, dict[str, object]] = {}
        for folder, entry in entries.items():
            if isinstance(folder, str) and isinstance(entry, dict) and isinstance(entry.get("image"), str):
                normalized[folder] = {
                    "image": entry["image"],
                    "updated": float(entry.get("updated", 0)),
                }
        return normalized
    except Exception:
        return {}


def save_folder_history(entries: dict[str, dict[str, object]]) -> None:
    atomic_write_text(FOLDER_HISTORY_PATH, json.dumps({"entries": entries}, ensure_ascii=False, indent=2))


def load_novelai_prompt_presets() -> list[dict[str, object]]:
    if not NOVELAI_PROMPT_PRESETS_PATH.exists():
        return []
    try:
        data = json.loads(NOVELAI_PROMPT_PRESETS_PATH.read_text(encoding="utf-8-sig"))
        presets = data.get("presets", data) if isinstance(data, dict) else data
        if not isinstance(presets, list):
            return []
        return [preset for preset in presets if isinstance(preset, dict) and str(preset.get("name") or "").strip()]
    except Exception:
        return []


def save_novelai_prompt_presets(presets: list[dict[str, object]]) -> None:
    atomic_write_text(NOVELAI_PROMPT_PRESETS_PATH, json.dumps({"presets": presets}, ensure_ascii=False, indent=2))


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    kernel32 = ctypes.windll.kernel32
    kernel32.SetLastError(0)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    handle = open_process(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        close_handle(handle)
        return True
    return int(kernel32.GetLastError()) == ERROR_ACCESS_DENIED


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
    atomic_write_text(path, "\r\n".join(lines) + "\r\n")


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
    process_started = Signal(object)
    process_done = Signal(object)
    folder_images_ready = Signal(object, object)
    prefetch_done = Signal(int, object, object, object, object)
    thumbnail_done = Signal(int, int, object)
    profile_event = Signal(str, float)
    update_check_done = Signal(object)
    comfyui_connection_done = Signal(object)
    comfyui_colorize_done = Signal(object)
    comfyui_setup_done = Signal(object)
    comfyui_download_progress = Signal(object)
    comfyui_download_done = Signal(object)
    comfyui_colorize_started = Signal(str)
    novelai_generation_started = Signal(str)
    novelai_generation_done = Signal(object)


class NovelAIClientAdapter:
    def __init__(self, api_token: str) -> None:
        self.api_token = api_token.strip()
        if not self.api_token:
            raise ValueError("NovelAI API token is empty")
        try:
            from novelai import NovelAI
            from novelai.types import GenerateImageParams
        except ImportError as exc:
            raise RuntimeError("novelai-sdk is not installed. Run install_support.bat, then restart RAIV.") from exc
        self._client_class = NovelAI
        self._params_class = GenerateImageParams
        self.client = NovelAI(api_key=self.api_token)

    def estimate_anlas(self, request: dict[str, object], is_opus: bool) -> int | None:
        try:
            params = self._build_params(request)
            estimate = params.calculate_anlas(is_opus=is_opus)
            return int(estimate)
        except Exception:
            return None

    def generate_images(self, request: dict[str, object]) -> list[object]:
        params = self._build_params(request)
        images = self.client.image.generate(params)
        if not images:
            raise ValueError("NovelAI did not return an image")
        return list(images)

    def image_seed(self, image: object) -> int | None:
        try:
            from novelai.utils.metadata import extract_metadata

            metadata = extract_metadata(image)
            for source in (metadata.alpha_info, metadata.png_info):
                if not isinstance(source, dict):
                    continue
                comment = source.get("Comment")
                if isinstance(comment, str):
                    try:
                        comment = json.loads(comment)
                    except json.JSONDecodeError:
                        continue
                if isinstance(comment, dict) and "seed" in comment:
                    return int(comment["seed"]) % (MAX_NOVELAI_SEED + 1)
        except Exception:
            return None
        return None

    def _build_params(self, request: dict[str, object]):
        kwargs: dict[str, object] = {
            "prompt": str(request.get("prompt", "")),
            "model": str(request.get("model", DEFAULT_NOVELAI_MODEL)),
            "size": (int(request.get("width", 832)), int(request.get("height", 1216))),
            "steps": int(request.get("steps", 28)),
            "scale": float(request.get("scale", 5.0)),
            "cfg_rescale": max(0.0, min(1.0, float(request.get("cfg_rescale", 0.0)))),
            "seed": int(request.get("seed", 0)),
            "n_samples": max(1, min(8, int(request.get("n_samples", 1)))),
            "variety_boost": bool(request.get("variety_boost", False)),
            "quality": bool(request.get("quality", True)),
            "uc_preset": str(request.get("uc_preset", "strong")),
        }
        negative_prompt = str(request.get("negative_prompt", "")).strip()
        if negative_prompt:
            kwargs["negative_prompt"] = negative_prompt
        sampler = str(request.get("sampler", "")).strip()
        if sampler:
            kwargs["sampler"] = sampler
        scheduler = str(request.get("noise_schedule", request.get("scheduler", ""))).strip()
        if scheduler:
            kwargs["noise_schedule"] = scheduler
        return self._params_class(**kwargs)


class PromptSubmitTextEdit(QTextEdit):
    submitRequested = Signal()

    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.enter_submits = True

    def keyPressEvent(self, event) -> None:
        if (
            self.enter_submits
            and event.key() in {Qt.Key_Return, Qt.Key_Enter}
            and not (event.modifiers() & Qt.ShiftModifier)
        ):
            self.submitRequested.emit()
            return
        super().keyPressEvent(event)


class VerticalResizeHandle(QFrame):
    resized = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._drag_y: int | None = None
        self._hovered = False
        self.setCursor(Qt.SizeVerCursor)
        self.setFixedHeight(18)
        self.setMouseTracking(True)
        self.setToolTip("ドラッグして高さを調整")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        center_y = self.height() // 2
        separator_color = self.palette().mid().color()
        separator_color.setAlpha(90)
        painter.setPen(QPen(separator_color, 1))
        painter.drawLine(0, center_y, self.width(), center_y)

        grip_color = self.palette().highlight().color() if self._hovered or self._drag_y is not None else self.palette().text().color()
        grip_color.setAlpha(220 if self._hovered or self._drag_y is not None else 150)
        painter.setPen(QPen(grip_color, 2, Qt.SolidLine, Qt.RoundCap))
        center_x = self.width() // 2
        for offset, half_width in ((-4, 8), (0, 11), (4, 8)):
            painter.drawLine(center_x - half_width, center_y + offset, center_x + half_width, center_y + offset)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_y = event.globalPosition().toPoint().y()
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_y is not None:
            y = event.globalPosition().toPoint().y()
            delta = y - self._drag_y
            if delta:
                self._drag_y = y
                self.resized.emit(delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._drag_y is not None:
            self._drag_y = None
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class SidePanelSplitterHandle(QSplitterHandle):
    def __init__(self, orientation: Qt.Orientation, parent: QSplitter) -> None:
        super().__init__(orientation, parent)
        self._hovered = False
        self._pressed = False
        self.setMouseTracking(True)
        self.setToolTip("ドラッグして設定ペインの幅を調整")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        center_x = self.width() // 2
        separator_color = self.palette().mid().color()
        separator_color.setAlpha(90)
        painter.setPen(QPen(separator_color, 1))
        painter.drawLine(center_x, 0, center_x, self.height())

        grip_color = self.palette().highlight().color() if self._hovered or self._pressed else self.palette().text().color()
        grip_color.setAlpha(220 if self._hovered or self._pressed else 150)
        painter.setPen(QPen(grip_color, 2, Qt.SolidLine, Qt.RoundCap))
        center_y = self.height() // 2
        for offset, half_height in ((-4, 8), (0, 11), (4, 8)):
            painter.drawLine(center_x + offset, center_y - half_height, center_x + offset, center_y + half_height)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._pressed = False
            self.update()
        super().mouseReleaseEvent(event)


class SidePanelSplitter(QSplitter):
    def createHandle(self) -> QSplitterHandle:
        return SidePanelSplitterHandle(self.orientation(), self)


class SidePanelOverlayResizeHandle(QFrame):
    resized = Signal(int)
    resizeFinished = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._drag_x: int | None = None
        self._hovered = False
        self.setCursor(Qt.SizeHorCursor)
        self.setMouseTracking(True)
        self.setToolTip("ドラッグして設定ペインの幅を調整")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        center_x = self.width() // 2
        separator_color = self.palette().mid().color()
        separator_color.setAlpha(90)
        painter.setPen(QPen(separator_color, 1))
        painter.drawLine(center_x, 0, center_x, self.height())

        grip_color = self.palette().highlight().color() if self._hovered or self._drag_x is not None else self.palette().text().color()
        grip_color.setAlpha(220 if self._hovered or self._drag_x is not None else 150)
        painter.setPen(QPen(grip_color, 2, Qt.SolidLine, Qt.RoundCap))
        center_y = self.height() // 2
        for offset, half_height in ((-4, 8), (0, 11), (4, 8)):
            painter.drawLine(center_x + offset, center_y - half_height, center_x + offset, center_y + half_height)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_x = event.globalPosition().toPoint().x()
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_x is not None:
            x = event.globalPosition().toPoint().x()
            delta = x - self._drag_x
            if delta:
                self._drag_x = x
                self.resized.emit(delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._drag_x is not None:
            self._drag_x = None
            self.update()
            self.resizeFinished.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class InactiveEditablePromptLineEdit(QLineEdit):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.prompt_active = True
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

    def set_prompt_active(self, active: bool) -> None:
        self.prompt_active = active
        self.setReadOnly(not active)
        self.opacity_effect.setOpacity(1.0 if active else 0.55)

    def mouseDoubleClickEvent(self, event) -> None:
        if not self.prompt_active:
            self.setReadOnly(False)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event) -> None:
        if not self.prompt_active:
            self.setReadOnly(True)
        super().focusOutEvent(event)


class NovelAIPromptTagRow(QWidget):
    changed = Signal()
    hoverEntered = Signal(object)
    hoverLeft = Signal(object)
    deleteRequested = Signal(object)
    moveUpRequested = Signal(object)
    moveDownRequested = Signal(object)

    def __init__(self, tag: str, active: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.tag = tag.strip()
        self.active = active
        self.setFocusPolicy(Qt.NoFocus)
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        self.indent_spacer = QWidget()
        self.indent_spacer.setFixedWidth(0)
        outer_layout.addWidget(self.indent_spacer)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("novelaiPromptTagContent")
        outer_layout.addWidget(self.content_widget, 1)
        layout = QHBoxLayout(self.content_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        self.active_button = QPushButton("👁")
        self.active_button.setFixedWidth(28)
        self.active_button.setFlat(True)
        self.apply_icon_button_style(self.active_button)
        self.active_button.setFocusPolicy(Qt.NoFocus)
        self.active_button.setToolTip("有効 / 無効")
        self.active_button.clicked.connect(self.toggle_active)
        layout.addWidget(self.active_button)
        self.handle_label = QLabel("☰")
        self.handle_label.setFixedWidth(22)
        self.handle_label.setAlignment(Qt.AlignCenter)
        self.handle_label.setToolTip("移動")
        layout.addWidget(self.handle_label)
        self.up_button = QPushButton("🔼")
        self.up_button.setFixedWidth(28)
        self.up_button.setFlat(True)
        self.apply_icon_button_style(self.up_button)
        self.up_button.setFocusPolicy(Qt.NoFocus)
        self.up_button.setToolTip("上へ")
        self.up_button.clicked.connect(lambda: self.moveUpRequested.emit(self))
        layout.addWidget(self.up_button)
        self.down_button = QPushButton("🔽")
        self.down_button.setFixedWidth(28)
        self.down_button.setFlat(True)
        self.apply_icon_button_style(self.down_button)
        self.down_button.setFocusPolicy(Qt.NoFocus)
        self.down_button.setToolTip("下へ")
        self.down_button.clicked.connect(lambda: self.moveDownRequested.emit(self))
        layout.addWidget(self.down_button)
        self.emphasis_button = QPushButton("強調")
        self.emphasis_button.setFixedWidth(58)
        self.emphasis_button.setFocusPolicy(Qt.NoFocus)
        self.emphasis_button.setToolTip("強調：全体を{ }で囲み、強度を1.05倍（重ね掛け可）")
        self.emphasis_button.clicked.connect(self.increase_emphasis)
        layout.addWidget(self.emphasis_button)
        self.suppress_button = QPushButton("抑制")
        self.suppress_button.setFixedWidth(58)
        self.suppress_button.setFocusPolicy(Qt.NoFocus)
        self.suppress_button.setToolTip("抑制：全体を[ ]で囲み、強度を1/1.05倍（重ね掛け可）")
        self.suppress_button.clicked.connect(self.increase_suppression)
        layout.addWidget(self.suppress_button)
        self.text_edit = InactiveEditablePromptLineEdit(self.tag)
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit, 1)
        self.delete_button = QPushButton("❌")
        self.delete_button.setFixedWidth(28)
        self.delete_button.setFlat(True)
        self.apply_icon_button_style(self.delete_button)
        self.delete_button.setFocusPolicy(Qt.NoFocus)
        self.delete_button.setToolTip("削除")
        self.delete_button.clicked.connect(lambda: self.deleteRequested.emit(self))
        layout.addWidget(self.delete_button)
        self.refresh()

    def set_depth(self, depth: int) -> None:
        self.indent_spacer.setFixedWidth(max(0, depth) * 20)

    def set_highlight_style(self, style: str) -> None:
        self.content_widget.setStyleSheet(
            f"#novelaiPromptTagContent {{ {style} }}" if style else ""
        )

    @staticmethod
    def apply_icon_button_style(button: QPushButton) -> None:
        button.setStyleSheet(
            "QPushButton { border: none; background: transparent; padding: 0; }"
            "QPushButton:hover { border: none; background: transparent; }"
            "QPushButton:pressed { background: palette(highlight); }"
            "QPushButton:disabled { border: none; background: transparent; }"
        )

    def enterEvent(self, event) -> None:
        self.hoverEntered.emit(self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.hoverLeft.emit(self)
        super().leaveEvent(event)

    def apply_language(self, language: str) -> None:
        labels = UI_TEXT_EN if language == "en" else UI_TEXT_JA
        self.up_button.setToolTip(labels.get("上へ", "上へ"))
        self.down_button.setToolTip(labels.get("下へ", "下へ"))
        self.active_button.setToolTip(labels.get("有効 / 無効", "有効 / 無効"))
        self.handle_label.setToolTip(labels.get("移動", "移動"))
        self.emphasis_button.setText(labels.get("強調", "強調"))
        self.emphasis_button.setToolTip(labels.get("強調：全体を{ }で囲み、強度を1.05倍（重ね掛け可）", "強調：全体を{ }で囲み、強度を1.05倍（重ね掛け可）"))
        self.suppress_button.setText(labels.get("抑制", "抑制"))
        self.suppress_button.setToolTip(labels.get("抑制：全体を[ ]で囲み、強度を1/1.05倍（重ね掛け可）", "抑制：全体を[ ]で囲み、強度を1/1.05倍（重ね掛け可）"))
        self.delete_button.setToolTip(labels.get("削除", "削除"))

    def toggle_active(self) -> None:
        self.active = not self.active
        self.refresh()
        self.changed.emit()

    def on_text_changed(self, text: str) -> None:
        self.tag = text.strip()
        self.changed.emit()

    def increase_emphasis(self) -> None:
        if self.tag.startswith("[") and self.tag.endswith("]"):
            self.tag = self.tag[1:-1].strip()
        else:
            self.tag = "{" + self.tag + "}"
        self.refresh()
        self.changed.emit()

    def increase_suppression(self) -> None:
        if self.tag.startswith("{") and self.tag.endswith("}"):
            self.tag = self.tag[1:-1].strip()
        else:
            self.tag = "[" + self.tag + "]"
        self.refresh()
        self.changed.emit()

    def refresh(self) -> None:
        self.active_button.setText("👁" if self.active else "◌")
        self.text_edit.blockSignals(True)
        self.text_edit.setText(self.tag)
        self.text_edit.blockSignals(False)
        self.text_edit.set_prompt_active(self.active)
        self.emphasis_button.setEnabled(self.active)
        self.suppress_button.setEnabled(self.active)


class NovelAIPromptFolderRow(QWidget):
    changed = Signal()
    hoverEntered = Signal(object)
    hoverLeft = Signal(object)
    toggleRequested = Signal(object)
    deleteRequested = Signal(object)
    moveUpRequested = Signal(object)
    moveDownRequested = Signal(object)

    def __init__(self, name: str, random_enabled: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.name = name.strip()
        self.random_enabled = bool(random_enabled)
        self.setFocusPolicy(Qt.NoFocus)
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        self.indent_spacer = QWidget()
        self.indent_spacer.setFixedWidth(0)
        outer_layout.addWidget(self.indent_spacer)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("novelaiPromptFolderContent")
        outer_layout.addWidget(self.content_widget, 1)
        layout = QHBoxLayout(self.content_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        self.toggle_button = QPushButton("▼")
        self.toggle_button.setFixedWidth(28)
        self.toggle_button.setFlat(True)
        NovelAIPromptTagRow.apply_icon_button_style(self.toggle_button)
        self.toggle_button.setFocusPolicy(Qt.NoFocus)
        self.toggle_button.clicked.connect(lambda: self.toggleRequested.emit(self))
        layout.addWidget(self.toggle_button)
        self.handle_label = QLabel("☰")
        self.handle_label.setFixedWidth(22)
        self.handle_label.setAlignment(Qt.AlignCenter)
        self.handle_label.setToolTip("移動")
        layout.addWidget(self.handle_label)
        self.up_button = QPushButton("🔼")
        self.up_button.setFixedWidth(28)
        self.up_button.setFlat(True)
        NovelAIPromptTagRow.apply_icon_button_style(self.up_button)
        self.up_button.setFocusPolicy(Qt.NoFocus)
        self.up_button.clicked.connect(lambda: self.moveUpRequested.emit(self))
        layout.addWidget(self.up_button)
        self.down_button = QPushButton("🔽")
        self.down_button.setFixedWidth(28)
        self.down_button.setFlat(True)
        NovelAIPromptTagRow.apply_icon_button_style(self.down_button)
        self.down_button.setFocusPolicy(Qt.NoFocus)
        self.down_button.clicked.connect(lambda: self.moveDownRequested.emit(self))
        layout.addWidget(self.down_button)
        self.random_button = QPushButton("ランダム")
        self.random_button.setFixedWidth(72)
        self.random_button.setCheckable(True)
        self.random_button.setChecked(self.random_enabled)
        self.random_button.setFocusPolicy(Qt.NoFocus)
        self.random_button.setToolTip("フォルダ内からランダムに選択")
        self.random_button.setStyleSheet(
            "QPushButton:checked { background: palette(highlight); color: palette(highlighted-text); }"
        )
        self.random_button.toggled.connect(self.on_random_toggled)
        layout.addWidget(self.random_button)
        self.name_edit = QLineEdit(self.name)
        self.name_edit.textChanged.connect(self.on_name_changed)
        layout.addWidget(self.name_edit, 1)
        self.delete_button = QPushButton("❌")
        self.delete_button.setFixedWidth(28)
        self.delete_button.setFlat(True)
        NovelAIPromptTagRow.apply_icon_button_style(self.delete_button)
        self.delete_button.setFocusPolicy(Qt.NoFocus)
        self.delete_button.clicked.connect(lambda: self.deleteRequested.emit(self))
        layout.addWidget(self.delete_button)

    def set_depth(self, depth: int) -> None:
        self.indent_spacer.setFixedWidth(max(0, depth) * 20)

    def set_highlight_style(self, style: str) -> None:
        self.content_widget.setStyleSheet(
            f"#novelaiPromptFolderContent {{ {style} }}" if style else ""
        )

    def enterEvent(self, event) -> None:
        self.hoverEntered.emit(self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.hoverLeft.emit(self)
        super().leaveEvent(event)

    def refresh_expanded(self, expanded: bool) -> None:
        self.toggle_button.setText("▼" if expanded else "▶")

    def on_name_changed(self, text: str) -> None:
        self.name = text.strip()
        self.changed.emit()

    def on_random_toggled(self, checked: bool) -> None:
        self.random_enabled = bool(checked)
        self.changed.emit()

    def apply_language(self, language: str) -> None:
        labels = UI_TEXT_EN if language == "en" else UI_TEXT_JA
        self.up_button.setToolTip(labels.get("上へ", "上へ"))
        self.down_button.setToolTip(labels.get("下へ", "下へ"))
        self.toggle_button.setToolTip(labels.get("開く / 閉じる", "開く / 閉じる"))
        self.handle_label.setToolTip(labels.get("移動", "移動"))
        self.random_button.setText(labels.get("ランダム", "ランダム"))
        self.random_button.setToolTip(labels.get("フォルダ内からランダムに選択", "フォルダ内からランダムに選択"))
        self.name_edit.setPlaceholderText(labels.get("フォルダ名", "フォルダ名"))
        self.delete_button.setToolTip(labels.get("削除", "削除"))


class NovelAIPromptTreeWidget(QTreeWidget):
    itemsMoved = Signal(object)
    dragStateChanged = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.drag_folder_row: NovelAIPromptFolderRow | None = None
        self.drag_source_row: QWidget | None = None
        self.hover_row: QWidget | None = None

    def highlight_style(self, alpha: int) -> str:
        color = self.palette().highlight().color()
        return f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {alpha});"

    def refresh_row_highlights(self) -> None:
        rows = {row for _item, row in self.item_widget_pairs()}
        for row in rows:
            if row is self.drag_source_row:
                row.set_highlight_style(self.highlight_style(110))
            elif row is self.drag_folder_row:
                row.set_highlight_style(self.highlight_style(80))
            elif not bool(self.property("dragging")) and row is self.hover_row:
                row.set_highlight_style(self.highlight_style(70))
            else:
                row.set_highlight_style("")

    def set_hover_row(self, row: object) -> None:
        if isinstance(row, (NovelAIPromptTagRow, NovelAIPromptFolderRow)):
            self.hover_row = row
            self.refresh_row_highlights()

    def clear_hover_row(self, row: object) -> None:
        if row is self.hover_row:
            self.hover_row = None
            self.refresh_row_highlights()

    def set_dragging(self, dragging: bool) -> None:
        self.setProperty("dragging", dragging)
        self.refresh_row_highlights()

    def startDrag(self, supported_actions) -> None:
        item = self.currentItem()
        row = self.itemWidget(item, 0) if item is not None else None
        self.drag_source_row = row
        self.set_dragging(True)
        self.dragStateChanged.emit(True)
        try:
            super().startDrag(supported_actions)
        finally:
            self.clear_drag_target()
            self.drag_source_row = None
            self.set_dragging(False)
            self.dragStateChanged.emit(False)

    def clear_drag_target(self) -> None:
        self.drag_folder_row = None
        self.refresh_row_highlights()

    def dragMoveEvent(self, event) -> None:
        super().dragMoveEvent(event)
        self.clear_drag_target()
        item = self.itemAt(event.position().toPoint())
        if (
            self.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.OnItem
            and item is not None
            and item.data(0, Qt.UserRole) == "folder"
        ):
            row = self.itemWidget(item, 0)
            if isinstance(row, NovelAIPromptFolderRow):
                self.drag_folder_row = row
        self.refresh_row_highlights()

    def dragLeaveEvent(self, event) -> None:
        self.clear_drag_target()
        super().dragLeaveEvent(event)

    def item_widget_pairs(self, parent: QTreeWidgetItem | None = None) -> list[tuple[QTreeWidgetItem, QWidget]]:
        pairs: list[tuple[QTreeWidgetItem, QWidget]] = []
        count = self.topLevelItemCount() if parent is None else parent.childCount()
        for index in range(count):
            item = self.topLevelItem(index) if parent is None else parent.child(index)
            widget = self.itemWidget(item, 0)
            if widget is not None:
                pairs.append((item, widget))
            pairs.extend(self.item_widget_pairs(item))
        return pairs

    def item_data_map(self) -> dict[QTreeWidgetItem, dict[str, object]]:
        data: dict[QTreeWidgetItem, dict[str, object]] = {}
        for item, widget in self.item_widget_pairs():
            if isinstance(widget, NovelAIPromptFolderRow):
                data[item] = {
                    "type": "folder",
                    "name": widget.name.strip(),
                    "expanded": item.isExpanded(),
                    "random": bool(widget.random_enabled),
                }
            elif isinstance(widget, NovelAIPromptTagRow):
                data[item] = {"type": "tag", "tag": widget.tag.strip(), "active": bool(widget.active)}
        return data

    def nodes_from_items(
        self,
        data: dict[QTreeWidgetItem, dict[str, object]],
        parent: QTreeWidgetItem | None = None,
    ) -> list[dict[str, object]]:
        nodes: list[dict[str, object]] = []
        count = self.topLevelItemCount() if parent is None else parent.childCount()
        for index in range(count):
            item = self.topLevelItem(index) if parent is None else parent.child(index)
            node = dict(data.get(item, {}))
            if not node:
                continue
            if node.get("type") == "folder":
                node["children"] = self.nodes_from_items(data, item)
            nodes.append(node)
        return nodes

    def dropEvent(self, event) -> None:
        data = self.item_data_map()
        self.clear_drag_target()
        super().dropEvent(event)
        self.itemsMoved.emit(
            {
                "items": self.nodes_from_items(data),
                "scroll_value": self.verticalScrollBar().value(),
            }
        )


class NovelAIPromptListEditor(QWidget):
    changed = Signal()
    submitRequested = Signal()

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.updating = False
        self.language = "ja"
        self.delete_folder_contents = False
        self.add_items_at_top = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        self.input_edit = QLineEdit()
        self.input_edit.returnPressed.connect(self.add_from_input)
        input_row.addWidget(self.input_edit, 1)
        self.add_button = QPushButton("追加")
        self.add_button.clicked.connect(self.add_from_input)
        input_row.addWidget(self.add_button)
        self.add_folder_button = QPushButton("フォルダ追加")
        self.add_folder_button.clicked.connect(self.add_folder)
        input_row.addWidget(self.add_folder_button)
        layout.addLayout(input_row)
        self.list_widget = NovelAIPromptTreeWidget()
        self.list_widget.setHeaderHidden(True)
        self.list_widget.setRootIsDecorated(False)
        self.list_widget.setIndentation(0)
        self.list_widget.setExpandsOnDoubleClick(False)
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setStyleSheet(
            "QTreeWidget::item:selected { background: transparent; color: palette(text); }"
            "QTreeWidget::item:hover { background: transparent; color: palette(text); }"
            "QTreeWidget::item:focus { outline: none; }"
            "QTreeWidget::branch { image: none; }"
        )
        self.list_widget.itemsMoved.connect(self.on_items_moved)
        self.list_widget.itemExpanded.connect(self.refresh_folder_item)
        self.list_widget.itemCollapsed.connect(self.refresh_folder_item)
        self.list_widget.setMinimumHeight(118)
        layout.addWidget(self.list_widget)
        self.set_text(text)

    def add_from_input(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            self.submitRequested.emit()
            return
        self.add_tag(text, True, None, insert_at_top=self.add_items_at_top)
        self.input_edit.clear()
        self.emit_changed()

    def on_items_moved(self, items: object) -> None:
        scroll_value: int | None = None
        if isinstance(items, dict):
            scroll_value = int(items.get("scroll_value", 0))
            items = items.get("items")
        if isinstance(items, list):
            self.set_items(items)
            if scroll_value is not None:
                scroll_bar = self.list_widget.verticalScrollBar()
                scroll_bar.setValue(scroll_value)
                QTimer.singleShot(0, lambda bar=scroll_bar, value=scroll_value: bar.setValue(value))
        self.emit_changed()

    def refresh_tag_item(self, item: QTreeWidgetItem, row: NovelAIPromptTagRow) -> None:
        item.setToolTip(0, "")

    def refresh_folder_item(self, item: QTreeWidgetItem) -> None:
        row = self.list_widget.itemWidget(item, 0)
        if isinstance(row, NovelAIPromptFolderRow):
            row.refresh_expanded(item.isExpanded())

    def toggle_folder(self, row: object) -> None:
        item = self.item_for_row(row)
        if item is None:
            return
        item.setExpanded(not item.isExpanded())
        self.refresh_folder_item(item)
        self.emit_changed()

    def add_folder(self) -> None:
        labels = UI_TEXT_EN if self.language == "en" else UI_TEXT_JA
        input_name = self.input_edit.text().strip()
        name = input_name or labels.get("新しいフォルダ", "新しいフォルダ")
        item = self.add_folder_item(name, None, insert_at_top=self.add_items_at_top)
        if input_name:
            self.input_edit.clear()
        self.list_widget.setCurrentItem(item)
        row = self.list_widget.itemWidget(item, 0)
        if isinstance(row, NovelAIPromptFolderRow) and not input_name:
            row.name_edit.setFocus()
            row.name_edit.selectAll()
        self.emit_changed()

    def split_prompt_text(self, text: str) -> list[str]:
        return [tag for tag, _active in self.split_prompt_items(text)]

    def split_prompt_items(self, text: str) -> list[tuple[str, bool]]:
        items: list[tuple[str, bool]] = []
        current: list[str] = []
        current_active = True
        curly_depth = 0
        square_depth = 0
        random_depth = 0
        weighted_depth = 0
        disabled_depth = 0
        text = text.replace("\n", ", ")
        index = 0
        while index < len(text):
            if current_active and disabled_depth == 0 and text.startswith(RAIV_DISABLED_PROMPT_START, index) and not "".join(current).strip():
                current_active = False
                disabled_depth = 1
                index += len(RAIV_DISABLED_PROMPT_START)
                continue
            if disabled_depth > 0 and text.startswith(RAIV_DISABLED_PROMPT_END, index):
                disabled_depth = 0
                index += len(RAIV_DISABLED_PROMPT_END)
                continue
            if disabled_depth == 0 and current_active and weighted_depth > 0 and text.startswith("::", index):
                weighted_depth = 0
                current.append("::")
                index += 2
                continue
            if disabled_depth == 0 and current_active and weighted_depth == 0 and random_depth == 0 and text.startswith("::", index):
                curly_depth = 0
                square_depth = 0
                current.append("::")
                index += 2
                continue
            weight_match = re.match(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)::", text[index:]) if disabled_depth == 0 and current_active and weighted_depth == 0 and random_depth == 0 else None
            if weight_match is not None and not "".join(current).strip():
                token = weight_match.group(0)
                weighted_depth = 1
                current.append(token)
                index += len(token)
                continue
            if disabled_depth == 0 and current_active and weighted_depth == 0 and text.startswith("||", index):
                random_depth = 0 if random_depth else 1
                current.append("||")
                index += 2
                continue
            char = text[index]
            if disabled_depth == 0 and current_active and random_depth == 0 and weighted_depth == 0 and char == "{":
                curly_depth += 1
            elif disabled_depth == 0 and current_active and random_depth == 0 and weighted_depth == 0 and char == "}" and curly_depth > 0:
                curly_depth -= 1
            elif disabled_depth == 0 and current_active and random_depth == 0 and weighted_depth == 0 and char == "[":
                square_depth += 1
            elif disabled_depth == 0 and current_active and random_depth == 0 and weighted_depth == 0 and char == "]" and square_depth > 0:
                square_depth -= 1
            if disabled_depth == 0 and char == "," and curly_depth == 0 and square_depth == 0 and random_depth == 0 and weighted_depth == 0 and index + 1 < len(text) and text[index + 1].isspace():
                part = "".join(current).strip()
                if part:
                    items.append((part, current_active))
                current = []
                current_active = True
                while index + 1 < len(text) and text[index + 1].isspace():
                    index += 1
            else:
                current.append(char)
            index += 1
        part = "".join(current).strip()
        if part:
            items.append((part, current_active))
        return items

    def add_tag(
        self,
        tag: str,
        active: bool = True,
        parent: QTreeWidgetItem | None = None,
        insert_at_top: bool = False,
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setData(0, Qt.UserRole, "tag")
        item.setFlags((item.flags() | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled)
        row = NovelAIPromptTagRow(tag, active)
        row.set_depth(self.item_depth(parent) + 1 if parent is not None else 0)
        row.apply_language(self.language)
        row.hoverEntered.connect(self.list_widget.set_hover_row)
        row.hoverLeft.connect(self.list_widget.clear_hover_row)
        row.changed.connect(self.emit_changed)
        row.deleteRequested.connect(self.delete_row)
        row.moveUpRequested.connect(self.move_row_up)
        row.moveDownRequested.connect(self.move_row_down)
        item.setSizeHint(0, row.sizeHint())
        if parent is None:
            if insert_at_top:
                self.list_widget.insertTopLevelItem(0, item)
            else:
                self.list_widget.addTopLevelItem(item)
        else:
            parent.addChild(item)
            parent.setExpanded(True)
        self.list_widget.setItemWidget(item, 0, row)
        self.refresh_tag_item(item, row)
        return item

    def add_folder_item(
        self,
        name: str,
        parent: QTreeWidgetItem | None = None,
        expanded: bool = True,
        random_enabled: bool = False,
        insert_at_top: bool = False,
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setData(0, Qt.UserRole, "folder")
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
        row = NovelAIPromptFolderRow(name, random_enabled)
        row.set_depth(self.item_depth(parent) + 1 if parent is not None else 0)
        row.apply_language(self.language)
        row.hoverEntered.connect(self.list_widget.set_hover_row)
        row.hoverLeft.connect(self.list_widget.clear_hover_row)
        row.changed.connect(self.emit_changed)
        row.toggleRequested.connect(self.toggle_folder)
        row.deleteRequested.connect(self.delete_row)
        row.moveUpRequested.connect(self.move_row_up)
        row.moveDownRequested.connect(self.move_row_down)
        item.setSizeHint(0, row.sizeHint())
        if parent is None:
            if insert_at_top:
                self.list_widget.insertTopLevelItem(0, item)
            else:
                self.list_widget.addTopLevelItem(item)
        else:
            parent.addChild(item)
            parent.setExpanded(True)
        self.list_widget.setItemWidget(item, 0, row)
        item.setExpanded(expanded)
        row.refresh_expanded(expanded)
        return item

    def item_depth(self, item: QTreeWidgetItem | None) -> int:
        depth = 0
        while item is not None and item.parent() is not None:
            depth += 1
            item = item.parent()
        return depth

    def item_for_row(self, row: object, parent: QTreeWidgetItem | None = None) -> QTreeWidgetItem | None:
        count = self.list_widget.topLevelItemCount() if parent is None else parent.childCount()
        for index in range(count):
            item = self.list_widget.topLevelItem(index) if parent is None else parent.child(index)
            if self.list_widget.itemWidget(item, 0) is row:
                return item
            found = self.item_for_row(row, item)
            if found is not None:
                return found
        return None

    def move_row_up(self, row: object) -> None:
        self.move_row(row, -1)

    def move_row_down(self, row: object) -> None:
        self.move_row(row, 1)

    def move_row(self, row: object, offset: int) -> None:
        item = self.item_for_row(row)
        if item is None:
            return
        path = self.item_path(item)
        items = self.to_items()
        container = items
        for parent_index in path[:-1]:
            children = container[parent_index].get("children")
            if not isinstance(children, list):
                return
            container = children
        index = path[-1]
        count = len(container)
        target = index + offset
        if index < 0 or target < 0 or target >= count:
            return
        container[index], container[target] = container[target], container[index]
        path[-1] = target
        self.set_items(items)
        self.list_widget.setCurrentItem(self.item_at_path(path))
        self.emit_changed()

    def item_path(self, item: QTreeWidgetItem) -> list[int]:
        path: list[int] = []
        current: QTreeWidgetItem | None = item
        while current is not None:
            parent = current.parent()
            path.append(self.list_widget.indexOfTopLevelItem(current) if parent is None else parent.indexOfChild(current))
            current = parent
        path.reverse()
        return path

    def item_at_path(self, path: list[int]) -> QTreeWidgetItem | None:
        current: QTreeWidgetItem | None = None
        for depth, index in enumerate(path):
            current = self.list_widget.topLevelItem(index) if depth == 0 else current.child(index) if current is not None else None
            if current is None:
                return None
        return current

    def delete_row(self, row: object) -> None:
        item = self.item_for_row(row)
        if item is None:
            return
        path = self.item_path(item)
        items = self.to_items()
        container = items
        for parent_index in path[:-1]:
            children = container[parent_index].get("children")
            if not isinstance(children, list):
                return
            container = children
        index = path[-1]
        removed = container.pop(index)
        children = removed.get("children")
        if not self.delete_folder_contents and isinstance(children, list):
            container[index:index] = children
        self.set_items(items)
        self.emit_changed()

    def set_text(self, text: str) -> None:
        self.set_items(self.split_prompt_nodes(text))

    def encode_folder_name(self, name: str) -> str:
        return base64.urlsafe_b64encode(name.encode("utf-8")).decode("ascii").rstrip("=")

    def decode_folder_name(self, encoded: str) -> str | None:
        try:
            padding = "=" * (-len(encoded) % 4)
            return base64.urlsafe_b64decode((encoded + padding).encode("ascii")).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None

    def split_prompt_nodes(self, text: str) -> list[dict[str, object]]:
        root: list[dict[str, object]] = []
        stack = [root]
        current: list[str] = []

        def flush() -> None:
            part = "".join(current).strip(" ,\r\n\t")
            current.clear()
            if part:
                stack[-1].extend({"type": "tag", "tag": tag, "active": active} for tag, active in self.split_prompt_items(part))

        index = 0
        while index < len(text):
            folder_marker = next(
                (
                    (marker, random_enabled)
                    for marker, random_enabled in (
                        (RAIV_PROMPT_RANDOM_FOLDER_START, True),
                        (RAIV_PROMPT_FOLDER_START, False),
                    )
                    if text.startswith(marker, index)
                ),
                None,
            )
            if folder_marker is not None:
                marker, random_enabled = folder_marker
                marker_end = text.find(">>", index + len(marker))
                if marker_end >= 0:
                    encoded = text[index + len(marker) : marker_end]
                    name = self.decode_folder_name(encoded)
                    if name is not None:
                        flush()
                        folder: dict[str, object] = {
                            "type": "folder",
                            "name": name,
                            "children": [],
                            "expanded": True,
                            "random": random_enabled,
                        }
                        stack[-1].append(folder)
                        stack.append(folder["children"])
                        index = marker_end + 2
                        continue
            if text.startswith(RAIV_PROMPT_FOLDER_END, index) and len(stack) > 1:
                flush()
                stack.pop()
                index += len(RAIV_PROMPT_FOLDER_END)
                continue
            current.append(text[index])
            index += 1
        flush()
        return root

    def active_text_from_text(self, text: str) -> str:
        return self.active_text_from_nodes(self.split_prompt_nodes(text))

    def active_text_from_nodes(self, nodes: list[dict[str, object]], separator: str = ", ") -> str:
        parts: list[str] = []
        for node in nodes:
            children = node.get("children")
            if isinstance(children, list):
                child_separator = "|" if bool(node.get("random", False)) else ", "
                child_text = self.active_text_from_nodes(children, child_separator)
                if child_text:
                    parts.append(f"||{child_text}||" if bool(node.get("random", False)) else child_text)
                continue
            tag = str(node.get("tag") or "").strip()
            if tag and bool(node.get("active", True)):
                parts.append(tag)
        return separator.join(parts)

    def set_items(self, items: list[dict[str, object]], fallback_text: str = "") -> None:
        self.updating = True
        self.list_widget.hover_row = None
        self.list_widget.drag_source_row = None
        self.list_widget.drag_folder_row = None
        self.list_widget.clear()
        self.add_items(items)
        if self.list_widget.topLevelItemCount() == 0 and fallback_text:
            self.add_items(self.split_prompt_nodes(fallback_text))
        self.updating = False

    def add_items(self, items: list[dict[str, object]], parent: QTreeWidgetItem | None = None) -> None:
        for data in items:
            if not isinstance(data, dict):
                continue
            if data.get("type") == "folder" or isinstance(data.get("children"), list):
                folder = self.add_folder_item(
                    str(data.get("name") or "").strip(),
                    parent,
                    bool(data.get("expanded", True)),
                    bool(data.get("random", False)),
                )
                children = data.get("children")
                if isinstance(children, list):
                    self.add_items(children, folder)
                folder.setExpanded(bool(data.get("expanded", True)))
                continue
            tag = str(data.get("tag") or "").strip()
            if tag:
                self.add_tag(tag, bool(data.get("active", True)), parent)

    def to_items(self) -> list[dict[str, object]]:
        return self.items_from_parent(None)

    def items_from_parent(self, parent: QTreeWidgetItem | None) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        count = self.list_widget.topLevelItemCount() if parent is None else parent.childCount()
        for index in range(count):
            item = self.list_widget.topLevelItem(index) if parent is None else parent.child(index)
            row = self.list_widget.itemWidget(item, 0)
            if isinstance(row, NovelAIPromptFolderRow):
                items.append({
                    "type": "folder",
                    "name": row.name.strip(),
                    "expanded": item.isExpanded(),
                    "random": bool(row.random_enabled),
                    "children": self.items_from_parent(item),
                })
            elif isinstance(row, NovelAIPromptTagRow) and row.tag.strip():
                items.append({"type": "tag", "tag": row.tag.strip(), "active": bool(row.active)})
        return items

    def disabled_prompt_text(self, tag: str) -> str:
        return f"{RAIV_DISABLED_PROMPT_START}{tag}{RAIV_DISABLED_PROMPT_END}"

    def to_text(self, active_only: bool = True, preserve_inactive: bool = False) -> str:
        if active_only and not preserve_inactive:
            return self.active_text_from_nodes(self.to_items())
        return self.text_from_parent(None, active_only, preserve_inactive)

    def text_from_parent(self, parent: QTreeWidgetItem | None, active_only: bool, preserve_inactive: bool) -> str:
        parts: list[str] = []
        count = self.list_widget.topLevelItemCount() if parent is None else parent.childCount()
        for index in range(count):
            item = self.list_widget.topLevelItem(index) if parent is None else parent.child(index)
            row = self.list_widget.itemWidget(item, 0)
            if isinstance(row, NovelAIPromptFolderRow):
                children = self.text_from_parent(item, active_only, preserve_inactive)
                if not active_only or preserve_inactive:
                    encoded = self.encode_folder_name(row.name.strip())
                    marker = RAIV_PROMPT_RANDOM_FOLDER_START if row.random_enabled else RAIV_PROMPT_FOLDER_START
                    parts.append(f"{marker}{encoded}>>{children}{RAIV_PROMPT_FOLDER_END}")
                elif children:
                    parts.append(children)
            elif isinstance(row, NovelAIPromptTagRow) and (row.active or not active_only):
                tag = row.tag.strip()
                if tag:
                    parts.append(tag if row.active or not preserve_inactive else self.disabled_prompt_text(tag))
        return ", ".join(parts)

    def emit_changed(self) -> None:
        if not self.updating:
            self.changed.emit()

    def apply_language(self, language: str) -> None:
        self.language = language
        labels = UI_TEXT_EN if language == "en" else UI_TEXT_JA
        self.add_button.setText(labels.get("追加", "追加"))
        self.add_folder_button.setText(labels.get("フォルダ追加", "フォルダ追加"))
        self.apply_language_to_parent(None, language)

    def apply_language_to_parent(self, parent: QTreeWidgetItem | None, language: str) -> None:
        count = self.list_widget.topLevelItemCount() if parent is None else parent.childCount()
        for index in range(count):
            item = self.list_widget.topLevelItem(index) if parent is None else parent.child(index)
            row = self.list_widget.itemWidget(item, 0)
            if isinstance(row, (NovelAIPromptTagRow, NovelAIPromptFolderRow)):
                row.apply_language(language)
            if isinstance(row, NovelAIPromptTagRow):
                self.refresh_tag_item(item, row)
            self.apply_language_to_parent(item, language)


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
        self.pixmap_cache: OrderedDict[tuple[int], QPixmap] = OrderedDict()
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
        self.display_brightness = 0.0
        self.display_contrast = 1.0
        self.display_gamma = 1.0
        self.display_sharpness = 0.0
        self.horizontal_wheel_navigation = False
        self.horizontal_wheel_inverted = False
        self.zoom = 1.0
        self.offset = QPoint(0, 0)
        self.pan_start: QPoint | None = None
        self.zoom_drag_start: QPoint | None = None
        self.fit_scale_anchor: float | None = None
        self.fit_image_size: tuple[int, int] | None = None
        self.empty_message_title = ""
        self.empty_message_detail = ""

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
        self.empty_message_title = ""
        self.empty_message_detail = ""
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

    def set_empty_message(self, title: str, detail: str) -> None:
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
        self.empty_message_title = title
        self.empty_message_detail = detail
        self.reset_view(update=False)
        self.update()

    def set_processed(self, processed: QImage | None, page_slot: int = 0) -> None:
        if page_slot == 1:
            self.raw_secondary_processed_image = processed or QImage()
            self.secondary_processed_image = self.transformed_image(
                self.adjusted_display_image(self.raw_secondary_processed_image)
            )
            self.secondary_processed_pixmap = self.pixmap_for_image(
                self.raw_secondary_processed_image,
                self.secondary_processed_image,
            )
        else:
            self.raw_processed_image = processed or QImage()
            self.processed_image = self.transformed_image(self.adjusted_display_image(self.raw_processed_image))
            self.processed_pixmap = self.pixmap_for_image(self.raw_processed_image, self.processed_image)
        self.clear_resample_cache()
        self.update()

    def set_key_bindings(self, bindings: dict[str, dict[str, dict | None]]) -> None:
        self.key_bindings = normalize_key_bindings(bindings)
        self.duplicate_mouse_bindings = duplicate_binding_signatures(self.key_bindings, "mouse")

    def transformed_image(self, image: QImage) -> QImage:
        if image.isNull():
            return QImage()
        return image

    def rebuild_display_images(self) -> None:
        self.source_image = self.transformed_image(self.adjusted_display_image(self.raw_source_image))
        self.processed_image = self.transformed_image(self.adjusted_display_image(self.raw_processed_image))
        self.secondary_source_image = self.transformed_image(self.adjusted_display_image(self.raw_secondary_source_image))
        self.secondary_processed_image = self.transformed_image(self.adjusted_display_image(self.raw_secondary_processed_image))
        self.source_pixmap = self.pixmap_for_image(self.raw_source_image, self.source_image)
        self.processed_pixmap = self.pixmap_for_image(self.raw_processed_image, self.processed_image)
        self.secondary_source_pixmap = self.pixmap_for_image(self.raw_secondary_source_image, self.secondary_source_image)
        self.secondary_processed_pixmap = self.pixmap_for_image(self.raw_secondary_processed_image, self.secondary_processed_image)

    def pixmap_for_image(self, raw_image: QImage, display_image: QImage) -> QPixmap:
        if raw_image.isNull() or display_image.isNull():
            return QPixmap()
        key = self.pixmap_cache_key(display_image)
        cached = self.pixmap_cache.get(key)
        if cached is not None:
            self.pixmap_cache.move_to_end(key)
            return cached
        pixmap = QPixmap.fromImage(display_image)
        self.pixmap_cache[key] = pixmap
        while len(self.pixmap_cache) > self.pixmap_cache_limit:
            self.pixmap_cache.popitem(last=False)
        return pixmap

    def pixmap_cache_key(self, raw_image: QImage) -> tuple[int]:
        return (int(raw_image.cacheKey()),)

    def set_pixmap_cache_limit(self, limit: int) -> None:
        self.pixmap_cache_limit = max(24, int(limit))
        while len(self.pixmap_cache) > self.pixmap_cache_limit:
            self.pixmap_cache.popitem(last=False)

    def queue_pixmap_prefetch(self, items: list[tuple[object, QImage]]) -> None:
        if self.tone_curve_enabled or self.has_display_adjustments():
            return
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

    def rotate_display(self, degrees: int, reset_view: bool = False) -> None:
        preserved_scale = self.current_scale()
        self.display_rotation = (self.display_rotation + degrees) % 360
        self.begin_interactive_resample_delay()
        if reset_view:
            self.reset_view(update=False)
        else:
            content_size = self.current_content_size()
            if not content_size.isEmpty() and self.width() > 0 and self.height() > 0:
                self.fit_scale_anchor = min(self.width() / content_size.width(), self.height() / content_size.height())
                self.fit_image_size = (content_size.width(), content_size.height())
                self.zoom = self.clamp_zoom_factor(preserved_scale / max(self.fit_scale_anchor, 0.000001))
                self.zoomChanged.emit(self.current_scale())
        self.update()

    def flip_display(self, horizontal: bool) -> None:
        if horizontal:
            self.display_flip_horizontal = not self.display_flip_horizontal
        else:
            self.display_flip_vertical = not self.display_flip_vertical
        self.begin_interactive_resample_delay()
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

    def set_display_adjustments(self, brightness: float, contrast: float, gamma: float, sharpness: float) -> None:
        self.display_brightness = max(-100.0, min(100.0, float(brightness)))
        self.display_contrast = max(0.0, min(3.0, float(contrast)))
        self.display_gamma = max(0.1, min(5.0, float(gamma)))
        self.display_sharpness = max(0.0, min(5.0, float(sharpness)))
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

    def base_content_size(self) -> QSize:
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

    def rotated_content_size(self, size: QSize) -> QSize:
        if size.isEmpty():
            return QSize()
        normalized = self.display_rotation % 360
        if normalized in (0, 180):
            return QSize(size.width(), size.height())
        if normalized in (90, 270):
            return QSize(size.height(), size.width())
        angle = math.radians(normalized)
        cos_value = abs(math.cos(angle))
        sin_value = abs(math.sin(angle))
        width = max(1, math.ceil(size.width() * cos_value + size.height() * sin_value))
        height = max(1, math.ceil(size.width() * sin_value + size.height() * cos_value))
        return QSize(width, height)

    def current_content_size(self) -> QSize:
        return self.rotated_content_size(self.base_content_size())

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

    def base_image_rect(self, rotated_target: QRect) -> QRect:
        base_size = self.base_content_size()
        if base_size.isEmpty() or rotated_target.isNull():
            return QRect()
        scale = self.current_scale()
        width = max(1, round(base_size.width() * scale))
        height = max(1, round(base_size.height() * scale))
        x = rotated_target.x() + (rotated_target.width() - width) // 2
        y = rotated_target.y() + (rotated_target.height() - height) // 2
        return QRect(x, y, width, height)

    def can_pan_view(self) -> bool:
        return abs(self.zoom - 1.0) > 0.0001

    def current_scale(self) -> float:
        content_size = self.current_content_size()
        if content_size.isEmpty():
            return 1.0
        size_key = (content_size.width(), content_size.height())
        if self.fit_scale_anchor is None or self.fit_image_size != size_key:
            self.fit_scale_anchor = min(self.width() / content_size.width(), self.height() / content_size.height())
            self.fit_image_size = size_key
        return max(0.01, min(MAX_DISPLAY_SCALE, self.fit_scale_anchor * self.zoom))

    def display_pixel_ratio(self) -> float:
        return max(1.0, float(self.devicePixelRatioF()))

    def scale_for_actual_percent(self, percent: int | float) -> float:
        return max(0.01, min(MAX_DISPLAY_SCALE, float(percent) / 100.0 / self.display_pixel_ratio()))

    def actual_percent_for_scale(self, scale: float) -> int:
        return max(1, round(scale * self.display_pixel_ratio() * 100))

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
        actual_scale = self.scale_for_actual_percent(percent)
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
        self.zoom = self.clamp_zoom_factor(self.scale_for_actual_percent(100) / self.fit_scale_anchor)
        self.zoomChanged.emit(self.current_scale())
        self.begin_interactive_resample_delay()
        self.update()

    def resampled_pixmap(self, image: QImage, target: QRect) -> QPixmap | None:
        if not self.cpu_resample_cache_enabled or image.isNull() or target.width() <= 0 or target.height() <= 0:
            return None
        if self.resample_interaction_active:
            return None
        device_pixel_ratio = self.display_pixel_ratio()
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

    def has_display_adjustments(self) -> bool:
        return (
            abs(self.display_brightness) > 0.0001
            or abs(self.display_contrast - 1.0) > 0.0001
            or abs(self.display_gamma - 1.0) > 0.0001
            or self.display_sharpness > 0.0001
        )

    def adjusted_display_image(self, image: QImage) -> QImage:
        image = self.apply_tone_curve_image(image)
        if image.isNull() or not self.has_display_adjustments():
            return image
        if np is None:
            return self.apply_sharpness_image(image) if self.display_sharpness > 0.0001 else image
        source = image.convertToFormat(QImage.Format_RGBA8888)
        size = source.sizeInBytes()
        data = bytes(source.bits()[:size])
        array = np.frombuffer(data, dtype=np.uint8).reshape((source.height(), source.width(), 4)).copy()
        rgb = array[:, :, :3].astype(np.float32)
        if abs(self.display_gamma - 1.0) > 0.0001:
            rgb = 255.0 * np.power(np.clip(rgb / 255.0, 0.0, 1.0), 1.0 / self.display_gamma)
        if abs(self.display_contrast - 1.0) > 0.0001:
            rgb = (rgb - 127.5) * self.display_contrast + 127.5
        if abs(self.display_brightness) > 0.0001:
            rgb = rgb + self.display_brightness
        array[:, :, :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
        output_data = array.tobytes()
        adjusted = QImage(output_data, source.width(), source.height(), QImage.Format_RGBA8888).copy()
        return self.apply_sharpness_image(adjusted)

    def apply_sharpness_image(self, image: QImage) -> QImage:
        if image.isNull() or self.display_sharpness <= 0.0001 or PILImage is None or ImageFilter is None:
            return image
        source = image.convertToFormat(QImage.Format_RGBA8888)
        size = source.sizeInBytes()
        data = bytes(source.bits()[:size])
        pil = PILImage.frombytes("RGBA", (source.width(), source.height()), data)
        percent = max(0, round(self.display_sharpness * 100))
        sharpened = pil.filter(ImageFilter.UnsharpMask(radius=1.0, percent=percent, threshold=2))
        output_data = sharpened.tobytes()
        return QImage(output_data, sharpened.width, sharpened.height, QImage.Format_RGBA8888).copy()

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

    def draw_empty_message(self, painter: QPainter) -> None:
        if not self.empty_message_title and not self.empty_message_detail:
            return
        rect = self.rect().adjusted(32, 32, -32, -32)
        if rect.width() <= 0 or rect.height() <= 0:
            return
        color = QColor("#ffffff" if self.background.lightness() < 128 else "#111111")
        painter.setPen(color)
        title_font = QFont(painter.font())
        title_font.setBold(True)
        title_font.setPointSize(max(12, title_font.pointSize() + 2))
        painter.setFont(title_font)
        title_bounds = painter.boundingRect(rect, Qt.AlignCenter | Qt.TextWordWrap, self.empty_message_title)
        detail_font = QFont(painter.font())
        detail_font.setBold(False)
        detail_font.setPointSize(max(9, title_font.pointSize() - 2))
        painter.setFont(detail_font)
        detail_bounds = painter.boundingRect(rect, Qt.AlignCenter | Qt.TextWordWrap, self.empty_message_detail)
        spacing = 12 if self.empty_message_title and self.empty_message_detail else 0
        total_height = title_bounds.height() + spacing + detail_bounds.height()
        top = rect.top() + max(0, (rect.height() - total_height) // 2)
        if self.empty_message_title:
            title_rect = QRect(rect.left(), top, rect.width(), title_bounds.height())
            painter.setFont(title_font)
            painter.drawText(title_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.empty_message_title)
            top += title_bounds.height() + spacing
        if self.empty_message_detail:
            detail_rect = QRect(rect.left(), top, rect.width(), detail_bounds.height())
            painter.setFont(detail_font)
            painter.drawText(detail_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.empty_message_detail)

    def paintGL(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), self.background)
        target = self.image_rect()
        if target.isNull():
            self.draw_empty_message(painter)
            painter.end()
            return
        base_target = self.base_image_rect(target)
        if base_target.isNull():
            painter.end()
            return
        painter.save()
        center = target.center()
        painter.translate(center)
        painter.rotate(self.display_rotation)
        painter.scale(-1 if self.display_flip_horizontal else 1, -1 if self.display_flip_vertical else 1)
        base_center = base_target.center()
        painter.translate(-base_center.x(), -base_center.y())
        target = base_target

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
            painter.restore()
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
        painter.restore()
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
            elif not self.can_pan_view():
                self.pan_start = None
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
            elif self.pan_start is not None and self.can_pan_view():
                pos = event.position().toPoint()
                delta = pos - self.pan_start
                self.offset += delta
                self.pan_start = pos
                self.update()
            else:
                self.pan_start = None

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
        if not self.compare_enabled or self.source_image.isNull():
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
        apply_application_color_scheme(self.config_data.ui_theme)
        self.novelai_prompt_presets = load_novelai_prompt_presets()
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
        self.signals.update_check_done.connect(self.on_update_check_done)
        self.signals.comfyui_connection_done.connect(self.on_comfyui_connection_done)
        self.signals.comfyui_colorize_done.connect(self.on_comfyui_colorize_done)
        self.signals.comfyui_colorize_started.connect(self.on_comfyui_colorize_started)
        self.signals.comfyui_setup_done.connect(self.on_comfyui_setup_done)
        self.signals.comfyui_download_progress.connect(self.on_comfyui_download_progress)
        self.signals.comfyui_download_done.connect(self.on_comfyui_download_done)
        self.signals.novelai_generation_started.connect(self.on_novelai_generation_started)
        self.signals.novelai_generation_done.connect(self.on_novelai_generation_done)

        self.image_paths: list[Path] = []
        self.image_path_set: set[Path] = set()
        self.image_path_string_set: set[str] = set()
        self.current_index = -1
        self.current_folder_path: Path | None = None
        self.dual_page_enabled = bool(self.config_data.dual_page_enabled)
        self.tone_curves: dict[str, ToneCurve] = {}
        self.current_tone_curve: ToneCurve | None = None
        self.folder_history: dict[str, dict[str, object]] = load_folder_history()
        self.folder_history_dirty = False
        self.folder_history_save_timer = QTimer(self)
        self.folder_history_save_timer.setSingleShot(True)
        self.folder_history_save_timer.timeout.connect(self.save_folder_history_now)
        self.config_save_timer = QTimer(self)
        self.config_save_timer.setSingleShot(True)
        self.config_save_timer.timeout.connect(self.persist_config)
        self.novelai_preview_timer = QTimer(self)
        self.novelai_preview_timer.setSingleShot(True)
        self.novelai_preview_timer.timeout.connect(self.update_novelai_anlas_preview)
        self.last_navigation_step = 1
        self.folder_list_loading = False
        self.deferred_page_steps = 0
        self.original_cache: OrderedDict[Path, QImage] = OrderedDict()
        self.image_height_cache: OrderedDict[Path, int] = OrderedDict()
        self.processed_cache: OrderedDict[tuple, QImage] = OrderedDict()
        self.processing_paths: set[Path] = set()
        self.processing_task_keys: dict[Path, tuple] = {}
        self.queued_tasks: dict[Path, UpscaleTask] = {}
        self.work_queue: queue.Queue[Path | None] = queue.Queue()
        self.prefetch_io_queue: queue.PriorityQueue[tuple[int, int, int, str, object, str, str]] = queue.PriorityQueue()
        self.prefetch_io_sequence = 0
        self.prefetch_io_lock = threading.Lock()
        self.thumbnail_queue: queue.PriorityQueue[tuple[int, int, int, int, str, int, float]] = queue.PriorityQueue()
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
        self.thumbnail_prefetch_timer = QTimer(self)
        self.thumbnail_prefetch_timer.setSingleShot(True)
        self.thumbnail_prefetch_timer.timeout.connect(self.schedule_thumbnail_prefetch)
        self.thumbnail_resize_refresh_timer = QTimer(self)
        self.thumbnail_resize_refresh_timer.setSingleShot(True)
        self.thumbnail_resize_refresh_timer.timeout.connect(self.refresh_thumbnail_icons_for_size)
        self.hdr_tonemap_apply_timer = QTimer(self)
        self.hdr_tonemap_apply_timer.setSingleShot(True)
        self.hdr_tonemap_apply_timer.timeout.connect(self.apply_hdr_tonemap_brightness)
        self.display_adjustment_apply_timer = QTimer(self)
        self.display_adjustment_apply_timer.setSingleShot(True)
        self.display_adjustment_apply_timer.timeout.connect(self.apply_display_adjustments)
        self.profile_stats: dict[str, dict[str, float]] = {}
        self.profile_update_timer = QTimer(self)
        self.profile_update_timer.setSingleShot(True)
        self.profile_update_timer.timeout.connect(self.update_profile_panel)
        self.update_check_running = False
        self.update_check_result: dict[str, str] | None = None
        self.comfyui_connection_running = False
        self.comfyui_colorize_running = False
        self.comfyui_setup_running = False
        self.comfyui_download_running = False
        self.colorize_processing_paths: set[Path] = set()
        self.colorize_queued_paths: set[Path] = set()
        self.colorize_queue: queue.Queue[dict[str, object] | None] = queue.Queue()
        self.colorize_plan: list[Path] = []
        self.colorize_done_paths: set[Path] = set()
        self.colorized_session_paths: dict[Path, Path] = {}
        self.novelai_generation_running = False
        self.novelai_continuous_generation_enabled = False
        self.novelai_continuous_generation_stopping = False
        self.novelai_continuous_delay_timer = QTimer(self)
        self.novelai_continuous_delay_timer.setSingleShot(True)
        self.novelai_continuous_delay_timer.timeout.connect(self.run_next_novelai_continuous_generation)
        self.novelai_generate_click_pending = False
        self.ignore_next_novelai_generate_release = False
        self.novelai_queue: queue.Queue[dict[str, object] | None] = queue.Queue()
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
        self.prefetching_processed_keys: set[tuple] = set()
        self.prefetch_viewer_plan: list[Path] = []
        self.prefetch_engine_plan: list[Path] = []
        self.prefetch_engine_done_paths: set[Path] = set()
        self.pixmap_prefetch_log_accum = 0
        self.side_panel_visible_before_fullscreen = True
        self.side_panel_width = int(self.config_data.side_panel_width)
        self.fullscreen_cursor_hidden = False
        self.fullscreen_cursor_hide_suspended = False
        self.side_panel_overlay = False
        self.borderless_fullscreen = False
        self.before_fullscreen_geometry = QRect()
        self.before_fullscreen_native_geometry = QRect()
        self.before_fullscreen_flags = self.windowFlags()
        self.before_fullscreen_state = Qt.WindowNoState
        self.before_fullscreen_native_style: int | None = None
        self.fullscreen_enforce_pending = False
        self.overlay_resizing = False
        self.overlay_modal_guard = False
        self.novelai_prompt_drag_active = False
        self.novelai_filename_tooltip_active = False
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
        self.splitter = SidePanelSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(18)
        if self.config_data.side_panel_on_left:
            self.splitter.addWidget(self.side_panel)
            self.splitter.addWidget(self.viewer_host)
            self.splitter.setStretchFactor(0, 0)
            self.splitter.setStretchFactor(1, 1)
        else:
            self.splitter.addWidget(self.viewer_host)
            self.splitter.addWidget(self.side_panel)
            self.splitter.setStretchFactor(0, 1)
            self.splitter.setStretchFactor(1, 0)
        self.splitter.splitterMoved.connect(self.on_splitter_moved)
        self.setCentralWidget(self.splitter)

        self.side_panel_overlay_resize_handle = SidePanelOverlayResizeHandle(self)
        self.side_panel_overlay_resize_handle.resized.connect(self.resize_overlay_side_panel)
        self.side_panel_overlay_resize_handle.resizeFinished.connect(self.finish_overlay_side_panel_resize)
        self.side_panel_overlay_resize_handle.hide()

        self._restore_geometry()
        self._apply_settings_to_viewer()
        self.initializing = False
        self.restore_last_image_if_needed()

        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()
        self.prefetch_io_workers = [
            threading.Thread(target=self._prefetch_io_worker_loop, daemon=True)
            for _index in range(2)
        ]
        for worker in self.prefetch_io_workers:
            worker.start()
        self.colorize_worker = threading.Thread(target=self._colorize_worker_loop, daemon=True)
        self.colorize_worker.start()
        self.novelai_worker = threading.Thread(target=self._novelai_worker_loop, daemon=True)
        self.novelai_worker.start()
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
        self.side_panel_side_button = QPushButton()
        self.side_panel_side_button.clicked.connect(self.toggle_side_panel_side)
        header.addWidget(self.side_panel_side_button)
        layout.addLayout(header)
        self.pin_button.setText("固定中" if self.config_data.side_panel_pinned else "自動表示")
        self.update_side_panel_side_button()

        tabs = QTabWidget()
        self.tabs = tabs
        realcugan_tab = QScrollArea()
        general_tab = QScrollArea()
        image_adjust_tab = QScrollArea()
        colorize_tab = QScrollArea()
        novelai_tab = QScrollArea()
        other_tab = QScrollArea()
        keyconfig_tab = QScrollArea()
        realcugan_tab.setWidgetResizable(True)
        general_tab.setWidgetResizable(True)
        image_adjust_tab.setWidgetResizable(True)
        colorize_tab.setWidgetResizable(True)
        novelai_tab.setWidgetResizable(True)
        other_tab.setWidgetResizable(True)
        keyconfig_tab.setWidgetResizable(True)
        tabs.addTab(realcugan_tab, "エンジン設定")
        tabs.addTab(general_tab, "全般")
        tabs.addTab(image_adjust_tab, "画像調整")
        tabs.addTab(colorize_tab, "AI彩色(β)")
        tabs.addTab(novelai_tab, "NovelAI生成")
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
        self.engine_form = form
        self.realesrgan_model_combo = QComboBox()
        self.realesrgan_model_combo.currentIndexChanged.connect(self.on_engine_model_changed)
        form.addRow("モデル", self.realesrgan_model_combo)
        self.scale_combo = QComboBox()
        self.scale_combo.currentTextChanged.connect(self.on_processing_settings_changed)
        form.addRow("倍率", self.scale_combo)

        self.denoise_combo = QComboBox()
        self.denoise_combo.addItems(["-1", "0", "1", "2", "3"])
        self.denoise_combo.setCurrentText(str(self.config_data.denoise))
        self.denoise_combo.currentTextChanged.connect(self.on_processing_settings_changed)
        form.addRow("ノイズ", self.denoise_combo)
        self.tile_combo = QComboBox()
        self.tile_combo.setEditable(True)
        self.tile_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.tile_combo.addItems(["0", "32", "64", "96", "128", "160", "192", "256", "320", "384", "512", "640", "768", "1024"])
        self.tile_combo.lineEdit().setValidator(QIntValidator(0, 99999, self.tile_combo))
        self.tile_combo.setCurrentText(str(max(0, int(self.config_data.tile))))
        self.tile_combo.currentTextChanged.connect(self.on_processing_settings_changed)
        form.addRow("tile", self.tile_combo)
        realcugan_layout.addLayout(form)
        self.denoise_help = self.help_label("ノイズ: -1 はノイズ除去なし。0/1/2/3 は数値が大きいほど強く除去します。")
        realcugan_layout.addWidget(self.denoise_help)
        self.realesrgan_model_help = self.help_label("Real-ESRGANはノイズ値を使わず、モデルで画風や復元傾向を選びます。")
        realcugan_layout.addWidget(self.realesrgan_model_help)
        self.realesrgan_model_detail = self.help_label(
            "realesr-animevideov3: アニメ/イラスト向けの軽量標準モデル。"
            " realesrgan-x4plus: 写真や一般画像向け。"
            " realesrgan-x4plus-anime: アニメ/イラスト向けのx4plus派生モデル。"
            " realesr-animevideov3は2倍/3倍/4倍、x4plus系は4倍に対応します。"
        )
        realcugan_layout.addWidget(self.realesrgan_model_detail)

        self.gigapixel_denoise_spin = QSpinBox()
        self.gigapixel_denoise_spin.setRange(0, 100)
        self.gigapixel_denoise_spin.setSpecialValueText("0 (オフ)")
        self.gigapixel_denoise_spin.setValue(self.config_data.gigapixel_denoise)
        self.gigapixel_denoise_spin.valueChanged.connect(self.on_processing_settings_changed)
        form.addRow("ノイズ", self.gigapixel_denoise_spin)
        self.gigapixel_sharpen_spin = QSpinBox()
        self.gigapixel_sharpen_spin.setRange(0, 100)
        self.gigapixel_sharpen_spin.setSpecialValueText("0 (オフ)")
        self.gigapixel_sharpen_spin.setValue(self.config_data.gigapixel_sharpen)
        self.gigapixel_sharpen_spin.valueChanged.connect(self.on_processing_settings_changed)
        form.addRow("Sharpen", self.gigapixel_sharpen_spin)
        self.gigapixel_compression_spin = QSpinBox()
        self.gigapixel_compression_spin.setRange(0, 100)
        self.gigapixel_compression_spin.setSpecialValueText("0 (オフ)")
        self.gigapixel_compression_spin.setValue(self.config_data.gigapixel_compression)
        self.gigapixel_compression_spin.valueChanged.connect(self.on_processing_settings_changed)
        form.addRow("Fix Compression", self.gigapixel_compression_spin)
        self.gigapixel_face_recovery_spin = QSpinBox()
        self.gigapixel_face_recovery_spin.setRange(0, 100)
        self.gigapixel_face_recovery_spin.setSpecialValueText("0 (オフ)")
        self.gigapixel_face_recovery_spin.setValue(self.config_data.gigapixel_face_recovery)
        self.gigapixel_face_recovery_spin.valueChanged.connect(self.on_processing_settings_changed)
        form.addRow("Face Recovery", self.gigapixel_face_recovery_spin)
        self.gigapixel_help = self.help_label("Gigapixel AI CLIはProライセンスが必要です。各補正は0で無効、1～100で強度を指定します。")
        realcugan_layout.addWidget(self.gigapixel_help)

        self.tile_help = self.help_label("tile: 0 は自動。内蔵GPUなどでメモリ不足になる場合は 128 や 256 など小さめの値を指定すると安定しやすくなりますが、遅くなることがあります。")
        realcugan_layout.addWidget(self.tile_help)
        realcugan_layout.addWidget(self.separator())

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
        self.auto_scale_check = QCheckBox("倍率を自動で決定する")
        self.auto_scale_check.setChecked(self.config_data.auto_realcugan_scale)
        self.auto_scale_check.stateChanged.connect(self.on_processing_settings_changed)
        form3.addRow(self.auto_scale_check)
        form3.addRow(self.help_label("画像ごとに、現在のエンジンとモデルで選択可能な倍率から、縦サイズ閾値へ届く最小倍率を選びます。届かない場合は最大倍率を使います。"))
        realcugan_layout.addLayout(form3)

        self.save_scale_check = QCheckBox("拡大結果を倍率フォルダに保存")
        self.save_scale_check.setChecked(self.config_data.save_upscaled_to_scale_folder)
        self.save_scale_check.stateChanged.connect(self.on_processing_settings_changed)
        self.use_scale_cache_check = QCheckBox("倍率フォルダがあれば表示に使う")
        self.use_scale_cache_check.setChecked(self.config_data.use_scale_folder_cache)
        self.use_scale_cache_check.stateChanged.connect(self.on_processing_settings_changed)
        realcugan_layout.addWidget(self.save_scale_check)
        realcugan_layout.addWidget(self.use_scale_cache_check)
        realcugan_layout.addWidget(self.help_label("現在選択中のエンジン、モデル、倍率に完全一致する倍率フォルダだけを表示に使います。別エンジンや別倍率の結果にはフォールバックしません。"))
        self.archive_help = self.help_label("アーカイブ表示中は保存先フォルダがないため、倍率フォルダ保存と倍率フォルダ読み込みは無効です。")
        self.archive_help.hide()
        realcugan_layout.addWidget(self.archive_help)
        rerun_button = QPushButton("再実行")
        rerun_button.clicked.connect(self.force_reprocess)
        realcugan_layout.addWidget(rerun_button)
        realcugan_layout.addWidget(self.separator())

        realcugan_layout.addWidget(QLabel("コマンドテンプレート"))
        self.command_edit = QLineEdit(self.config_data.command_template)
        self.command_edit.editingFinished.connect(self.on_command_template_changed)
        realcugan_layout.addWidget(self.command_edit)
        exe_button = QPushButton("エンジンexeを選択")
        exe_button.clicked.connect(self.choose_engine_exe)
        realcugan_layout.addWidget(exe_button)
        realcugan_layout.addWidget(self.help_label("使用できる置換: {input} {output} {output_dir} {scale} {denoise} {tile} {model} {sharpen} {compression} {face_recovery}"))
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
        self.refit_rotation_check = QCheckBox("回転時に表示全体をフィットし直す")
        self.refit_rotation_check.setChecked(self.config_data.refit_view_on_rotation)
        self.refit_rotation_check.stateChanged.connect(self.on_general_settings_changed)
        general_layout.addWidget(self.refit_rotation_check)
        general_layout.addWidget(self.help_label("オフの時は回転してもズーム倍率を維持します。オンにすると、回転後の縦横サイズに合わせて画像全体が収まる倍率へ調整します。"))
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
        self.colorize_progress_bar = QProgressBar()
        self.upscale_progress_bar = QProgressBar()
        self.processed_prefetch_bar = QProgressBar()
        self.pixmap_prefetch_bar = QProgressBar()
        for bar in (self.original_prefetch_bar, self.colorize_progress_bar, self.upscale_progress_bar, self.processed_prefetch_bar, self.pixmap_prefetch_bar):
            bar.setRange(0, 1)
            bar.setValue(0)
            bar.setTextVisible(True)
        progress_layout.addRow("拡大前メモリ読込", self.original_prefetch_bar)
        progress_layout.addRow("AI彩色画像生成", self.colorize_progress_bar)
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
        display_controls_label = QLabel("表示操作")
        display_controls_label.setObjectName("displayControlsLabel")
        image_adjust_layout.addWidget(display_controls_label)
        display_controls_layout = QGridLayout()
        rotate_left_button = QPushButton("左回転")
        rotate_left_button.clicked.connect(lambda: self.viewer.rotate_display(-90, reset_view=self.config_data.refit_view_on_rotation))
        rotate_right_button = QPushButton("右回転")
        rotate_right_button.clicked.connect(lambda: self.viewer.rotate_display(90, reset_view=self.config_data.refit_view_on_rotation))
        flip_horizontal_button = QPushButton("左右反転")
        flip_horizontal_button.clicked.connect(lambda: self.viewer.flip_display(True))
        flip_vertical_button = QPushButton("上下反転")
        flip_vertical_button.clicked.connect(lambda: self.viewer.flip_display(False))
        reset_display_button = QPushButton("表示リセット")
        reset_display_button.clicked.connect(self.viewer.reset_display_state)
        display_controls_layout.addWidget(rotate_left_button, 0, 0)
        display_controls_layout.addWidget(rotate_right_button, 0, 1)
        display_controls_layout.addWidget(flip_horizontal_button, 1, 0)
        display_controls_layout.addWidget(flip_vertical_button, 1, 1)
        display_controls_layout.addWidget(reset_display_button, 2, 0, 1, 2)
        image_adjust_layout.addLayout(display_controls_layout)
        image_adjust_layout.addWidget(self.separator())
        basic_adjust_label = QLabel("基本表示調整")
        basic_adjust_label.setObjectName("basicDisplayAdjustmentLabel")
        image_adjust_layout.addWidget(basic_adjust_label)
        basic_adjust_grid = QGridLayout()
        basic_adjust_grid.setColumnStretch(2, 1)
        self.display_brightness_slider = QSlider(Qt.Horizontal)
        self.display_brightness_slider.setRange(-100, 100)
        self.display_brightness_slider.setSingleStep(1)
        self.display_brightness_slider.setPageStep(10)
        self.display_brightness_slider.setValue(round(float(self.config_data.display_brightness)))
        self.display_brightness_slider.valueChanged.connect(self.on_display_adjustments_changed)
        self.display_brightness_value_label = QLabel()
        brightness_reset_button = QPushButton("リセット")
        brightness_reset_button.clicked.connect(lambda: self.reset_display_adjustment("brightness"))
        basic_adjust_grid.addWidget(QLabel("明るさ"), 0, 0)
        basic_adjust_grid.addWidget(self.display_brightness_value_label, 0, 1)
        basic_adjust_grid.addWidget(self.display_brightness_slider, 0, 2)
        basic_adjust_grid.addWidget(brightness_reset_button, 0, 3)

        self.display_contrast_slider = QSlider(Qt.Horizontal)
        self.display_contrast_slider.setRange(0, 300)
        self.display_contrast_slider.setSingleStep(5)
        self.display_contrast_slider.setPageStep(10)
        self.display_contrast_slider.setValue(round(float(self.config_data.display_contrast) * 100))
        self.display_contrast_slider.valueChanged.connect(self.on_display_adjustments_changed)
        self.display_contrast_value_label = QLabel()
        contrast_reset_button = QPushButton("リセット")
        contrast_reset_button.clicked.connect(lambda: self.reset_display_adjustment("contrast"))
        basic_adjust_grid.addWidget(QLabel("コントラスト"), 1, 0)
        basic_adjust_grid.addWidget(self.display_contrast_value_label, 1, 1)
        basic_adjust_grid.addWidget(self.display_contrast_slider, 1, 2)
        basic_adjust_grid.addWidget(contrast_reset_button, 1, 3)

        self.display_gamma_slider = QSlider(Qt.Horizontal)
        self.display_gamma_slider.setRange(10, 500)
        self.display_gamma_slider.setSingleStep(5)
        self.display_gamma_slider.setPageStep(10)
        self.display_gamma_slider.setValue(round(float(self.config_data.display_gamma) * 100))
        self.display_gamma_slider.valueChanged.connect(self.on_display_adjustments_changed)
        self.display_gamma_value_label = QLabel()
        gamma_reset_button = QPushButton("リセット")
        gamma_reset_button.clicked.connect(lambda: self.reset_display_adjustment("gamma"))
        basic_adjust_grid.addWidget(QLabel("ガンマ"), 2, 0)
        basic_adjust_grid.addWidget(self.display_gamma_value_label, 2, 1)
        basic_adjust_grid.addWidget(self.display_gamma_slider, 2, 2)
        basic_adjust_grid.addWidget(gamma_reset_button, 2, 3)

        self.display_sharpness_slider = QSlider(Qt.Horizontal)
        self.display_sharpness_slider.setRange(0, 50)
        self.display_sharpness_slider.setSingleStep(1)
        self.display_sharpness_slider.setPageStep(5)
        self.display_sharpness_slider.setValue(round(float(self.config_data.display_sharpness) * 10))
        self.display_sharpness_slider.valueChanged.connect(self.on_display_adjustments_changed)
        self.display_sharpness_value_label = QLabel()
        sharpness_reset_button = QPushButton("リセット")
        sharpness_reset_button.clicked.connect(lambda: self.reset_display_adjustment("sharpness"))
        basic_adjust_grid.addWidget(QLabel("シャープネス"), 3, 0)
        basic_adjust_grid.addWidget(self.display_sharpness_value_label, 3, 1)
        basic_adjust_grid.addWidget(self.display_sharpness_slider, 3, 2)
        basic_adjust_grid.addWidget(sharpness_reset_button, 3, 3)
        image_adjust_layout.addLayout(basic_adjust_grid)
        self.update_display_adjustment_labels()
        image_adjust_layout.addWidget(self.help_label("表示上だけの非破壊調整です。元ファイルや拡大処理済みファイルは変更しません。"))
        image_adjust_layout.addWidget(self.separator())
        hdr_tonemap_label = QLabel("HDR互換表示")
        hdr_tonemap_label.setObjectName("hdrCompatibleDisplayLabel")
        image_adjust_layout.addWidget(hdr_tonemap_label)
        self.hdr_tonemap_brightness_label = QLabel()
        image_adjust_layout.addWidget(self.hdr_tonemap_brightness_label)
        self.hdr_tonemap_brightness_slider = QSlider(Qt.Horizontal)
        self.hdr_tonemap_brightness_slider.setRange(50, 150)
        self.hdr_tonemap_brightness_slider.setSingleStep(5)
        self.hdr_tonemap_brightness_slider.setPageStep(10)
        self.hdr_tonemap_brightness_slider.setValue(round(float(self.config_data.hdr_tonemap_brightness) * 100))
        self.hdr_tonemap_brightness_slider.valueChanged.connect(self.on_hdr_tonemap_brightness_changed)
        hdr_tonemap_row = QHBoxLayout()
        hdr_tonemap_row.addWidget(self.hdr_tonemap_brightness_slider, 1)
        self.hdr_tonemap_reset_button = QPushButton("100%に戻す")
        self.hdr_tonemap_reset_button.clicked.connect(self.reset_hdr_tonemap_brightness)
        hdr_tonemap_row.addWidget(self.hdr_tonemap_reset_button)
        image_adjust_layout.addLayout(hdr_tonemap_row)
        image_adjust_layout.addWidget(self.help_label("HDR画像を表示している時だけ有効です。100%を基準に、SDR互換表示へ変換する時の明るさを調整します。"))
        image_adjust_layout.addWidget(self.separator())
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

        colorize_content = QWidget()
        colorize_layout = QVBoxLayout(colorize_content)
        colorize_layout.addWidget(self.help_label("ComfyUIを使用し、表示画像を加工する開発中機能です。主にモノクロ画像のAI彩色を想定しています。IN/OUT制御は実装済みのため、モデルやプロンプトを調整すればユーザー側で目的に近づけられますが、開発者側では画質調整はまだ十分ではありません。"))
        comfy_form = QFormLayout()
        self.comfyui_api_edit = QLineEdit(self.config_data.comfyui_api_url or DEFAULT_COMFYUI_API_URL)
        self.comfyui_api_edit.editingFinished.connect(self.on_comfyui_settings_changed)
        comfy_form.addRow("ComfyUI API URL", self.comfyui_api_edit)
        self.comfyui_base_dir_edit = QLineEdit(self.config_data.comfyui_base_dir)
        self.comfyui_base_dir_edit.editingFinished.connect(self.on_comfyui_settings_changed)
        comfy_form.addRow("ComfyUI base directory", self.comfyui_base_dir_edit)
        self.comfyui_workflow_edit = QLineEdit(self.config_data.comfyui_workflow_path)
        self.comfyui_workflow_edit.editingFinished.connect(self.on_comfyui_workflow_changed)
        workflow_buttons = QHBoxLayout()
        browse_workflow_button = QPushButton("参照")
        browse_workflow_button.clicked.connect(self.choose_comfyui_workflow)
        detect_nodes_button = QPushButton("ノード検出")
        detect_nodes_button.clicked.connect(self.detect_comfyui_nodes)
        workflow_buttons.addWidget(browse_workflow_button)
        workflow_buttons.addWidget(detect_nodes_button)
        workflow_row = QVBoxLayout()
        workflow_row.addWidget(self.comfyui_workflow_edit)
        workflow_row.addLayout(workflow_buttons)
        comfy_form.addRow("workflow JSON", workflow_row)
        self.comfyui_input_combo = QComboBox()
        self.comfyui_input_combo.currentIndexChanged.connect(self.on_comfyui_settings_changed)
        comfy_form.addRow("入力画像ノード", self.comfyui_input_combo)
        self.comfyui_output_combo = QComboBox()
        self.comfyui_output_combo.currentIndexChanged.connect(self.on_comfyui_settings_changed)
        comfy_form.addRow("出力画像ノード", self.comfyui_output_combo)
        colorize_layout.addLayout(comfy_form)
        colorize_layout.addWidget(self.help_label("ComfyUIを起動しておき、初期設定を実行してください。推奨モデルがある場合はRAIV用workflowを自動生成します。"))
        colorize_setup_buttons = QHBoxLayout()
        self.comfyui_check_button = QPushButton("接続確認")
        self.comfyui_check_button.clicked.connect(self.check_comfyui_connection)
        self.comfyui_download_button = QPushButton("推奨モデル/ControlNetをダウンロード")
        self.comfyui_download_button.clicked.connect(self.download_comfyui_recommended_model)
        self.comfyui_setup_button = QPushButton("初期設定")
        self.comfyui_setup_button.clicked.connect(self.setup_comfyui_defaults)
        colorize_setup_buttons.addWidget(self.comfyui_check_button)
        colorize_setup_buttons.addWidget(self.comfyui_download_button)
        colorize_setup_buttons.addWidget(self.comfyui_setup_button)
        colorize_setup_buttons.addStretch(1)
        colorize_layout.addLayout(colorize_setup_buttons)
        colorize_prefetch_form = QFormLayout()
        self.colorize_prefetch_check = QCheckBox("AI彩色を先行処理する")
        self.colorize_prefetch_check.setChecked(self.config_data.colorize_prefetch_enabled)
        self.colorize_prefetch_check.stateChanged.connect(self.on_colorize_prefetch_settings_changed)
        self.save_colorized_check = QCheckBox("彩色結果をフォルダに保存")
        self.save_colorized_check.setChecked(self.config_data.save_colorized_to_folder)
        self.save_colorized_check.stateChanged.connect(self.on_comfyui_settings_changed)
        self.use_colorized_cache_check = QCheckBox("彩色フォルダがあれば表示に使う")
        self.use_colorized_cache_check.setChecked(self.config_data.use_colorized_folder_cache)
        self.use_colorized_cache_check.stateChanged.connect(self.on_colorized_cache_settings_changed)
        self.colorize_prefetch_spin = QSpinBox()
        self.colorize_prefetch_spin.setRange(0, 99999)
        self.colorize_prefetch_spin.setValue(self.config_data.colorize_prefetch_count)
        self.colorize_prefetch_spin.valueChanged.connect(self.on_colorize_prefetch_settings_changed)
        colorize_prefetch_form.addRow(self.colorize_prefetch_check)
        colorize_prefetch_form.addRow(self.save_colorized_check)
        colorize_prefetch_form.addRow(self.use_colorized_cache_check)
        colorize_prefetch_form.addRow("AI彩色先読み", self.colorize_prefetch_spin)
        colorize_layout.addLayout(colorize_prefetch_form)
        colorize_layout.addWidget(self.help_label("彩色済み画像がないページだけComfyUIへ送ります。既存の彩色結果は上書きせず、手動の「現在画像を彩色」だけ上書きします。"))
        colorize_adjust_form = QFormLayout()
        self.colorize_denoise_spin = QDoubleSpinBox()
        self.colorize_denoise_spin.setRange(0.0, 1.0)
        self.colorize_denoise_spin.setSingleStep(0.01)
        self.colorize_denoise_spin.setDecimals(2)
        self.colorize_denoise_spin.setValue(float(self.config_data.colorize_denoise))
        self.colorize_denoise_spin.valueChanged.connect(self.on_comfyui_settings_changed)
        colorize_adjust_form.addRow("彩色強度", self.colorize_denoise_spin)
        self.colorize_controlnet_strength_spin = QDoubleSpinBox()
        self.colorize_controlnet_strength_spin.setRange(0.0, 2.0)
        self.colorize_controlnet_strength_spin.setSingleStep(0.05)
        self.colorize_controlnet_strength_spin.setDecimals(2)
        self.colorize_controlnet_strength_spin.setValue(float(self.config_data.colorize_controlnet_strength))
        self.colorize_controlnet_strength_spin.valueChanged.connect(self.on_comfyui_settings_changed)
        colorize_adjust_form.addRow("線画保持", self.colorize_controlnet_strength_spin)
        self.colorize_controlnet_end_spin = QDoubleSpinBox()
        self.colorize_controlnet_end_spin.setRange(0.0, 1.0)
        self.colorize_controlnet_end_spin.setSingleStep(0.05)
        self.colorize_controlnet_end_spin.setDecimals(2)
        self.colorize_controlnet_end_spin.setValue(float(self.config_data.colorize_controlnet_end))
        self.colorize_controlnet_end_spin.valueChanged.connect(self.on_comfyui_settings_changed)
        colorize_adjust_form.addRow("線画保持終了", self.colorize_controlnet_end_spin)
        self.colorize_saturation_spin = QDoubleSpinBox()
        self.colorize_saturation_spin.setRange(0.0, 3.0)
        self.colorize_saturation_spin.setSingleStep(0.05)
        self.colorize_saturation_spin.setDecimals(2)
        self.colorize_saturation_spin.setValue(float(self.config_data.colorize_saturation_boost))
        self.colorize_saturation_spin.valueChanged.connect(self.on_comfyui_settings_changed)
        colorize_adjust_form.addRow("彩度補正", self.colorize_saturation_spin)
        self.colorize_luminance_spin = QDoubleSpinBox()
        self.colorize_luminance_spin.setRange(0.0, 1.0)
        self.colorize_luminance_spin.setSingleStep(0.05)
        self.colorize_luminance_spin.setDecimals(2)
        self.colorize_luminance_spin.setValue(float(self.config_data.colorize_luminance_preserve))
        self.colorize_luminance_spin.valueChanged.connect(self.on_comfyui_settings_changed)
        colorize_adjust_form.addRow("輝度保持", self.colorize_luminance_spin)
        colorize_layout.addLayout(colorize_adjust_form)
        colorize_layout.addWidget(self.help_label("彩色強度を上げると色は乗りやすくなりますが形が変わりやすくなります。線画保持を上げると崩れにくくなりますが色が弱くなることがあります。輝度保持を下げるとAI生成側の雰囲気が残り、上げると元画像の明暗と文字が残りやすくなります。"))
        colorize_layout.addWidget(QLabel("Positive prompt"))
        self.colorize_positive_edit = QTextEdit(self.config_data.colorize_positive_prompt or DEFAULT_COLORIZE_POSITIVE_PROMPT)
        self.colorize_positive_edit.setFixedHeight(70)
        self.colorize_positive_edit.textChanged.connect(self.on_comfyui_settings_changed)
        colorize_layout.addWidget(self.colorize_positive_edit)
        colorize_layout.addWidget(QLabel("Negative prompt"))
        self.colorize_negative_edit = QTextEdit(self.config_data.colorize_negative_prompt or DEFAULT_COLORIZE_NEGATIVE_PROMPT)
        self.colorize_negative_edit.setFixedHeight(70)
        self.colorize_negative_edit.textChanged.connect(self.on_comfyui_settings_changed)
        colorize_layout.addWidget(self.colorize_negative_edit)
        colorize_run_buttons = QHBoxLayout()
        self.comfyui_colorize_button = QPushButton("現在画像を彩色")
        self.comfyui_colorize_button.clicked.connect(self.colorize_current_image_with_comfyui)
        colorize_run_buttons.addWidget(self.comfyui_colorize_button)
        colorize_run_buttons.addStretch(1)
        colorize_layout.addLayout(colorize_run_buttons)
        self.comfyui_status_label = self.help_label("")
        self.comfyui_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        colorize_layout.addWidget(self.comfyui_status_label)
        colorize_layout.addStretch(1)
        colorize_tab.setWidget(colorize_content)
        self.detect_comfyui_nodes(update_status=False)

        novelai_tab.setWidget(self.build_novelai_tab_content())

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
        self.theme_combo = QComboBox()
        for key, label in THEME_OPTIONS:
            self.theme_combo.addItem(self.tr_ui(label), key)
        self.set_combo_by_data(self.theme_combo, self.config_data.ui_theme)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        self.theme_label = QLabel(self.tr_ui("テーマ"))
        language_form.addRow(self.theme_label, self.theme_combo)
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
        self.hide_colorize_tab_check = QCheckBox("AI彩色を表示しない")
        self.hide_colorize_tab_check.setChecked(self.config_data.hide_colorize_tab)
        self.hide_colorize_tab_check.stateChanged.connect(self.on_tab_visibility_settings_changed)
        other_layout.addWidget(self.hide_colorize_tab_check)
        self.hide_novelai_tab_check = QCheckBox("NovelAI生成を表示しない")
        self.hide_novelai_tab_check.setChecked(self.config_data.hide_novelai_tab)
        self.hide_novelai_tab_check.stateChanged.connect(self.on_tab_visibility_settings_changed)
        other_layout.addWidget(self.hide_novelai_tab_check)
        self.hide_keyconfig_tab_check = QCheckBox("キーコンフィグを表示しない")
        self.hide_keyconfig_tab_check.setChecked(self.config_data.hide_keyconfig_tab)
        self.hide_keyconfig_tab_check.stateChanged.connect(self.on_tab_visibility_settings_changed)
        other_layout.addWidget(self.hide_keyconfig_tab_check)
        other_layout.addWidget(self.separator())
        self.single_instance_check = QCheckBox("アプリの二重起動を禁止する")
        self.single_instance_check.setChecked(self.config_data.single_instance_enabled)
        self.single_instance_check.stateChanged.connect(self.on_general_settings_changed)
        other_layout.addWidget(self.single_instance_check)
        self.restore_last_image_check = QCheckBox("最後に開いていた画像を次回起動時に開く")
        self.restore_last_image_check.setChecked(self.config_data.restore_last_image_on_start)
        self.restore_last_image_check.stateChanged.connect(self.on_general_settings_changed)
        other_layout.addWidget(self.restore_last_image_check)
        self.folder_history_check = QCheckBox("フォルダごとに最後に開いていた画像を記録する")
        self.folder_history_check.setChecked(self.config_data.remember_last_image_per_folder)
        self.folder_history_check.stateChanged.connect(self.on_general_settings_changed)
        other_layout.addWidget(self.folder_history_check)
        folder_history_form = QFormLayout()
        self.folder_history_limit_spin = QSpinBox()
        self.folder_history_limit_spin.setRange(0, 999999)
        self.folder_history_limit_spin.setValue(max(0, int(self.config_data.folder_history_limit)))
        self.folder_history_limit_spin.valueChanged.connect(self.on_general_settings_changed)
        folder_history_form.addRow("フォルダ履歴保存件数", self.folder_history_limit_spin)
        other_layout.addLayout(folder_history_form)
        other_layout.addWidget(self.help_label("0 は無制限。履歴は setting.json ではなく folder_history.json に保存します。"))
        self.confirm_delete_check = QCheckBox("削除時に確認メッセージを出す")
        self.confirm_delete_check.setChecked(self.config_data.confirm_delete_current_image)
        self.confirm_delete_check.stateChanged.connect(self.on_general_settings_changed)
        other_layout.addWidget(self.confirm_delete_check)
        self.delete_processed_check = QCheckBox("削除時、拡大結果も削除する")
        self.delete_processed_check.setChecked(self.config_data.delete_processed_with_source)
        self.delete_processed_check.stateChanged.connect(self.on_general_settings_changed)
        other_layout.addWidget(self.delete_processed_check)
        self.cleanup_check = QCheckBox("次回起動時に古い一時ファイルを削除")
        self.cleanup_check.setChecked(self.config_data.cleanup_temp_on_start)
        self.cleanup_check.stateChanged.connect(self.on_cleanup_changed)
        other_layout.addWidget(self.cleanup_check)
        other_layout.addWidget(self.separator())
        version_form = QFormLayout()
        self.version_label = QLabel()
        self.version_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        version_form.addRow("バージョン", self.version_label)
        other_layout.addLayout(version_form)
        self.update_check_button = QPushButton("アップデートを確認")
        self.update_check_button.clicked.connect(self.check_for_updates)
        other_layout.addWidget(self.update_check_button)
        self.update_status_label = self.help_label("")
        self.update_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.update_status_label.setOpenExternalLinks(True)
        other_layout.addWidget(self.update_status_label)
        self.update_version_label()
        self.render_update_check_result()
        other_layout.addStretch(1)
        other_tab.setWidget(other_content)

        keyconfig_tab.setWidget(self.build_keyconfig_tab())

        self.normalize_form_labels(form, form3, viewer_form, background_form, compare_form, view_form, page_position_form, curve_form, comfy_form, colorize_prefetch_form, colorize_adjust_form, language_form, resample_form, folder_history_form, version_form)

        tab_index = {tab_id: index for index, tab_id in enumerate(SETTINGS_TAB_IDS)}.get(self.config_data.settings_tab, 0)
        self.tabs.setCurrentIndex(tab_index)
        self.apply_settings_tab_visibility()
        self.apply_engine_ui()
        self.update_hdr_tonemap_controls()
        QTimer.singleShot(0, self.apply_language)
        return root

    def build_novelai_tab_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.help_label("NovelAIの永続APIトークンを使い、テキストから画像を生成してRAIVへ取り込みます。バイブストランスファー、画像から画像生成、インペイントは未対応です。"))

        prompt_mode_row = QHBoxLayout()
        self.novelai_split_prompts_check = QCheckBox("プロンプトを分解する")
        self.novelai_split_prompts_check.setChecked(self.config_data.novelai_split_prompts)
        self.novelai_split_prompts_check.stateChanged.connect(self.on_novelai_split_prompts_changed)
        prompt_mode_row.addWidget(self.novelai_split_prompts_check)
        self.novelai_show_reconstructed_prompts_check = QCheckBox("再構築したプロンプトを表示する")
        self.novelai_show_reconstructed_prompts_check.setChecked(self.config_data.novelai_show_reconstructed_prompts)
        self.novelai_show_reconstructed_prompts_check.stateChanged.connect(self.on_novelai_show_reconstructed_prompts_changed)
        prompt_mode_row.addWidget(self.novelai_show_reconstructed_prompts_check)
        prompt_mode_row.addStretch(1)
        layout.addLayout(prompt_mode_row)
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("タグプリセット"))
        self.novelai_prompt_preset_combo = QComboBox()
        preset_row.addWidget(self.novelai_prompt_preset_combo, 1)
        self.novelai_prompt_preset_load_button = QPushButton("読込")
        self.novelai_prompt_preset_load_button.clicked.connect(self.load_novelai_prompt_preset)
        preset_row.addWidget(self.novelai_prompt_preset_load_button)
        self.novelai_prompt_preset_save_button = QPushButton("保存")
        self.novelai_prompt_preset_save_button.clicked.connect(self.save_novelai_prompt_preset_dialog)
        preset_row.addWidget(self.novelai_prompt_preset_save_button)
        self.novelai_prompt_preset_delete_button = QPushButton("削除")
        self.novelai_prompt_preset_delete_button.clicked.connect(self.delete_novelai_prompt_preset)
        preset_row.addWidget(self.novelai_prompt_preset_delete_button)
        layout.addLayout(preset_row)
        self.refresh_novelai_prompt_preset_combo()

        prompt_heading_row = QHBoxLayout()
        self.novelai_prompt_toggle_button = QPushButton("プロンプト v")
        self.novelai_prompt_toggle_button.setCheckable(True)
        self.novelai_prompt_toggle_button.setChecked(bool(self.config_data.novelai_prompt_expanded))
        self.novelai_prompt_toggle_button.clicked.connect(
            lambda checked: self.on_novelai_prompt_section_toggled("prompt", checked)
        )
        prompt_heading_row.addWidget(self.novelai_prompt_toggle_button, 1)
        self.novelai_add_prompt_items_at_top_check = QCheckBox("先頭に追加する")
        self.novelai_add_prompt_items_at_top_check.setChecked(self.config_data.novelai_add_prompt_items_at_top)
        self.novelai_add_prompt_items_at_top_check.stateChanged.connect(self.on_novelai_add_prompt_items_at_top_changed)
        prompt_heading_row.addWidget(self.novelai_add_prompt_items_at_top_check)
        self.novelai_delete_folder_contents_check = QCheckBox("フォルダ削除時、中身ごと消す")
        self.novelai_delete_folder_contents_check.setChecked(self.config_data.novelai_delete_folder_contents)
        self.novelai_delete_folder_contents_check.stateChanged.connect(self.on_novelai_delete_folder_contents_changed)
        prompt_heading_row.addWidget(self.novelai_delete_folder_contents_check)
        layout.addLayout(prompt_heading_row)
        self.novelai_prompt_edit = PromptSubmitTextEdit(self.config_data.novelai_prompt)
        self.novelai_prompt_edit.setMinimumHeight(0)
        self.novelai_prompt_edit.textChanged.connect(self.on_novelai_settings_changed)
        self.novelai_prompt_edit.submitRequested.connect(self.generate_novelai_images)
        layout.addWidget(self.novelai_prompt_edit)
        self.novelai_prompt_list_edit = NovelAIPromptListEditor("")
        self.novelai_prompt_list_edit.list_widget.dragStateChanged.connect(self.on_novelai_prompt_drag_state_changed)
        self.novelai_prompt_list_edit.set_items(self.config_data.novelai_prompt_items, self.config_data.novelai_prompt)
        self.novelai_prompt_list_edit.changed.connect(self.on_novelai_prompt_list_changed)
        self.novelai_prompt_list_edit.submitRequested.connect(self.generate_novelai_images)
        layout.addWidget(self.novelai_prompt_list_edit)
        self.novelai_reconstructed_prompt_label = self.help_label("")
        self.novelai_reconstructed_prompt_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.novelai_reconstructed_prompt_label)
        self.novelai_prompt_resize_handle = VerticalResizeHandle()
        self.novelai_prompt_resize_handle.resized.connect(
            lambda delta: self.resize_novelai_prompt_editor("prompt", delta)
        )
        layout.addWidget(self.novelai_prompt_resize_handle)
        self.novelai_negative_prompt_toggle_button = QPushButton("除外したい要素 v")
        self.novelai_negative_prompt_toggle_button.setCheckable(True)
        self.novelai_negative_prompt_toggle_button.setChecked(bool(self.config_data.novelai_negative_prompt_expanded))
        self.novelai_negative_prompt_toggle_button.clicked.connect(
            lambda checked: self.on_novelai_prompt_section_toggled("negative", checked)
        )
        layout.addWidget(self.novelai_negative_prompt_toggle_button)
        self.novelai_negative_edit = PromptSubmitTextEdit(self.config_data.novelai_negative_prompt)
        self.novelai_negative_edit.setMinimumHeight(0)
        self.novelai_negative_edit.textChanged.connect(self.on_novelai_settings_changed)
        self.novelai_negative_edit.submitRequested.connect(self.generate_novelai_images)
        layout.addWidget(self.novelai_negative_edit)
        self.novelai_negative_list_edit = NovelAIPromptListEditor("")
        self.novelai_negative_list_edit.list_widget.dragStateChanged.connect(self.on_novelai_prompt_drag_state_changed)
        self.novelai_negative_list_edit.set_items(self.config_data.novelai_negative_prompt_items, self.config_data.novelai_negative_prompt)
        self.novelai_negative_list_edit.changed.connect(self.on_novelai_prompt_list_changed)
        self.novelai_negative_list_edit.submitRequested.connect(self.generate_novelai_images)
        layout.addWidget(self.novelai_negative_list_edit)
        self.novelai_reconstructed_negative_prompt_label = self.help_label("")
        self.novelai_reconstructed_negative_prompt_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.novelai_reconstructed_negative_prompt_label)
        self.on_novelai_add_prompt_items_at_top_changed(persist=False)
        self.novelai_negative_resize_handle = VerticalResizeHandle()
        self.novelai_negative_resize_handle.resized.connect(
            lambda delta: self.resize_novelai_prompt_editor("negative", delta)
        )
        layout.addWidget(self.novelai_negative_resize_handle)
        self.apply_novelai_prompt_editor_heights()
        self.novelai_enter_generate_check = QCheckBox("Enterで生成する（改行はShift+Enter）")
        self.novelai_enter_generate_check.setChecked(self.config_data.novelai_enter_to_generate)
        self.novelai_enter_generate_check.stateChanged.connect(self.on_novelai_enter_generate_changed)
        layout.addWidget(self.novelai_enter_generate_check)
        self.on_novelai_delete_folder_contents_changed(persist=False)
        self.on_novelai_enter_generate_changed()
        self.update_novelai_prompt_editor_visibility()
        size_form = QFormLayout()
        self.novelai_size_combo = QComboBox()
        self.novelai_size_combo.addItems(list(NOVELAI_SIZE_PRESETS.keys()) + ["Custom"])
        self.novelai_size_combo.currentTextChanged.connect(self.on_novelai_size_preset_changed)
        size_form.addRow("画像解像度", self.novelai_size_combo)
        size_row = QHBoxLayout()
        self.novelai_width_spin = QSpinBox()
        self.novelai_width_spin.setRange(64, 4096)
        self.novelai_width_spin.setSingleStep(64)
        self.novelai_width_spin.setFixedWidth(96)
        self.novelai_width_spin.setValue(self.config_data.novelai_width)
        self.novelai_width_spin.valueChanged.connect(self.on_novelai_size_changed)
        self.novelai_height_spin = QSpinBox()
        self.novelai_height_spin.setRange(64, 4096)
        self.novelai_height_spin.setSingleStep(64)
        self.novelai_height_spin.setFixedWidth(96)
        self.novelai_height_spin.setValue(self.config_data.novelai_height)
        self.novelai_height_spin.valueChanged.connect(self.on_novelai_size_changed)
        size_row.addWidget(self.novelai_width_spin)
        size_row.addWidget(QLabel("x"))
        size_row.addWidget(self.novelai_height_spin)
        self.novelai_resolution_limit_label = QLabel("")
        self.novelai_resolution_limit_label.setStyleSheet("color: #e06060;")
        self.novelai_resolution_limit_label.setVisible(False)
        size_row.addWidget(self.novelai_resolution_limit_label)
        size_row.addStretch(1)
        size_form.addRow("幅 / 高さ", size_row)
        layout.addLayout(size_form)

        basic_form = QFormLayout()
        number_row = QHBoxLayout()
        self.novelai_batch_group = QButtonGroup(self)
        self.novelai_batch_group.setExclusive(True)
        for value in range(1, 9):
            button = QPushButton(str(value))
            button.setCheckable(True)
            button.setFixedWidth(34)
            self.novelai_batch_group.addButton(button, value)
            number_row.addWidget(button)
        number_row.addStretch(1)
        batch_button = self.novelai_batch_group.button(max(1, min(8, int(self.config_data.novelai_batch_count))))
        if batch_button is not None:
            batch_button.setChecked(True)
        self.novelai_batch_group.idClicked.connect(self.on_novelai_settings_changed)
        basic_form.addRow("生成枚数", number_row)
        seed_row = QHBoxLayout()
        seed_row.setContentsMargins(0, 0, 0, 0)
        seed_row.setAlignment(Qt.AlignLeft)
        self.novelai_random_seed_check = QCheckBox("ランダムシード")
        self.novelai_random_seed_check.setChecked(self.config_data.novelai_random_seed)
        self.novelai_random_seed_check.stateChanged.connect(self.on_novelai_random_seed_changed)
        self.novelai_seed_spin = QLineEdit(str(max(0, min(MAX_NOVELAI_SEED, int(self.config_data.novelai_seed)))))
        self.novelai_seed_spin.setFixedWidth(128)
        self.novelai_seed_spin.setAlignment(Qt.AlignLeft)
        self.novelai_seed_spin.setPlaceholderText("0-4294967295")
        self.novelai_seed_spin.textChanged.connect(self.on_novelai_settings_changed)
        self.novelai_seed_spin.editingFinished.connect(self.normalize_novelai_seed_input)
        self.novelai_seed_spin.setEnabled(not self.config_data.novelai_random_seed)
        seed_row.addWidget(self.novelai_random_seed_check)
        seed_row.addWidget(self.novelai_seed_spin)
        seed_row.addStretch(1)
        basic_form.addRow("シード値", seed_row)
        layout.addLayout(basic_form)

        self.novelai_detail_button = QPushButton("詳細設定 >")
        self.novelai_detail_button.setCheckable(True)
        self.novelai_detail_button.clicked.connect(self.on_novelai_detail_toggled)
        layout.addWidget(self.novelai_detail_button)
        self.novelai_detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.novelai_detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        output_form = QFormLayout()
        output_row = QHBoxLayout()
        self.novelai_output_dir_edit = QLineEdit(self.config_data.novelai_output_dir or str(DEFAULT_NOVELAI_GENERATED_DIR))
        self.novelai_output_dir_edit.editingFinished.connect(self.on_novelai_settings_changed)
        output_button = QPushButton("参照")
        output_button.clicked.connect(self.choose_novelai_output_dir)
        output_row.addWidget(self.novelai_output_dir_edit, 1)
        output_row.addWidget(output_button)
        output_form.addRow("保存先", output_row)
        filename_row = QHBoxLayout()
        self.novelai_filename_combo = QComboBox()
        self.novelai_filename_combo.addItem("シード値", "seed")
        self.novelai_filename_combo.addItem("日付/シード値", "date_seed")
        self.novelai_filename_combo.addItem("日付/時刻", "date_time")
        self.novelai_filename_combo.addItem("日付/時刻_シード値", "date_time_seed")
        self.novelai_filename_combo.addItem("カスタム", "custom")
        self.set_combo_by_data(self.novelai_filename_combo, self.config_data.novelai_output_name_mode)
        self.novelai_filename_combo.currentIndexChanged.connect(self.on_novelai_filename_preset_changed)
        filename_row.addWidget(self.novelai_filename_combo)
        self.novelai_filename_template_edit = QLineEdit(self.config_data.novelai_output_name_template)
        self.novelai_filename_template_edit.setToolTip(
            "使用できる変数:\n{YYYY}: 年（4桁）\n{MM}: 月（2桁）\n{DD}: 日（2桁）\n"
            "{HH}: 時（2桁）\n{mm}: 分（2桁）\n{ss}: 秒（2桁）\n"
            "{date}: 日付まとめ（YYYYMMDD）\n{time}: 時刻まとめ（HHMMSS）\n"
            "{seed}: 生成シード値\n/ または \\: フォルダ区切り（入れ子可能）\n"
            "末尾がフォルダ区切りの場合、ファイル名に {seed} を補います。\n例: {date}/{time}_{seed}"
        )
        self.novelai_filename_template_edit.installEventFilter(self)
        self.novelai_filename_template_edit.textEdited.connect(self.on_novelai_filename_template_edited)
        filename_row.addWidget(self.novelai_filename_template_edit, 1)
        filename_row.addWidget(QLabel(".png"))
        output_form.addRow("ファイル名", filename_row)
        detail_layout.addLayout(output_form)
        detail_auth_form = QFormLayout()
        self.saved_novelai_api_token = load_novelai_api_token()
        self.novelai_token_edit = QLineEdit(self.saved_novelai_api_token)
        self.novelai_token_edit.setEchoMode(QLineEdit.Password)
        self.novelai_token_edit.editingFinished.connect(self.on_novelai_settings_changed)
        detail_auth_form.addRow("永続APIトークン", self.novelai_token_edit)
        detail_layout.addLayout(detail_auth_form)
        quality_form = QFormLayout()
        self.novelai_quality_tags_check = QCheckBox("品質タグを追加する")
        self.novelai_quality_tags_check.setChecked(self.config_data.novelai_quality_tags)
        self.novelai_quality_tags_check.stateChanged.connect(self.on_novelai_settings_changed)
        quality_form.addRow(self.novelai_quality_tags_check)
        self.novelai_uc_preset_combo = QComboBox()
        for key, label in NOVELAI_UC_PRESET_OPTIONS:
            self.novelai_uc_preset_combo.addItem(label, key)
        self.set_combo_by_data(self.novelai_uc_preset_combo, self.config_data.novelai_uc_preset)
        self.novelai_uc_preset_combo.currentIndexChanged.connect(self.on_novelai_settings_changed)
        quality_form.addRow("除外プリセット", self.novelai_uc_preset_combo)
        self.novelai_dataset_mode_combo = QComboBox()
        for key, label in NOVELAI_DATASET_MODE_OPTIONS:
            self.novelai_dataset_mode_combo.addItem(label, key)
        self.set_combo_by_data(self.novelai_dataset_mode_combo, self.config_data.novelai_dataset_mode)
        self.novelai_dataset_mode_combo.currentIndexChanged.connect(self.on_novelai_settings_changed)
        quality_form.addRow("モード", self.novelai_dataset_mode_combo)
        detail_layout.addLayout(quality_form)

        params_form = QFormLayout()
        self.novelai_model_combo = QComboBox()
        self.novelai_model_combo.addItems(NOVELAI_MODEL_OPTIONS)
        self.novelai_model_combo.setCurrentText(self.config_data.novelai_model or DEFAULT_NOVELAI_MODEL)
        self.novelai_model_combo.currentTextChanged.connect(self.on_novelai_settings_changed)
        params_form.addRow("モデル", self.novelai_model_combo)
        self.novelai_sampler_combo = QComboBox()
        self.novelai_sampler_combo.addItems(NOVELAI_SAMPLER_OPTIONS)
        self.novelai_sampler_combo.setCurrentText(self.config_data.novelai_sampler or DEFAULT_NOVELAI_SAMPLER)
        self.novelai_sampler_combo.currentTextChanged.connect(self.on_novelai_settings_changed)
        params_form.addRow("サンプラー", self.novelai_sampler_combo)
        self.novelai_scheduler_combo = QComboBox()
        self.novelai_scheduler_combo.addItems(NOVELAI_SCHEDULER_OPTIONS)
        self.novelai_scheduler_combo.setCurrentText(self.config_data.novelai_scheduler or DEFAULT_NOVELAI_SCHEDULER)
        self.novelai_scheduler_combo.currentTextChanged.connect(self.on_novelai_settings_changed)
        params_form.addRow("ノイズスケジュール", self.novelai_scheduler_combo)
        self.novelai_steps_spin = QSpinBox()
        self.novelai_steps_spin.setRange(1, 150)
        self.novelai_steps_spin.setFixedWidth(96)
        self.novelai_steps_spin.setValue(self.config_data.novelai_steps)
        self.novelai_steps_spin.valueChanged.connect(self.on_novelai_settings_changed)
        params_form.addRow("ステップ数", self.novelai_steps_spin)
        self.novelai_scale_spin = QDoubleSpinBox()
        self.novelai_scale_spin.setRange(0.0, 30.0)
        self.novelai_scale_spin.setSingleStep(0.1)
        self.novelai_scale_spin.setDecimals(2)
        self.novelai_scale_spin.setFixedWidth(96)
        self.novelai_scale_spin.setValue(float(self.config_data.novelai_scale))
        self.novelai_scale_spin.valueChanged.connect(self.on_novelai_settings_changed)
        guidance_row = QHBoxLayout()
        guidance_row.addWidget(self.novelai_scale_spin)
        self.novelai_variety_boost_check = QCheckBox("多様性")
        self.novelai_variety_boost_check.setChecked(self.config_data.novelai_variety_boost)
        self.novelai_variety_boost_check.stateChanged.connect(self.on_novelai_settings_changed)
        guidance_row.addWidget(self.novelai_variety_boost_check)
        guidance_row.addStretch(1)
        params_form.addRow("プロンプトガイダンス", guidance_row)
        self.novelai_cfg_rescale_spin = QDoubleSpinBox()
        self.novelai_cfg_rescale_spin.setRange(0.0, 1.0)
        self.novelai_cfg_rescale_spin.setSingleStep(0.01)
        self.novelai_cfg_rescale_spin.setDecimals(2)
        self.novelai_cfg_rescale_spin.setFixedWidth(96)
        self.novelai_cfg_rescale_spin.setValue(float(self.config_data.novelai_cfg_rescale))
        self.novelai_cfg_rescale_spin.valueChanged.connect(self.on_novelai_settings_changed)
        params_form.addRow("プロンプトガイダンスの再調整", self.novelai_cfg_rescale_spin)
        detail_layout.addLayout(params_form)

        self.novelai_opus_check = QCheckBox("OpusプランとしてAnlasを推定")
        self.novelai_opus_check.setChecked(self.config_data.novelai_is_opus)
        self.novelai_opus_check.stateChanged.connect(self.on_novelai_settings_changed)
        self.novelai_auto_upscale_check = QCheckBox("生成後に拡大処理キューへ投入")
        self.novelai_auto_upscale_check.setChecked(self.config_data.novelai_auto_upscale)
        self.novelai_auto_upscale_check.stateChanged.connect(self.on_novelai_settings_changed)
        self.novelai_metadata_check = QCheckBox("生成設定をJSONサイドカーに保存")
        self.novelai_metadata_check.setChecked(self.config_data.novelai_save_metadata_json)
        self.novelai_metadata_check.stateChanged.connect(self.on_novelai_settings_changed)
        for check in (
            self.novelai_opus_check,
            self.novelai_auto_upscale_check,
            self.novelai_metadata_check,
        ):
            detail_layout.addWidget(check)
        layout.addWidget(self.novelai_detail_widget)
        self.novelai_detail_button.setChecked(bool(self.config_data.novelai_detail_expanded))
        self.on_novelai_detail_toggled(self.novelai_detail_button.isChecked())

        self.novelai_anlas_label = self.help_label("")
        self.novelai_anlas_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.novelai_anlas_label)
        run_row = QHBoxLayout()
        self.novelai_generate_button = QPushButton("生成")
        self.novelai_generate_button.installEventFilter(self)
        run_row.addWidget(self.novelai_generate_button)
        self.novelai_auto_open_check = QCheckBox("生成後に自動表示")
        self.novelai_auto_open_check.setChecked(self.config_data.novelai_auto_open)
        self.novelai_auto_open_check.stateChanged.connect(self.on_novelai_settings_changed)
        run_row.addWidget(self.novelai_auto_open_check)
        self.novelai_continuous_delay_widget = QWidget()
        delay_layout = QHBoxLayout(self.novelai_continuous_delay_widget)
        delay_layout.setContentsMargins(0, 0, 0, 0)
        delay_layout.setAlignment(Qt.AlignLeft)
        delay_layout.addWidget(QLabel("連続生成間隔"))
        self.novelai_continuous_delay_spin = QDoubleSpinBox()
        self.novelai_continuous_delay_spin.setRange(0.1, 3600.0)
        self.novelai_continuous_delay_spin.setDecimals(1)
        self.novelai_continuous_delay_spin.setSingleStep(0.5)
        self.novelai_continuous_delay_spin.setFixedWidth(92)
        self.novelai_continuous_delay_spin.setSuffix(f" {self.tr_ui('秒')}")
        self.novelai_continuous_delay_spin.setValue(max(0.1, min(3600.0, float(self.config_data.novelai_continuous_delay_seconds))))
        self.novelai_continuous_delay_spin.valueChanged.connect(self.on_novelai_settings_changed)
        delay_layout.addWidget(self.novelai_continuous_delay_spin)
        run_row.addWidget(self.novelai_continuous_delay_widget)
        self.novelai_import_button = QPushButton("メタデータをインポート")
        self.novelai_import_button.clicked.connect(self.import_novelai_metadata_dialog)
        run_row.addWidget(self.novelai_import_button)
        run_row.addStretch(1)
        layout.addLayout(run_row)
        self.novelai_status_label = self.help_label("")
        self.novelai_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.novelai_status_label)
        layout.addStretch(1)
        self.sync_novelai_size_preset()
        self.update_novelai_batch_buttons()
        self.update_novelai_anlas_preview()
        self.update_novelai_continuous_delay_visibility()
        return content

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
        label.setForegroundRole(QPalette.PlaceholderText)
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

    def choose_novelai_output_dir(self) -> None:
        current = Path(self.novelai_output_dir_edit.text().strip() or str(DEFAULT_NOVELAI_GENERATED_DIR))
        folder = QFileDialog.getExistingDirectory(self, "NovelAI生成画像の保存先", str(current if current.exists() else APP_DIR))
        if folder:
            self.novelai_output_dir_edit.setText(folder)
            self.on_novelai_settings_changed()

    def on_novelai_filename_preset_changed(self, *_args) -> None:
        mode = str(self.novelai_filename_combo.currentData() or "custom")
        template = NOVELAI_OUTPUT_NAME_TEMPLATES.get(mode)
        if template is not None:
            self.novelai_filename_template_edit.setText(template)
        self.on_novelai_settings_changed()

    def on_novelai_filename_template_edited(self, _text: str) -> None:
        custom_index = self.novelai_filename_combo.findData("custom")
        if custom_index >= 0 and self.novelai_filename_combo.currentIndex() != custom_index:
            self.novelai_filename_combo.blockSignals(True)
            self.novelai_filename_combo.setCurrentIndex(custom_index)
            self.novelai_filename_combo.blockSignals(False)
        self.on_novelai_settings_changed()

    def refresh_novelai_prompt_preset_combo(self, selected_name: str = "") -> None:
        combo = getattr(self, "novelai_prompt_preset_combo", None)
        if combo is None:
            return
        current = selected_name or str(combo.currentData() or "")
        combo.blockSignals(True)
        combo.clear()
        for preset in self.novelai_prompt_presets:
            name = str(preset.get("name") or "").strip()
            if name:
                combo.addItem(name, name)
        if current:
            self.set_combo_by_data(combo, current)
        combo.blockSignals(False)

    def novelai_prompt_items_for_preset(self, editor: NovelAIPromptListEditor, text_edit: PromptSubmitTextEdit) -> list[dict[str, object]]:
        if self.novelai_split_prompts_enabled():
            return editor.to_items()
        return editor.split_prompt_nodes(text_edit.toPlainText())

    def current_novelai_prompt_preset_payload(self, name: str) -> dict[str, object]:
        return {
            "name": name,
            "prompt_items": self.novelai_prompt_items_for_preset(self.novelai_prompt_list_edit, self.novelai_prompt_edit),
            "negative_items": self.novelai_prompt_items_for_preset(self.novelai_negative_list_edit, self.novelai_negative_edit),
        }

    def save_novelai_prompt_preset_dialog(self) -> None:
        current_name = str(self.novelai_prompt_preset_combo.currentData() or "") if hasattr(self, "novelai_prompt_preset_combo") else ""
        name, ok = QInputDialog.getText(self, APP_NAME, "タグプリセット名", text=current_name)
        name = name.strip()
        if not ok or not name:
            return
        existing_index = next((index for index, preset in enumerate(self.novelai_prompt_presets) if str(preset.get("name") or "") == name), -1)
        if existing_index >= 0:
            answer = QMessageBox.question(self, APP_NAME, f"タグプリセット「{name}」を上書きしますか？")
            if answer != QMessageBox.Yes:
                return
            self.novelai_prompt_presets[existing_index] = self.current_novelai_prompt_preset_payload(name)
        else:
            self.novelai_prompt_presets.append(self.current_novelai_prompt_preset_payload(name))
        self.novelai_prompt_presets.sort(key=lambda preset: str(preset.get("name") or "").casefold())
        save_novelai_prompt_presets(self.novelai_prompt_presets)
        self.refresh_novelai_prompt_preset_combo(name)

    def selected_novelai_prompt_preset(self) -> dict[str, object] | None:
        name = str(self.novelai_prompt_preset_combo.currentData() or "") if hasattr(self, "novelai_prompt_preset_combo") else ""
        if not name:
            return None
        return next((preset for preset in self.novelai_prompt_presets if str(preset.get("name") or "") == name), None)

    def load_novelai_prompt_preset(self) -> None:
        preset = self.selected_novelai_prompt_preset()
        if preset is None:
            return
        prompt_items = preset.get("prompt_items")
        negative_items = preset.get("negative_items")
        self.novelai_split_prompts_check.blockSignals(True)
        self.novelai_split_prompts_check.setChecked(True)
        self.novelai_split_prompts_check.blockSignals(False)
        self.novelai_prompt_list_edit.set_items(prompt_items if isinstance(prompt_items, list) else [], "")
        self.novelai_negative_list_edit.set_items(negative_items if isinstance(negative_items, list) else [], "")
        self.sync_novelai_text_from_lists()
        self.update_novelai_prompt_editor_visibility()
        self.on_novelai_settings_changed()

    def delete_novelai_prompt_preset(self) -> None:
        preset = self.selected_novelai_prompt_preset()
        if preset is None:
            return
        name = str(preset.get("name") or "")
        answer = QMessageBox.question(self, APP_NAME, f"タグプリセット「{name}」を削除しますか？")
        if answer != QMessageBox.Yes:
            return
        self.novelai_prompt_presets = [item for item in self.novelai_prompt_presets if str(item.get("name") or "") != name]
        save_novelai_prompt_presets(self.novelai_prompt_presets)
        self.refresh_novelai_prompt_preset_combo()

    def sync_novelai_size_preset(self) -> None:
        if not hasattr(self, "novelai_size_combo"):
            return
        current = (self.novelai_width_spin.value(), self.novelai_height_spin.value())
        label = next((name for name, size in NOVELAI_SIZE_PRESETS.items() if size == current), "Custom")
        self.novelai_size_combo.blockSignals(True)
        self.novelai_size_combo.setCurrentText(label)
        self.novelai_size_combo.blockSignals(False)

    def on_novelai_size_preset_changed(self, text: str) -> None:
        size = NOVELAI_SIZE_PRESETS.get(text)
        if size is not None:
            width, height = size
            self.novelai_width_spin.blockSignals(True)
            self.novelai_height_spin.blockSignals(True)
            self.novelai_width_spin.setValue(width)
            self.novelai_height_spin.setValue(height)
            self.novelai_width_spin.blockSignals(False)
            self.novelai_height_spin.blockSignals(False)
        self.update_novelai_batch_buttons()
        self.on_novelai_settings_changed()

    def on_novelai_size_changed(self, *_args) -> None:
        self.sync_novelai_size_preset()
        self.update_novelai_batch_buttons()
        self.on_novelai_settings_changed()

    def novelai_max_batch_count(self, width: int | None = None, height: int | None = None) -> int:
        if width is None:
            width = self.novelai_width_spin.value()
        if height is None:
            height = self.novelai_height_spin.value()
        pixels = max(1, int(width)) * max(1, int(height))
        for pixel_limit, batch_limit in NOVELAI_MAX_BATCH_BY_PIXELS:
            if pixels <= pixel_limit:
                return batch_limit
        return 0

    def update_novelai_batch_buttons(self) -> None:
        group = getattr(self, "novelai_batch_group", None)
        if group is None:
            return
        maximum = self.novelai_max_batch_count()
        if maximum > 0:
            tooltip = (
                f"この解像度では1回に最大{maximum}枚まで生成できます。"
                if self.ui_language() == "ja"
                else f"This resolution supports up to {maximum} images per request."
            )
        else:
            tooltip = (
                "この解像度はNovelAIの対応上限を超えています。"
                if self.ui_language() == "ja"
                else "This resolution exceeds NovelAI's supported limit."
            )
        for value in range(1, 9):
            button = group.button(value)
            if button is not None:
                button.setEnabled(value <= maximum)
                button.setToolTip("" if value <= maximum else tooltip)
        selected = group.checkedId()
        if maximum > 0 and selected > maximum:
            button = group.button(maximum)
            if button is not None:
                button.setChecked(True)
        resolution_label = getattr(self, "novelai_resolution_limit_label", None)
        if resolution_label is not None:
            resolution_label.setText(tooltip if maximum == 0 else "")
            resolution_label.setVisible(maximum == 0)
        self.update_novelai_generate_button_text()

    def on_novelai_random_seed_changed(self, *_args) -> None:
        if hasattr(self, "novelai_seed_spin"):
            self.novelai_seed_spin.setEnabled(not self.novelai_random_seed_check.isChecked())
        self.on_novelai_settings_changed()

    def novelai_seed_value(self) -> int:
        text = self.novelai_seed_spin.text().strip() if hasattr(self, "novelai_seed_spin") else "0"
        try:
            return max(0, min(MAX_NOVELAI_SEED, int(text)))
        except ValueError:
            return 0

    def set_novelai_seed_value(self, value: object) -> None:
        try:
            seed = max(0, min(MAX_NOVELAI_SEED, int(value)))
        except (TypeError, ValueError):
            seed = 0
        self.novelai_seed_spin.setText(str(seed))

    def normalize_novelai_seed_input(self) -> None:
        self.set_novelai_seed_value(self.novelai_seed_value())

    def on_novelai_detail_toggled(self, checked: bool) -> None:
        if hasattr(self, "novelai_detail_widget"):
            self.novelai_detail_widget.setVisible(bool(checked))
        if hasattr(self, "novelai_detail_button"):
            if self.novelai_detail_button.isChecked() != bool(checked):
                self.novelai_detail_button.blockSignals(True)
                self.novelai_detail_button.setChecked(bool(checked))
                self.novelai_detail_button.blockSignals(False)
            self.novelai_detail_button.setText(self.tr_ui("詳細設定 v" if checked else "詳細設定 >"))
        if hasattr(self, "config_data"):
            self.config_data.novelai_detail_expanded = bool(checked)
            if not getattr(self, "initializing", False):
                self.persist_config()

    def novelai_split_prompts_enabled(self) -> bool:
        return bool(getattr(self, "novelai_split_prompts_check", None) and self.novelai_split_prompts_check.isChecked())

    def on_novelai_prompt_section_toggled(self, target: str, checked: bool) -> None:
        checked = bool(checked)
        if target == "prompt":
            self.config_data.novelai_prompt_expanded = checked
        else:
            self.config_data.novelai_negative_prompt_expanded = checked
        self.update_novelai_prompt_editor_visibility()
        if not getattr(self, "initializing", False):
            self.persist_config()

    def on_novelai_show_reconstructed_prompts_changed(self, *_args) -> None:
        self.update_novelai_reconstructed_prompt_labels()
        self.update_novelai_prompt_editor_visibility()
        self.on_novelai_settings_changed()

    def update_novelai_reconstructed_prompt_labels(self) -> None:
        if not hasattr(self, "novelai_reconstructed_prompt_label"):
            return
        self.novelai_reconstructed_prompt_label.setText(self.novelai_prompt_list_edit.to_text())
        self.novelai_reconstructed_negative_prompt_label.setText(self.novelai_negative_list_edit.to_text())

    def on_novelai_prompt_drag_state_changed(self, active: bool) -> None:
        self.novelai_prompt_drag_active = bool(active)
        if active:
            self.overlay_hide_suppressed_until = float("inf")
            if self.side_panel_overlay and not self.pin_button.isChecked():
                self.set_overlay_side_panel_visible(True)
                self.side_panel.raise_()
        else:
            self.overlay_hide_suppressed_until = time.monotonic() + SIDE_PANEL_HIDE_GRACE_SEC
            QTimer.singleShot(SIDE_PANEL_HIDE_DELAY_MS, self.hide_overlay_side_panel_if_needed)

    def active_novelai_text_from_editor(self, editor: NovelAIPromptListEditor, text: str) -> str:
        return editor.active_text_from_text(text)

    def novelai_prompt_storage_text(self) -> str:
        if self.novelai_split_prompts_enabled() and hasattr(self, "novelai_prompt_list_edit"):
            return self.novelai_prompt_list_edit.to_text(active_only=False, preserve_inactive=True)
        return self.novelai_prompt_edit.toPlainText().strip()

    def novelai_negative_prompt_storage_text(self) -> str:
        if self.novelai_split_prompts_enabled() and hasattr(self, "novelai_negative_list_edit"):
            return self.novelai_negative_list_edit.to_text(active_only=False, preserve_inactive=True)
        return self.novelai_negative_edit.toPlainText().strip()

    def novelai_prompt_text(self) -> str:
        if self.novelai_split_prompts_enabled() and hasattr(self, "novelai_prompt_list_edit"):
            return self.novelai_prompt_list_edit.to_text()
        return self.active_novelai_text_from_editor(self.novelai_prompt_list_edit, self.novelai_prompt_edit.toPlainText())

    def novelai_negative_prompt_text(self) -> str:
        if self.novelai_split_prompts_enabled() and hasattr(self, "novelai_negative_list_edit"):
            return self.novelai_negative_list_edit.to_text()
        return self.active_novelai_text_from_editor(self.novelai_negative_list_edit, self.novelai_negative_edit.toPlainText())

    def novelai_dataset_mode(self) -> str:
        combo = getattr(self, "novelai_dataset_mode_combo", None)
        mode = combo.currentData() if combo is not None else self.config_data.novelai_dataset_mode
        return str(mode or "anime")

    def apply_novelai_dataset_mode_to_prompt(self, prompt: str) -> str:
        prompt = prompt.strip()
        if self.novelai_dataset_mode() != "furry":
            return prompt
        folded = prompt.casefold()
        tag = NOVELAI_FURRY_DATASET_TAG
        if folded == tag or folded.startswith(f"{tag},"):
            return prompt
        return f"{tag}, {prompt}" if prompt else tag

    def restore_novelai_dataset_mode(self, prompt: str) -> tuple[str, str]:
        stripped = prompt.strip()
        tag = NOVELAI_FURRY_DATASET_TAG
        folded = stripped.casefold()
        if folded == tag:
            return "", "furry"
        if folded.startswith(f"{tag},"):
            return stripped[len(tag) + 1 :].lstrip(), "furry"
        return prompt, "anime"

    def clamp_novelai_prompt_editor_height(self, height: int) -> int:
        return max(0, int(height))

    def apply_novelai_prompt_editor_heights(self) -> None:
        prompt_height = self.clamp_novelai_prompt_editor_height(self.config_data.novelai_prompt_editor_height)
        negative_height = self.clamp_novelai_prompt_editor_height(self.config_data.novelai_negative_prompt_editor_height)
        for widget in (self.novelai_prompt_edit, self.novelai_prompt_list_edit):
            widget.setFixedHeight(prompt_height)
        for widget in (self.novelai_negative_edit, self.novelai_negative_list_edit):
            widget.setFixedHeight(negative_height)

    def resize_novelai_prompt_editor(self, target: str, delta: int) -> None:
        if target == "prompt":
            self.config_data.novelai_prompt_editor_height = self.clamp_novelai_prompt_editor_height(
                self.config_data.novelai_prompt_editor_height + delta
            )
        else:
            self.config_data.novelai_negative_prompt_editor_height = self.clamp_novelai_prompt_editor_height(
                self.config_data.novelai_negative_prompt_editor_height + delta
            )
        self.apply_novelai_prompt_editor_heights()
        self.on_novelai_settings_changed()

    def update_novelai_prompt_editor_visibility(self) -> None:
        if not hasattr(self, "novelai_prompt_list_edit"):
            return
        split_enabled = self.novelai_split_prompts_enabled()
        prompt_expanded = self.novelai_prompt_toggle_button.isChecked()
        negative_expanded = self.novelai_negative_prompt_toggle_button.isChecked()
        self.update_novelai_reconstructed_prompt_labels()
        self.novelai_prompt_toggle_button.setText(self.tr_ui("プロンプト v" if prompt_expanded else "プロンプト >"))
        self.novelai_negative_prompt_toggle_button.setText(
            self.tr_ui("除外したい要素 v" if negative_expanded else "除外したい要素 >")
        )
        self.novelai_prompt_edit.setVisible(prompt_expanded and not split_enabled)
        self.novelai_negative_edit.setVisible(negative_expanded and not split_enabled)
        self.novelai_prompt_list_edit.setVisible(prompt_expanded and split_enabled)
        self.novelai_negative_list_edit.setVisible(negative_expanded and split_enabled)
        show_reconstructed = split_enabled and self.novelai_show_reconstructed_prompts_check.isChecked()
        self.novelai_show_reconstructed_prompts_check.setEnabled(split_enabled)
        self.novelai_reconstructed_prompt_label.setVisible(prompt_expanded and show_reconstructed)
        self.novelai_reconstructed_negative_prompt_label.setVisible(negative_expanded and show_reconstructed)
        self.novelai_prompt_resize_handle.setVisible(prompt_expanded)
        self.novelai_negative_resize_handle.setVisible(negative_expanded)
        if hasattr(self, "novelai_add_prompt_items_at_top_check"):
            self.novelai_add_prompt_items_at_top_check.setVisible(split_enabled)
        if hasattr(self, "novelai_enter_generate_check"):
            self.novelai_enter_generate_check.setVisible(not split_enabled)
        if hasattr(self, "novelai_delete_folder_contents_check"):
            self.novelai_delete_folder_contents_check.setVisible(split_enabled)

    def sync_novelai_lists_from_text(self) -> None:
        if hasattr(self, "novelai_prompt_list_edit"):
            self.novelai_prompt_list_edit.set_text(self.novelai_prompt_edit.toPlainText())
        if hasattr(self, "novelai_negative_list_edit"):
            self.novelai_negative_list_edit.set_text(self.novelai_negative_edit.toPlainText())

    def on_novelai_split_prompts_changed(self, *_args) -> None:
        if self.novelai_split_prompts_enabled():
            self.sync_novelai_lists_from_text()
        else:
            self.sync_novelai_text_from_lists()
        self.update_novelai_prompt_editor_visibility()
        self.on_novelai_settings_changed()

    def on_novelai_add_prompt_items_at_top_changed(self, *_args, persist: bool = True) -> None:
        enabled = bool(
            getattr(self, "novelai_add_prompt_items_at_top_check", None)
            and self.novelai_add_prompt_items_at_top_check.isChecked()
        )
        for editor_name in ("novelai_prompt_list_edit", "novelai_negative_list_edit"):
            editor = getattr(self, editor_name, None)
            if isinstance(editor, NovelAIPromptListEditor):
                editor.add_items_at_top = enabled
        if persist:
            self.on_novelai_settings_changed()

    def on_novelai_prompt_list_changed(self) -> None:
        if not self.novelai_split_prompts_enabled():
            return
        self.sync_novelai_text_from_lists()
        self.update_novelai_reconstructed_prompt_labels()
        self.on_novelai_settings_changed()

    def sync_novelai_text_from_lists(self) -> None:
        self.novelai_prompt_edit.blockSignals(True)
        self.novelai_negative_edit.blockSignals(True)
        self.novelai_prompt_edit.setPlainText(self.novelai_prompt_list_edit.to_text(active_only=False, preserve_inactive=True))
        self.novelai_negative_edit.setPlainText(self.novelai_negative_list_edit.to_text(active_only=False, preserve_inactive=True))
        self.novelai_prompt_edit.blockSignals(False)
        self.novelai_negative_edit.blockSignals(False)

    def on_novelai_enter_generate_changed(self, *_args) -> None:
        enabled = bool(self.novelai_enter_generate_check.isChecked()) if hasattr(self, "novelai_enter_generate_check") else True
        for edit_name in ("novelai_prompt_edit", "novelai_negative_edit"):
            edit = getattr(self, edit_name, None)
            if edit is not None:
                edit.enter_submits = enabled
        self.on_novelai_settings_changed()

    def on_novelai_delete_folder_contents_changed(self, *_args, persist: bool = True) -> None:
        enabled = bool(
            getattr(self, "novelai_delete_folder_contents_check", None)
            and self.novelai_delete_folder_contents_check.isChecked()
        )
        for editor_name in ("novelai_prompt_list_edit", "novelai_negative_list_edit"):
            editor = getattr(self, editor_name, None)
            if isinstance(editor, NovelAIPromptListEditor):
                editor.delete_folder_contents = enabled
        if persist:
            self.on_novelai_settings_changed()

    def novelai_number_of_images(self) -> int:
        group = getattr(self, "novelai_batch_group", None)
        if group is None:
            return max(1, min(8, int(self.config_data.novelai_batch_count)))
        value = group.checkedId()
        return max(1, min(8, int(value if value > 0 else 1)))

    def on_novelai_settings_changed(self, *_args) -> None:
        if not getattr(self, "initializing", False):
            self.schedule_persist_config()
            self.novelai_preview_timer.start(NOVELAI_PREVIEW_DEBOUNCE_MS)

    def current_novelai_request(self, seed: int | None = None) -> dict[str, object]:
        return {
            "prompt": self.apply_novelai_dataset_mode_to_prompt(self.novelai_prompt_text()),
            "negative_prompt": self.novelai_negative_prompt_text(),
            "model": self.novelai_model_combo.currentText().strip() or DEFAULT_NOVELAI_MODEL,
            "sampler": self.novelai_sampler_combo.currentText().strip() or DEFAULT_NOVELAI_SAMPLER,
            "noise_schedule": self.novelai_scheduler_combo.currentText().strip() or DEFAULT_NOVELAI_SCHEDULER,
            "seed": int(self.novelai_seed_value() if seed is None else seed),
            "width": self.novelai_width_spin.value(),
            "height": self.novelai_height_spin.value(),
            "steps": self.novelai_steps_spin.value(),
            "scale": self.novelai_scale_spin.value(),
            "cfg_rescale": self.novelai_cfg_rescale_spin.value(),
            "variety_boost": self.novelai_variety_boost_check.isChecked(),
            "n_samples": self.novelai_number_of_images(),
            "quality": self.novelai_quality_tags_check.isChecked(),
            "uc_preset": self.novelai_uc_preset_combo.currentData() or "strong",
        }

    def estimate_novelai_anlas(self) -> int | None:
        try:
            from novelai.types import GenerateImageParams
            request = self.current_novelai_request()
            kwargs: dict[str, object] = {
                "prompt": str(request["prompt"]),
                "model": str(request["model"]),
                "size": (int(request["width"]), int(request["height"])),
                "steps": int(request["steps"]),
                "scale": float(request["scale"]),
                "cfg_rescale": float(request["cfg_rescale"]),
                "seed": int(request["seed"]),
                "n_samples": int(request["n_samples"]),
                "variety_boost": bool(request["variety_boost"]),
                "quality": bool(request["quality"]),
                "uc_preset": str(request["uc_preset"]),
            }
            if str(request["negative_prompt"]).strip():
                kwargs["negative_prompt"] = str(request["negative_prompt"]).strip()
            if str(request["sampler"]).strip():
                kwargs["sampler"] = str(request["sampler"]).strip()
            if str(request["noise_schedule"]).strip():
                kwargs["noise_schedule"] = str(request["noise_schedule"]).strip()
            params = GenerateImageParams(**kwargs)
            estimate = params.calculate_anlas(is_opus=self.novelai_opus_check.isChecked())
            return int(estimate)
        except Exception:
            return None

    def update_novelai_anlas_preview(self) -> None:
        if not hasattr(self, "novelai_anlas_label"):
            return
        estimate = self.estimate_novelai_anlas()
        if estimate is None:
            self.novelai_anlas_label.setText("推定消費Anlas: novelai-sdk未インストール、または現在の設定では推定できません。")
            return
        self.novelai_anlas_label.setText(f"推定消費Anlas: {estimate}（SDKによる推定。実際の消費量と完全一致する保証はありません）")

    def import_novelai_metadata_dialog(self) -> None:
        initial = self.config_data.last_dir or self.novelai_output_dir_edit.text().strip() or str(APP_DIR)
        path_text, _filter = QFileDialog.getOpenFileName(
            self,
            "NovelAIメタデータをインポート",
            initial,
            "Images (*.png *.webp);;All files (*.*)",
        )
        if not path_text:
            return
        try:
            metadata = self.read_novelai_metadata(Path(path_text))
            self.apply_novelai_metadata(metadata)
            self.novelai_status_label.setText("NovelAIメタデータをインポートしました。")
            self.persist_config()
        except Exception as exc:
            self.novelai_status_label.setText(f"NovelAIメタデータを読み込めませんでした: {exc}")
            QMessageBox.warning(self, APP_NAME, f"NovelAIメタデータを読み込めませんでした。\n\n{exc}")

    def read_novelai_metadata(self, path: Path) -> dict[str, object]:
        if PILImage is None:
            raise RuntimeError("Pillow is not available")
        with PILImage.open(path) as image:
            info = dict(image.info)
        comment = info.get("Comment") or info.get("comment") or info.get("parameters")
        if not isinstance(comment, str) or not comment.strip():
            raise ValueError("Comment JSONが見つかりません。")
        data = json.loads(comment)
        if not isinstance(data, dict):
            raise ValueError("Comment JSONの形式が不正です。")
        data["_source_text"] = str(info.get("Source") or "")
        return data

    def novelai_model_from_metadata(self, metadata: dict[str, object]) -> str:
        model = str(metadata.get("model") or "").strip()
        if model in NOVELAI_MODEL_OPTIONS:
            return model
        source = str(metadata.get("_source_text") or "").casefold()
        if "4.5" in source:
            return "nai-diffusion-4-5-curated" if "curated" in source else "nai-diffusion-4-5-full"
        if "v4" in source or "diffusion 4" in source:
            return "nai-diffusion-4-curated" if "curated" in source else "nai-diffusion-4-full"
        if "v3" in source or "diffusion 3" in source:
            return "nai-diffusion-3"
        return DEFAULT_NOVELAI_MODEL

    def strip_novelai_suffix(self, text: str, suffixes: list[str]) -> tuple[str, bool]:
        stripped = text.rstrip()
        folded = stripped.casefold()
        for suffix in sorted(suffixes, key=len, reverse=True):
            suffix = suffix.strip()
            if suffix and folded.endswith(suffix.casefold()):
                return stripped[: len(stripped) - len(suffix)].rstrip(), True
        return text, False

    def restore_novelai_quality_tags(self, prompt: str, model: str) -> tuple[str, bool]:
        suffixes = NOVELAI_QUALITY_TAGS_SUFFIXES_BY_MODEL.get(model, [])
        return self.strip_novelai_suffix(prompt, suffixes)

    def restore_novelai_uc_preset(self, negative: str, model: str) -> tuple[str, str]:
        preset_texts = NOVELAI_UC_PRESET_TEXTS_BY_MODEL.get(model, {})
        candidates: list[tuple[str, str]] = []
        for preset, suffixes in preset_texts.items():
            for suffix in suffixes:
                candidates.append((preset, suffix))
        stripped = negative.rstrip()
        folded = stripped.casefold()
        for preset, preset_text in sorted(candidates, key=lambda item: len(item[1]), reverse=True):
            preset_text = preset_text.strip()
            if not preset_text:
                continue
            preset_folded = preset_text.casefold()
            if folded.startswith(preset_folded):
                remainder = stripped[len(preset_text) :].lstrip(" ,")
                return remainder, preset
        for preset, preset_text in sorted(candidates, key=lambda item: len(item[1]), reverse=True):
            preset_text = preset_text.strip()
            if preset_text and folded.endswith(preset_text.casefold()):
                return stripped[: len(stripped) - len(preset_text)].rstrip(" ,"), preset
        return negative, "none"

    def set_novelai_number_of_images(self, value: int) -> None:
        button = self.novelai_batch_group.button(max(1, min(8, int(value))))
        if button is not None:
            button.setChecked(True)

    def apply_novelai_metadata(self, metadata: dict[str, object]) -> None:
        prompt = str(metadata.get("prompt") or metadata.get("Description") or "")
        v4_prompt = metadata.get("v4_prompt")
        if not prompt and isinstance(v4_prompt, dict):
            caption = v4_prompt.get("caption")
            if isinstance(caption, dict):
                prompt = str(caption.get("base_caption") or "")
        negative = str(metadata.get("uc") or "")
        v4_negative = metadata.get("v4_negative_prompt")
        if not negative and isinstance(v4_negative, dict):
            caption = v4_negative.get("caption")
            if isinstance(caption, dict):
                negative = str(caption.get("base_caption") or "")
        model = self.novelai_model_from_metadata(metadata)
        prompt, dataset_mode = self.restore_novelai_dataset_mode(prompt)
        prompt, quality_enabled = self.restore_novelai_quality_tags(prompt, model)
        negative, uc_preset = self.restore_novelai_uc_preset(negative, model)
        self.novelai_prompt_edit.setPlainText(prompt)
        self.novelai_negative_edit.setPlainText(negative)
        self.sync_novelai_lists_from_text()
        self.set_combo_by_text(self.novelai_model_combo, model)
        self.set_combo_by_data(self.novelai_dataset_mode_combo, dataset_mode)
        self.set_combo_by_text(self.novelai_sampler_combo, str(metadata.get("sampler") or DEFAULT_NOVELAI_SAMPLER))
        self.set_combo_by_text(self.novelai_scheduler_combo, str(metadata.get("noise_schedule") or DEFAULT_NOVELAI_SCHEDULER))
        self.novelai_width_spin.setValue(max(64, min(4096, int(metadata.get("width", self.novelai_width_spin.value())))))
        self.novelai_height_spin.setValue(max(64, min(4096, int(metadata.get("height", self.novelai_height_spin.value())))))
        self.sync_novelai_size_preset()
        self.novelai_steps_spin.setValue(max(1, min(150, int(metadata.get("steps", self.novelai_steps_spin.value())))))
        self.novelai_scale_spin.setValue(max(0.0, min(30.0, float(metadata.get("scale", self.novelai_scale_spin.value())))))
        self.novelai_cfg_rescale_spin.setValue(max(0.0, min(1.0, float(metadata.get("cfg_rescale", self.novelai_cfg_rescale_spin.value())))))
        self.novelai_random_seed_check.setChecked(False)
        self.novelai_seed_spin.setEnabled(True)
        self.set_novelai_seed_value(metadata.get("seed", self.novelai_seed_value()))
        self.set_novelai_number_of_images(max(1, min(8, int(metadata.get("n_samples", 1)))))
        self.update_novelai_batch_buttons()
        self.novelai_variety_boost_check.setChecked(bool(metadata.get("variety_boost", False)))
        self.novelai_quality_tags_check.setChecked(quality_enabled)
        self.set_combo_by_data(self.novelai_uc_preset_combo, uc_preset)
        self.update_novelai_anlas_preview()

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
        self.update_side_panel_side_button()
        if hasattr(self, "language_label"):
            self.language_label.setText("Language")
        self.update_side_panel_resize_handle_tooltips()
        if hasattr(self, "theme_combo"):
            current = self.theme_combo.currentData() or THEME_SYSTEM
            self.theme_combo.blockSignals(True)
            self.theme_combo.clear()
            for key, label in THEME_OPTIONS:
                self.theme_combo.addItem(self.tr_ui(label), key)
            self.set_combo_by_data(self.theme_combo, current)
            self.theme_combo.blockSignals(False)
            self.theme_label.setText(self.tr_ui("テーマ"))
        if hasattr(self, "version_label"):
            self.update_version_label()
            self.render_update_check_result()
        if hasattr(self, "tone_curve_channel_combo"):
            current = self.tone_curve_channel_combo.currentData() or "value"
            self.tone_curve_channel_combo.blockSignals(True)
            self.tone_curve_channel_combo.clear()
            for channel in CURVE_CHANNELS:
                self.tone_curve_channel_combo.addItem(self.tr_ui(CURVE_CHANNEL_LABELS[channel]), channel)
            index = self.tone_curve_channel_combo.findData(current)
            self.tone_curve_channel_combo.setCurrentIndex(max(0, index))
            self.tone_curve_channel_combo.blockSignals(False)
        if hasattr(self, "novelai_uc_preset_combo"):
            current = self.novelai_uc_preset_combo.currentData() or "strong"
            self.novelai_uc_preset_combo.blockSignals(True)
            self.novelai_uc_preset_combo.clear()
            for key, label in NOVELAI_UC_PRESET_OPTIONS:
                self.novelai_uc_preset_combo.addItem(self.tr_ui(label), key)
            self.set_combo_by_data(self.novelai_uc_preset_combo, current)
            self.novelai_uc_preset_combo.blockSignals(False)
        if hasattr(self, "novelai_filename_combo"):
            current = self.novelai_filename_combo.currentData() or "seed"
            self.novelai_filename_combo.blockSignals(True)
            self.novelai_filename_combo.clear()
            self.novelai_filename_combo.addItem(self.tr_ui("シード値"), "seed")
            self.novelai_filename_combo.addItem(self.tr_ui("日付/シード値"), "date_seed")
            self.novelai_filename_combo.addItem(self.tr_ui("日付/時刻"), "date_time")
            self.novelai_filename_combo.addItem(self.tr_ui("日付/時刻_シード値"), "date_time_seed")
            self.novelai_filename_combo.addItem(self.tr_ui("カスタム"), "custom")
            self.set_combo_by_data(self.novelai_filename_combo, current)
            self.novelai_filename_combo.blockSignals(False)
        if hasattr(self, "novelai_filename_template_edit"):
            self.novelai_filename_template_edit.setToolTip(
                self.tr_ui(
                    "使用できる変数:\n{YYYY}: 年（4桁）\n{MM}: 月（2桁）\n{DD}: 日（2桁）\n"
                    "{HH}: 時（2桁）\n{mm}: 分（2桁）\n{ss}: 秒（2桁）\n"
                    "{date}: 日付まとめ（YYYYMMDD）\n{time}: 時刻まとめ（HHMMSS）\n"
                    "{seed}: 生成シード値\n/ または \\: フォルダ区切り（入れ子可能）\n"
                    "末尾がフォルダ区切りの場合、ファイル名に {seed} を補います。\n例: {date}/{time}_{seed}"
                )
            )
        self.update_novelai_batch_buttons()
        for editor_name in ("novelai_prompt_list_edit", "novelai_negative_list_edit"):
            editor = getattr(self, editor_name, None)
            if isinstance(editor, NovelAIPromptListEditor):
                editor.apply_language(self.ui_language())
        if hasattr(self, "novelai_prompt_toggle_button"):
            self.update_novelai_prompt_editor_visibility()
        if hasattr(self, "novelai_continuous_delay_spin"):
            self.novelai_continuous_delay_spin.setSuffix(f" {self.tr_ui('秒')}")
        off_text = "0 (Off)" if self.ui_language() == "en" else "0 (オフ)"
        for name in (
            "gigapixel_denoise_spin",
            "gigapixel_sharpen_spin",
            "gigapixel_compression_spin",
            "gigapixel_face_recovery_spin",
        ):
            spin = getattr(self, name, None)
            if isinstance(spin, QSpinBox):
                spin.setSpecialValueText(off_text)
        self.update_novelai_generate_button_text()
        self.update_zoom_label(self.viewer.current_scale() if hasattr(self, "viewer") else 1.0)
        self.update_page_position_slider()
        self.update_hdr_tonemap_controls()
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

    def update_version_label(self) -> None:
        if hasattr(self, "version_label"):
            self.version_label.setText(f"{APP_SHORT_NAME} v{APP_VERSION}")

    def render_update_check_result(self) -> None:
        if not hasattr(self, "update_status_label"):
            return
        result = self.update_check_result or {}
        status = result.get("status", "")
        english = self.ui_language() == "en"
        if not status:
            self.update_status_label.setText("")
        elif status == "checking":
            self.update_status_label.setText("Checking for updates..." if english else "アップデートを確認中...")
        elif status == "latest":
            self.update_status_label.setText(
                f"You are using the latest version. Current: v{APP_VERSION}"
                if english
                else f"最新版です。現在のバージョン: v{APP_VERSION}"
            )
        elif status == "available":
            tag = result.get("tag_name", "")
            url = result.get("html_url") or RELEASES_PAGE_URL
            if english:
                self.update_status_label.setText(f"A new version is available: {tag}\nReleases: {url}")
            else:
                self.update_status_label.setText(f"新しいバージョンがあります: {tag}\nReleases: {url}")
        elif status == "error":
            message = result.get("message", "")
            self.update_status_label.setText(
                f"Update check failed: {message}"
                if english
                else f"アップデート確認に失敗しました: {message}"
            )
        else:
            self.update_status_label.setText(str(result))

    def check_for_updates(self) -> None:
        if self.update_check_running:
            return
        self.update_check_running = True
        self.update_check_result = {"status": "checking"}
        self.update_check_button.setEnabled(False)
        self.render_update_check_result()

        def worker() -> None:
            try:
                info = latest_release_info()
                tag = info.get("tag_name", "")
                if not tag:
                    raise ValueError("latest release tag was empty")
                if compare_versions(tag, APP_VERSION) > 0:
                    result = {"status": "available", **info}
                else:
                    result = {"status": "latest", **info}
            except urllib.error.HTTPError as exc:
                result = {"status": "error", "message": f"HTTP {exc.code}"}
            except urllib.error.URLError as exc:
                result = {"status": "error", "message": str(exc.reason)}
            except Exception as exc:
                result = {"status": "error", "message": str(exc)}
            self.signals.update_check_done.emit(result)

        threading.Thread(target=worker, daemon=True).start()

    def on_update_check_done(self, result: object) -> None:
        self.update_check_running = False
        if hasattr(self, "update_check_button"):
            self.update_check_button.setEnabled(True)
        self.update_check_result = result if isinstance(result, dict) else {"status": "error", "message": str(result)}
        self.render_update_check_result()

    def comfyui_api_base(self) -> str:
        return self.comfyui_api_edit.text().strip() or DEFAULT_COMFYUI_API_URL

    def on_comfyui_settings_changed(self, *_args) -> None:
        self.schedule_persist_config()

    def on_comfyui_workflow_changed(self) -> None:
        self.persist_config()
        self.detect_comfyui_nodes(update_status=False)

    def choose_comfyui_workflow(self) -> None:
        start_dir = str(Path(self.comfyui_workflow_edit.text()).parent) if self.comfyui_workflow_edit.text().strip() else self.config_data.last_dir or str(APP_DIR)
        path, _filter = QFileDialog.getOpenFileName(self, self.tr_ui("workflow JSON"), start_dir, "JSON (*.json);;All files (*.*)")
        if not path:
            return
        self.comfyui_workflow_edit.setText(path)
        self.on_comfyui_workflow_changed()

    def set_combo_by_data(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(max(0, index))

    def set_combo_by_text(self, combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        combo.setCurrentIndex(max(0, index))

    def detect_comfyui_nodes(self, update_status: bool = True) -> None:
        if not hasattr(self, "comfyui_input_combo"):
            return
        previous_input = str(self.comfyui_input_combo.currentData() or self.config_data.comfyui_input_node_id or "")
        previous_output = str(self.comfyui_output_combo.currentData() or self.config_data.comfyui_output_node_id or "")
        self.comfyui_input_combo.blockSignals(True)
        self.comfyui_output_combo.blockSignals(True)
        self.comfyui_input_combo.clear()
        self.comfyui_output_combo.clear()
        path_text = self.comfyui_workflow_edit.text().strip() if hasattr(self, "comfyui_workflow_edit") else ""
        try:
            if not path_text:
                return
            workflow = load_comfyui_api_workflow(Path(path_text))
            input_choices = comfyui_node_choices(workflow, {"LoadImage"})
            output_choices = comfyui_node_choices(workflow, {"SaveImage", "PreviewImage"})
            for node_id, label in input_choices:
                self.comfyui_input_combo.addItem(label, node_id)
            for node_id, label in output_choices:
                self.comfyui_output_combo.addItem(label, node_id)
            self.set_combo_by_data(self.comfyui_input_combo, previous_input)
            self.set_combo_by_data(self.comfyui_output_combo, previous_output)
            if update_status and hasattr(self, "comfyui_status_label"):
                self.comfyui_status_label.setText(f"LoadImage: {len(input_choices)} / Output: {len(output_choices)}")
        except Exception as exc:
            if update_status and hasattr(self, "comfyui_status_label"):
                self.comfyui_status_label.setText(f"workflow JSONを読み込めません: {exc}")
        finally:
            self.comfyui_input_combo.blockSignals(False)
            self.comfyui_output_combo.blockSignals(False)
            self.persist_config()

    def check_comfyui_connection(self) -> None:
        if self.comfyui_connection_running:
            return
        api_url = self.comfyui_api_base()
        self.comfyui_connection_running = True
        self.comfyui_check_button.setEnabled(False)
        self.comfyui_status_label.setText(f"ComfyUIへ接続確認中: {api_url}")

        def worker() -> None:
            try:
                stats = comfyui_get_json(api_url, "/system_stats", timeout=8)
                result = {"status": "ok", "system": stats.get("system", {})}
            except urllib.error.HTTPError as exc:
                result = {"status": "error", "message": f"HTTP {exc.code}"}
            except urllib.error.URLError as exc:
                result = {"status": "error", "message": str(exc.reason)}
            except Exception as exc:
                result = {"status": "error", "message": str(exc)}
            self.signals.comfyui_connection_done.emit(result)

        threading.Thread(target=worker, daemon=True).start()

    def on_comfyui_connection_done(self, result: object) -> None:
        self.comfyui_connection_running = False
        if hasattr(self, "comfyui_check_button"):
            self.comfyui_check_button.setEnabled(True)
        if not isinstance(result, dict):
            self.comfyui_status_label.setText(str(result))
            return
        if result.get("status") == "ok":
            self.comfyui_status_label.setText(f"ComfyUIに接続できました: {self.comfyui_api_base()}")
        else:
            self.comfyui_status_label.setText(f"ComfyUIに接続できません: {result.get('message', '')}")

    def comfyui_base_dir(self) -> Path | None:
        text = self.comfyui_base_dir_edit.text().strip()
        return Path(text) if text else None

    def comfyui_recommended_model_path(self) -> Path | None:
        base_dir = self.comfyui_base_dir()
        if base_dir is None:
            return None
        return base_dir / "models" / "checkpoints" / COMFYUI_RECOMMENDED_MODEL_NAME

    def comfyui_recommended_controlnet_path(self) -> Path | None:
        base_dir = self.comfyui_base_dir()
        if base_dir is None:
            return None
        return base_dir / "models" / "controlnet" / COMFYUI_RECOMMENDED_CONTROLNET_NAME

    def setup_comfyui_defaults(self) -> None:
        if self.comfyui_setup_running:
            return
        api_url = self.comfyui_api_base()
        self.comfyui_setup_running = True
        self.comfyui_setup_button.setEnabled(False)
        self.comfyui_status_label.setText("ComfyUI初期設定を確認中...")

        def worker() -> None:
            try:
                stats = comfyui_get_json(api_url, "/system_stats", timeout=12)
                base_dir = comfyui_base_dir_from_system_stats(stats)
                checkpoints = comfyui_checkpoint_names(api_url)
                controlnets = comfyui_controlnet_names(api_url)
                has_model = COMFYUI_RECOMMENDED_MODEL_NAME in checkpoints
                has_controlnet = COMFYUI_RECOMMENDED_CONTROLNET_NAME in controlnets
                workflow_path = COMFYUI_WORKFLOW_DIR / COMFYUI_DEFAULT_WORKFLOW_NAME
                if has_model and has_controlnet:
                    save_default_comfyui_workflow(
                        workflow_path,
                        COMFYUI_RECOMMENDED_MODEL_NAME,
                        COMFYUI_RECOMMENDED_CONTROLNET_NAME,
                    )
                result = {
                    "status": "ok",
                    "api_url": api_url,
                    "base_dir": str(base_dir) if base_dir is not None else "",
                    "checkpoints": checkpoints,
                    "controlnets": controlnets,
                    "has_model": has_model,
                    "has_controlnet": has_controlnet,
                    "workflow_path": str(workflow_path) if has_model and has_controlnet else "",
                }
            except urllib.error.HTTPError as exc:
                result = {"status": "error", "message": f"HTTP {exc.code}"}
            except urllib.error.URLError as exc:
                result = {"status": "error", "message": str(exc.reason)}
            except Exception as exc:
                result = {"status": "error", "message": str(exc)}
            self.signals.comfyui_setup_done.emit(result)

        threading.Thread(target=worker, daemon=True).start()

    def on_comfyui_setup_done(self, result: object) -> None:
        self.comfyui_setup_running = False
        if hasattr(self, "comfyui_setup_button"):
            self.comfyui_setup_button.setEnabled(True)
        if not isinstance(result, dict):
            self.comfyui_status_label.setText(str(result))
            return
        if result.get("status") != "ok":
            self.comfyui_status_label.setText(f"ComfyUI初期設定に失敗しました: {result.get('message', '')}")
            return
        base_dir = str(result.get("base_dir") or "")
        if base_dir:
            self.comfyui_base_dir_edit.setText(base_dir)
        if result.get("has_model") and result.get("has_controlnet"):
            workflow_path = str(result.get("workflow_path") or "")
            self.comfyui_workflow_edit.setText(workflow_path)
            self.detect_comfyui_nodes(update_status=False)
            self.set_combo_by_data(self.comfyui_input_combo, COMFYUI_INPUT_NODE_ID)
            self.set_combo_by_data(self.comfyui_output_combo, COMFYUI_OUTPUT_NODE_ID)
            self.persist_config()
            self.comfyui_status_label.setText(
                f"ComfyUI初期設定が完了しました。\n"
                f"モデル: {COMFYUI_RECOMMENDED_MODEL_NAME}\n"
                f"ControlNet: {COMFYUI_RECOMMENDED_CONTROLNET_NAME}\n"
                f"workflow: {workflow_path}"
            )
        else:
            model_target = self.comfyui_recommended_model_path()
            controlnet_target = self.comfyui_recommended_controlnet_path()
            missing = []
            if not result.get("has_model"):
                missing.append(f"checkpoint: {COMFYUI_RECOMMENDED_MODEL_NAME}\n保存先: {model_target if model_target is not None else 'ComfyUI base directory未検出'}")
            if not result.get("has_controlnet"):
                missing.append(f"ControlNet: {COMFYUI_RECOMMENDED_CONTROLNET_NAME}\n保存先: {controlnet_target if controlnet_target is not None else 'ComfyUI base directory未検出'}")
            self.persist_config()
            self.comfyui_status_label.setText(
                "ComfyUIには接続できましたが、推奨ファイルが不足しています。\n"
                + "\n".join(missing)
                + "\n必要なら「推奨モデル/ControlNetをダウンロード」を押してください。"
            )

    def download_comfyui_recommended_model(self) -> None:
        if self.comfyui_download_running:
            return
        downloads = [
            ("checkpoint", COMFYUI_RECOMMENDED_MODEL_NAME, COMFYUI_RECOMMENDED_MODEL_URL, self.comfyui_recommended_model_path()),
            ("ControlNet", COMFYUI_RECOMMENDED_CONTROLNET_NAME, COMFYUI_RECOMMENDED_CONTROLNET_URL, self.comfyui_recommended_controlnet_path()),
        ]
        pending = [(label, name, url, target) for label, name, url, target in downloads if target is not None and not target.exists()]
        missing_base = any(target is None for _label, _name, _url, target in downloads)
        if missing_base:
            target = None
        else:
            target = pending[0][3] if pending else None
        if target is None:
            if missing_base:
                self.comfyui_status_label.setText("先にComfyUI初期設定を実行し、base directoryを検出してください。")
            else:
                self.comfyui_status_label.setText("推奨モデルとControlNetは既に存在します。")
            return
        label, name, url, target = pending[0]
        self.persist_config()
        self.comfyui_download_running = True
        self.comfyui_download_button.setEnabled(False)
        self.comfyui_status_label.setText(f"推奨{label}をダウンロード中...\n{name}\n保存先: {target}")

        def worker() -> None:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                temp_path = target.with_suffix(target.suffix + ".part")
                request = urllib.request.Request(url, headers={"User-Agent": f"{APP_SHORT_NAME}/{APP_VERSION}"})
                with urllib.request.urlopen(request, timeout=60) as response, temp_path.open("wb") as output:
                    total = int(response.headers.get("Content-Length") or 0)
                    downloaded = 0
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                        downloaded += len(chunk)
                        self.signals.comfyui_download_progress.emit({"label": label, "downloaded": downloaded, "total": total})
                temp_path.replace(target)
                self.signals.comfyui_download_done.emit({"status": "ok", "label": label, "name": name, "path": str(target)})
            except Exception as exc:
                self.signals.comfyui_download_done.emit({"status": "error", "message": str(exc)})

        threading.Thread(target=worker, daemon=True).start()

    def on_comfyui_download_progress(self, result: object) -> None:
        if not isinstance(result, dict):
            return
        label = str(result.get("label") or "モデル")
        downloaded = int(result.get("downloaded") or 0)
        total = int(result.get("total") or 0)
        if total > 0:
            percent = downloaded * 100 / total
            self.comfyui_status_label.setText(f"推奨{label}をダウンロード中... {percent:.1f}% ({downloaded / 1024**3:.2f} / {total / 1024**3:.2f} GiB)")
        else:
            self.comfyui_status_label.setText(f"推奨{label}をダウンロード中... {downloaded / 1024**3:.2f} GiB")

    def on_comfyui_download_done(self, result: object) -> None:
        self.comfyui_download_running = False
        if hasattr(self, "comfyui_download_button"):
            self.comfyui_download_button.setEnabled(True)
        if not isinstance(result, dict):
            self.comfyui_status_label.setText(str(result))
            return
        if result.get("status") == "ok":
            self.comfyui_status_label.setText(f"推奨{result.get('label', 'モデル')}を保存しました: {result.get('path')}\n不足が残っている場合は、続けてダウンロードを押してください。\n最後にComfyUI初期設定をもう一度実行してください。")
        else:
            self.comfyui_status_label.setText(f"推奨ファイルのダウンロードに失敗しました: {result.get('message', '')}")

    def update_novelai_generate_button_text(self) -> None:
        if hasattr(self, "novelai_generate_button"):
            if self.novelai_continuous_generation_stopping:
                text = "停止中"
                enabled = False
            elif self.novelai_continuous_generation_enabled:
                text = "連続生成中"
                enabled = True
            elif self.novelai_generation_running:
                text = "生成中"
                enabled = False
            else:
                text = "生成"
                enabled = self.novelai_max_batch_count() > 0
            self.novelai_generate_button.setText(self.tr_ui(text))
            self.novelai_generate_button.setEnabled(enabled)

    def update_novelai_continuous_delay_visibility(self) -> None:
        if hasattr(self, "novelai_continuous_delay_widget"):
            self.novelai_continuous_delay_widget.setVisible(bool(self.novelai_continuous_generation_enabled))

    def novelai_continuous_delay_ms(self) -> int:
        if hasattr(self, "novelai_continuous_delay_spin"):
            seconds = self.novelai_continuous_delay_spin.value()
        else:
            seconds = self.config_data.novelai_continuous_delay_seconds
        return max(100, int(round(float(seconds) * 1000)))

    def set_novelai_continuous_generation_enabled(self, enabled: bool) -> None:
        self.novelai_continuous_generation_enabled = bool(enabled)
        if enabled:
            self.novelai_continuous_generation_stopping = False
        else:
            self.novelai_continuous_delay_timer.stop()
        self.update_novelai_generate_button_text()
        self.update_novelai_continuous_delay_visibility()

    def request_stop_novelai_continuous_generation(self) -> None:
        self.novelai_continuous_delay_timer.stop()
        self.novelai_continuous_generation_enabled = False
        self.novelai_continuous_generation_stopping = bool(self.novelai_generation_running)
        self.update_novelai_generate_button_text()
        self.update_novelai_continuous_delay_visibility()
        if self.novelai_generation_running:
            self.novelai_status_label.setText("連続生成を停止します。実行中の生成は完了まで続きます。")
        else:
            self.novelai_continuous_generation_stopping = False
            self.update_novelai_generate_button_text()

    def toggle_novelai_continuous_generation(self) -> None:
        if self.novelai_continuous_generation_enabled:
            self.request_stop_novelai_continuous_generation()
            return
        self.set_novelai_continuous_generation_enabled(not self.novelai_continuous_generation_enabled)
        if self.novelai_continuous_generation_enabled:
            self.novelai_status_label.setText("連続生成を開始しました。停止するには生成ボタンをもう一度ダブルクリックしてください。連続生成中は常にランダムシードで生成します。")
            if not self.novelai_generation_running:
                self.generate_novelai_images()
        else:
            self.request_stop_novelai_continuous_generation()

    def on_novelai_generate_button_clicked(self) -> None:
        if self.novelai_continuous_generation_enabled:
            self.request_stop_novelai_continuous_generation()
            return
        if self.novelai_generation_running or self.novelai_continuous_generation_stopping:
            return
        self.novelai_generate_click_pending = True
        QTimer.singleShot(QApplication.doubleClickInterval(), self.run_pending_novelai_generate_click)

    def run_pending_novelai_generate_click(self) -> None:
        if not self.novelai_generate_click_pending:
            return
        self.novelai_generate_click_pending = False
        if self.novelai_generation_running or self.novelai_continuous_generation_enabled or self.novelai_continuous_generation_stopping:
            return
        self.generate_novelai_images()

    def continue_novelai_generation_if_needed(self) -> None:
        if (
            self.novelai_continuous_generation_enabled
            and not self.novelai_continuous_generation_stopping
            and not getattr(self, "closing", False)
        ):
            self.novelai_continuous_delay_timer.start(self.novelai_continuous_delay_ms())
        else:
            self.set_novelai_continuous_generation_enabled(False)
            self.novelai_continuous_generation_stopping = False
            self.update_novelai_generate_button_text()

    def run_next_novelai_continuous_generation(self) -> None:
        if (
            not self.novelai_continuous_generation_enabled
            or self.novelai_continuous_generation_stopping
            or self.novelai_generation_running
            or getattr(self, "closing", False)
        ):
            return
        self.generate_novelai_images()

    def generate_novelai_images(self) -> None:
        if self.novelai_generation_running:
            self.novelai_status_label.setText("NovelAI生成は実行中です。")
            return
        maximum_count = self.novelai_max_batch_count()
        if maximum_count == 0:
            self.set_novelai_continuous_generation_enabled(False)
            self.novelai_continuous_generation_stopping = False
            self.update_novelai_generate_button_text()
            self.novelai_status_label.setText("現在の解像度はNovelAIの対応上限を超えています。")
            return
        token = self.novelai_token_edit.text().strip()
        if not token:
            self.set_novelai_continuous_generation_enabled(False)
            self.novelai_continuous_generation_stopping = False
            self.update_novelai_generate_button_text()
            QMessageBox.information(self, APP_NAME, "NovelAI Persistent API Tokenを入力してください。")
            return
        prompt = self.novelai_prompt_text()
        if not prompt:
            self.set_novelai_continuous_generation_enabled(False)
            self.novelai_continuous_generation_stopping = False
            self.update_novelai_generate_button_text()
            QMessageBox.information(self, APP_NAME, "Promptを入力してください。")
            return
        selected_count = self.novelai_number_of_images()
        if selected_count > maximum_count:
            self.set_novelai_continuous_generation_enabled(False)
            self.novelai_continuous_generation_stopping = False
            self.update_novelai_generate_button_text()
            message = (
                f"現在の解像度では1回に最大{maximum_count}枚まで生成できます。\n"
                f"生成枚数を{maximum_count}枚以下に変更してください。"
            )
            QMessageBox.information(self, APP_NAME, message)
            return
        output_dir = Path(self.novelai_output_dir_edit.text().strip() or str(DEFAULT_NOVELAI_GENERATED_DIR))
        task = {
            "api_token": token,
            "output_dir": output_dir,
            "output_name_template": self.novelai_filename_template_edit.text().strip() or "{seed}",
            "request": self.current_novelai_request(),
            "random_seed": bool(self.novelai_continuous_generation_enabled or self.novelai_random_seed_check.isChecked()),
            "save_metadata_json": self.novelai_metadata_check.isChecked(),
            "auto_open": self.novelai_auto_open_check.isChecked(),
            "auto_upscale": self.novelai_auto_upscale_check.isChecked(),
            "is_opus": self.novelai_opus_check.isChecked(),
        }
        self.persist_config()
        self.novelai_generation_running = True
        self.update_novelai_generate_button_text()
        self.novelai_status_label.setText("NovelAI生成キューへ追加しました。")
        self.novelai_queue.put(task)

    def _novelai_worker_loop(self) -> None:
        while True:
            task = self.novelai_queue.get()
            if task is None or getattr(self, "closing", False):
                return
            self.signals.novelai_generation_started.emit(str(task.get("output_dir", "")))
            try:
                result = self.run_novelai_generation(task)
            except Exception as exc:
                result = {"ok": False, "message": str(exc), "paths": []}
            self.signals.novelai_generation_done.emit(result)

    def run_novelai_generation(self, task: dict[str, object]) -> dict[str, object]:
        output_dir = Path(task["output_dir"])
        timestamp = time.localtime()
        request = dict(task["request"])  # type: ignore[arg-type]
        random_seed_enabled = bool(task.get("random_seed", True))
        save_metadata_json = bool(task.get("save_metadata_json", True))
        generated_paths: list[Path] = []
        started = time.perf_counter()
        maximum_count = self.novelai_max_batch_count(int(request.get("width", 832)), int(request.get("height", 1216)))
        requested_count = int(request.get("n_samples", 1))
        if requested_count > maximum_count:
            if maximum_count > 0:
                raise ValueError(f"現在の解像度では1回に最大{maximum_count}枚まで生成できます。")
            raise ValueError("現在の解像度はNovelAIの対応上限を超えています。")
        adapter = NovelAIClientAdapter(str(task.get("api_token", "")))
        seed = random.randint(0, MAX_NOVELAI_SEED) if random_seed_enabled else int(request.get("seed", 0)) % (MAX_NOVELAI_SEED + 1)
        request = {**request, "seed": seed, "n_samples": max(1, min(8, int(request.get("n_samples", 1))))}
        output_dir.mkdir(parents=True, exist_ok=True)
        output_name_template = str(task.get("output_name_template", "{seed}"))
        self.unique_novelai_output_path(output_dir, timestamp, seed, output_name_template)
        images = adapter.generate_images(request)
        for index, image in enumerate(images, start=1):
            image_seed = adapter.image_seed(image)
            if image_seed is None:
                image_seed = (seed + index - 1) % (MAX_NOVELAI_SEED + 1)
            output_path = self.unique_novelai_output_path(
                output_dir,
                timestamp,
                image_seed,
                output_name_template,
                index if len(images) > 1 else None,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(output_path))
            generated_paths.append(output_path)
            if save_metadata_json:
                image_request = {**request, "seed": image_seed, "n_samples": 1}
                metadata = {
                    "source": "NovelAI",
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "request": image_request,
                    "batch_request": request,
                    "image_index": index,
                    "seed": image_seed,
                    "estimated_anlas": adapter.estimate_anlas(request, bool(task.get("is_opus", False))),
                }
                atomic_write_text(
                    output_path.with_suffix(output_path.suffix + ".json"),
                    json.dumps(metadata, ensure_ascii=False, indent=2),
                )
        return {
            "ok": True,
            "paths": generated_paths,
            "seed": seed,
            "auto_open": bool(task.get("auto_open", True)),
            "auto_upscale": bool(task.get("auto_upscale", True)),
            "elapsed_ms": (time.perf_counter() - started) * 1000,
        }

    def unique_novelai_output_path(self, output_dir: Path, timestamp, seed: int, filename_template: str = "{seed}", image_index: int | None = None) -> Path:
        raw_template = str(filename_template or "{seed}")
        normalized = raw_template.replace("\\", "/")
        if normalized.startswith("/") or any(re.match(r"^[A-Za-z]:", part) for part in normalized.split("/")):
            raise ValueError("保存名には絶対パスやドライブ指定を使用できません。")
        if normalized.endswith("/"):
            normalized += "{seed}"
        raw_parts = [part for part in normalized.split("/") if part]
        if any(part in {".", ".."} for part in raw_parts):
            raise ValueError("保存名には . または .. を使用できません。")
        expanded_parts = [self.expand_novelai_name_template(part, timestamp, seed) for part in raw_parts]
        safe_parts = [self.sanitize_novelai_path_part(part) for part in expanded_parts]
        if not safe_parts:
            safe_parts = [str(seed)]
        base = safe_parts[-1]
        if base.casefold().endswith(".png"):
            base = base[:-4]
        if not base:
            base = str(seed)
        if image_index is not None:
            base = f"{base}_{image_index:02d}"
        output_root = output_dir.resolve()
        parent = output_dir.joinpath(*safe_parts[:-1])
        path = parent / f"{base}.png"
        if not path.resolve().is_relative_to(output_root):
            raise ValueError("保存名が保存先フォルダの外を指しています。")
        suffix = 1
        while path.exists():
            path = parent / f"{base}_{suffix}.png"
            suffix += 1
        return path

    def sanitize_novelai_path_part(self, value: str) -> str:
        part = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or ""))
        part = re.sub(r"[ .]+$", lambda match: "_" * len(match.group(0)), part)
        if not part:
            return "_"
        reserved_name = part.split(".", 1)[0].upper()
        reserved_names = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
        return f"_{part}" if reserved_name in reserved_names else part

    def expand_novelai_name_template(self, template: str, timestamp, seed: int) -> str:
        values = {
            "YYYY": time.strftime("%Y", timestamp),
            "MM": time.strftime("%m", timestamp),
            "DD": time.strftime("%d", timestamp),
            "HH": time.strftime("%H", timestamp),
            "mm": time.strftime("%M", timestamp),
            "ss": time.strftime("%S", timestamp),
            "date": time.strftime("%Y%m%d", timestamp),
            "time": time.strftime("%H%M%S", timestamp),
            "seed": str(seed),
        }
        base = str(template or "")
        for name, value in values.items():
            base = base.replace(f"{{{name}}}", value)
        return base

    def on_novelai_generation_started(self, output_dir: str) -> None:
        self.append_log_if_visible(f"NovelAI generation started: {output_dir}")
        if hasattr(self, "novelai_status_label"):
            self.novelai_status_label.setText(f"NovelAIで生成中: {output_dir}")

    def on_novelai_generation_done(self, result: object) -> None:
        self.novelai_generation_running = False
        if not isinstance(result, dict) or not result.get("ok"):
            self.set_novelai_continuous_generation_enabled(False)
            self.novelai_continuous_generation_stopping = False
            self.update_novelai_generate_button_text()
            message = str(result.get("message", "unknown error")) if isinstance(result, dict) else "unknown error"
            self.append_log_if_visible(f"NovelAI generation failed: {message}")
            if hasattr(self, "novelai_status_label"):
                self.novelai_status_label.setText(f"NovelAI生成に失敗しました: {message}")
            return
        paths = [Path(path) for path in result.get("paths", [])]
        if "seed" in result:
            self.set_novelai_seed_value(result.get("seed"))
            self.persist_config()
        if not paths:
            if hasattr(self, "novelai_status_label"):
                self.novelai_status_label.setText("NovelAI生成は完了しましたが、画像がありません。")
            self.continue_novelai_generation_if_needed()
            return
        self.record_profile("NovelAI生成", float(result.get("elapsed_ms", 0.0)))
        self.append_log_if_visible(f"NovelAI generation done: {len(paths)} image(s)")
        if hasattr(self, "novelai_status_label"):
            self.novelai_status_label.setText(f"NovelAI生成完了: {len(paths)}枚")
        if result.get("auto_open", True):
            self.open_path_deferred(paths[-1])
        else:
            self.refresh_current_folder_after_novelai_generation(paths)
        if result.get("auto_upscale", True):
            QTimer.singleShot(200, lambda generated=paths: self.enqueue_generated_upscales(generated))
        self.continue_novelai_generation_if_needed()

    def refresh_current_folder_after_novelai_generation(self, paths: list[Path]) -> None:
        if self.archive_mode_active() or not self.image_paths or self.current_index < 0:
            return
        try:
            current_path = self.image_paths[self.current_index].resolve()
            current_folder = self.current_real_folder()
            generated_folders = {path.resolve().parent for path in paths}
        except OSError:
            return
        if current_folder is None or current_folder.resolve() not in generated_folders:
            return
        self.folder_list_loading = True
        self.deferred_page_steps = 0
        self.collect_folder_images_async(current_folder, current_path)

    def enqueue_generated_upscales(self, paths: list[Path]) -> None:
        for index, path in enumerate(paths):
            if path.exists() and self.is_image(path):
                self.enqueue_realcugan(path, front=index == 0, force=False, check_existing=True, check_skip=True)
        self.update_prefetch_progress_bars()

    def current_colorize_input_path(self) -> Path | None:
        if not self.image_paths or self.current_index < 0 or self.current_index >= len(self.image_paths):
            return None
        path = self.image_paths[self.current_index]
        return path if path.is_file() else None

    def colorized_output_dir(self, source: Path) -> Path:
        if self.archive_mode_active():
            return APP_DIR / "RAIV_colorized"
        return source.parent / "RAIV_colorized"

    def colorized_output_path(self, source: Path) -> Path:
        return self.colorized_output_dir(source) / f"{source.stem}_comfyui.png"

    def has_colorized_result(self, source: Path) -> bool:
        if not source.is_file():
            return False
        session_path = self.colorized_session_paths.get(self.normalized_path(source))
        if session_path is not None and session_path.exists():
            return True
        path = self.colorized_output_path(source)
        return path.exists()

    def existing_colorized_path(self, source: Path) -> Path | None:
        if not self.use_colorized_cache_check.isChecked() or not self.has_colorized_result(source):
            return None
        path = self.colorized_output_path(source)
        return path if path.exists() else None

    def display_source_path(self, source: Path) -> Path:
        session_path = self.colorized_session_paths.get(self.normalized_path(source))
        if session_path is not None and session_path.exists():
            return session_path
        return self.existing_colorized_path(source) or source

    def colorize_ready(self) -> tuple[bool, str]:
        workflow_path = Path(self.comfyui_workflow_edit.text().strip())
        if not workflow_path.is_file():
            return False, "workflow JSONを指定してください。"
        input_node = str(self.comfyui_input_combo.currentData() or "")
        output_node = str(self.comfyui_output_combo.currentData() or "")
        if not input_node or not output_node:
            return False, "入力画像ノードと出力画像ノードを指定してください。"
        return True, ""

    def colorize_current_image_with_comfyui(self) -> None:
        source = self.current_colorize_input_path()
        if source is None:
            self.comfyui_status_label.setText("彩色する画像がありません。")
            return
        ready, message = self.colorize_ready()
        if not ready:
            self.comfyui_status_label.setText(message)
            return
        self.persist_config()
        self.enqueue_colorize(source, front=True, force=True, show_result=True)
        self.comfyui_status_label.setText(f"ComfyUI彩色キューへ追加: {source.name}")

    def enqueue_colorize(self, path: Path, front: bool = False, force: bool = False, show_result: bool = False) -> None:
        path = self.normalized_path(path)
        if not force and self.has_colorized_result(path):
            self.colorize_done_paths.add(path)
            return
        ready, message = self.colorize_ready()
        if not ready:
            if front:
                self.comfyui_status_label.setText(message)
            return
        if path in self.colorize_processing_paths:
            return
        if path in self.colorize_queued_paths:
            if front:
                self.promote_colorize_item(path)
            return
        task = {
            "source": path,
            "force": force,
            "api_url": self.comfyui_api_base(),
            "workflow_path": Path(self.comfyui_workflow_edit.text().strip()),
            "input_node": str(self.comfyui_input_combo.currentData() or ""),
            "output_node": str(self.comfyui_output_combo.currentData() or ""),
            "output_dir": self.colorized_output_dir(path),
            "save_to_folder": self.save_colorized_check.isChecked(),
            "positive_prompt": self.colorize_positive_edit.toPlainText().strip() or DEFAULT_COLORIZE_POSITIVE_PROMPT,
            "negative_prompt": self.colorize_negative_edit.toPlainText().strip() or DEFAULT_COLORIZE_NEGATIVE_PROMPT,
            "denoise": self.colorize_denoise_spin.value(),
            "controlnet_strength": self.colorize_controlnet_strength_spin.value(),
            "controlnet_end": self.colorize_controlnet_end_spin.value(),
            "saturation_boost": self.colorize_saturation_spin.value(),
            "luminance_preserve": self.colorize_luminance_spin.value(),
            "show_result": show_result,
        }
        self.colorize_queued_paths.add(path)
        if front:
            with self.colorize_queue.mutex:
                self.colorize_queue.queue.appendleft(task)
                self.colorize_queue.unfinished_tasks += 1
                self.colorize_queue.not_empty.notify()
        else:
            self.colorize_queue.put(task)
        self.update_prefetch_progress_bars()

    def promote_colorize_item(self, path: Path) -> None:
        path = self.normalized_path(path)
        with self.colorize_queue.mutex:
            items = [item for item in self.colorize_queue.queue if item is not None and item.get("source") != path]
            current = [item for item in self.colorize_queue.queue if item is not None and item.get("source") == path]
            self.colorize_queue.queue.clear()
            self.colorize_queue.queue.extend(items)
            if current:
                self.colorize_queue.queue.appendleft(current[0])
            self.colorize_queue.not_empty.notify()

    def reorder_colorize_queue(self, priority_paths: list[Path]) -> None:
        priority = [self.normalized_path(path) for path in priority_paths]
        priority_rank = {path: index for index, path in enumerate(priority)}
        with self.colorize_queue.mutex:
            items = [item for item in self.colorize_queue.queue if item is not None]
            if not items:
                return
            items.sort(key=lambda item: priority_rank.get(self.normalized_path(Path(item["source"])), len(priority_rank) + 1))
            self.colorize_queue.queue.clear()
            self.colorize_queue.queue.extend(items)
            self.colorize_queue.not_empty.notify()

    def _colorize_worker_loop(self) -> None:
        while True:
            task = self.colorize_queue.get()
            if task is None or getattr(self, "closing", False):
                return
            source = self.normalized_path(Path(task["source"]))
            force = bool(task.get("force"))
            self.colorize_queued_paths.discard(source)
            if not force and self.has_colorized_result(source):
                self.colorize_done_paths.add(source)
                continue
            self.colorize_processing_paths.add(source)
            self.signals.comfyui_colorize_started.emit(str(source))
            try:
                result = self.run_comfyui_colorize(
                    str(task["api_url"]),
                    source,
                    Path(task["workflow_path"]),
                    str(task["input_node"]),
                    str(task["output_node"]),
                    Path(task["output_dir"]),
                    bool(task.get("save_to_folder", True)),
                    str(task.get("positive_prompt") or DEFAULT_COLORIZE_POSITIVE_PROMPT),
                    str(task.get("negative_prompt") or DEFAULT_COLORIZE_NEGATIVE_PROMPT),
                    float(task.get("denoise") or 0.62),
                    float(task.get("controlnet_strength") or 0.65),
                    float(task.get("controlnet_end") or 0.65),
                    float(task.get("saturation_boost") or 1.35),
                    float(task.get("luminance_preserve") or 0.72),
                )
                result["show_result"] = bool(task.get("show_result"))
            except urllib.error.HTTPError as exc:
                result = {"status": "error", "source": str(source), "message": f"HTTP {exc.code}"}
            except urllib.error.URLError as exc:
                result = {"status": "error", "source": str(source), "message": str(exc.reason)}
            except Exception as exc:
                result = {"status": "error", "source": str(source), "message": str(exc)}
            self.colorize_processing_paths.discard(source)
            self.signals.comfyui_colorize_done.emit(result)

    def run_comfyui_colorize(
        self,
        api_url: str,
        source: Path,
        workflow_path: Path,
        input_node: str,
        output_node: str,
        output_dir: Path,
        save_to_folder: bool,
        positive_prompt: str,
        negative_prompt: str,
        denoise: float,
        controlnet_strength: float,
        controlnet_end: float,
        saturation_boost: float,
        luminance_preserve: float,
    ) -> dict[str, object]:
        workflow = load_comfyui_api_workflow(workflow_path)
        if input_node not in workflow:
            raise ValueError("input node was not found in workflow")
        if output_node not in workflow:
            raise ValueError("output node was not found in workflow")
        uploaded = comfyui_upload_image(api_url, source)
        image_name = str(uploaded.get("name") or source.name)
        workflow[input_node].setdefault("inputs", {})["image"] = image_name
        self.apply_colorize_settings_to_workflow(
            workflow,
            positive_prompt,
            negative_prompt,
            denoise,
            controlnet_strength,
            controlnet_end,
        )
        output_inputs = workflow[output_node].setdefault("inputs", {})
        if str(workflow[output_node].get("class_type") or "") == "SaveImage":
            workflow[output_node]["class_type"] = "PreviewImage"
            output_inputs.pop("filename_prefix", None)
        prompt_response = comfyui_post_json(api_url, "/prompt", {"prompt": workflow, "client_id": uuid.uuid4().hex}, timeout=30)
        prompt_id = str(prompt_response.get("prompt_id") or "")
        if not prompt_id:
            raise ValueError("ComfyUI did not return prompt_id")
        deadline = time.time() + 900
        history_entry = None
        while time.time() < deadline:
            history = comfyui_get_json(api_url, f"/history/{prompt_id}", timeout=30)
            history_entry = history.get(prompt_id) if isinstance(history, dict) else None
            if history_entry:
                status = history_entry.get("status", {}) if isinstance(history_entry, dict) else {}
                if isinstance(status, dict) and status.get("status_str") == "error":
                    raise RuntimeError(self.comfyui_history_error_message(status))
                if isinstance(status, dict) and status.get("completed") and not history_entry.get("outputs"):
                    raise RuntimeError(self.comfyui_history_error_message(status))
            if history_entry and history_entry.get("outputs"):
                break
            time.sleep(0.7)
        if not history_entry or not history_entry.get("outputs"):
            raise TimeoutError("ComfyUI generation did not finish")
        outputs = history_entry.get("outputs", {})
        images = []
        if isinstance(outputs, dict):
            selected = outputs.get(output_node)
            if isinstance(selected, dict) and isinstance(selected.get("images"), list):
                images = selected["images"]
            if not images:
                for output in outputs.values():
                    if isinstance(output, dict) and isinstance(output.get("images"), list):
                        images = output["images"]
                        break
        if not images:
            raise ValueError("ComfyUI did not return an output image")
        image_info = images[0]
        filename = str(image_info.get("filename") or "")
        subfolder = str(image_info.get("subfolder") or "")
        file_type = str(image_info.get("type") or "output")
        query = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": file_type})
        with urllib.request.urlopen(comfyui_api_url(api_url, f"/view?{query}"), timeout=60) as response:
            image_bytes = response.read()
        image_bytes = preserve_original_luminance(
            source,
            image_bytes,
            saturation_boost=saturation_boost,
            luminance_preserve=luminance_preserve,
        )
        if save_to_folder:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.colorized_output_path(source)
        else:
            fd, text_path = tempfile.mkstemp(prefix=f"{source.stem}_comfyui_", suffix=".png", dir=self.process_temp_dir)
            os.close(fd)
            output_path = Path(text_path)
        atomic_write_bytes(output_path, image_bytes)
        return {"status": "ok", "source": str(source), "path": str(output_path), "saved": save_to_folder}

    def apply_colorize_settings_to_workflow(
        self,
        workflow: dict[str, dict],
        positive_prompt: str,
        negative_prompt: str,
        denoise: float,
        controlnet_strength: float,
        controlnet_end: float,
    ) -> None:
        for node_id, node in workflow.items():
            class_type = str(node.get("class_type") or "")
            inputs = node.setdefault("inputs", {})
            title = str(node.get("_meta", {}).get("title") or "")
            if class_type == "CLIPTextEncode":
                if "Negative" in title or node_id == "3":
                    inputs["text"] = negative_prompt
                elif "Positive" in title or node_id == "2":
                    inputs["text"] = positive_prompt
            elif class_type == "KSampler":
                inputs["denoise"] = max(0.0, min(1.0, float(denoise)))
                inputs["steps"] = 28
                inputs["cfg"] = 5.2
                inputs["sampler_name"] = "dpmpp_2m_sde"
                inputs["scheduler"] = "karras"
            elif class_type == "ControlNetApplyAdvanced":
                inputs["strength"] = max(0.0, min(2.0, float(controlnet_strength)))
                inputs["end_percent"] = max(0.0, min(1.0, float(controlnet_end)))

    def comfyui_history_error_message(self, status: dict) -> str:
        for message in status.get("messages", []):
            if not isinstance(message, list) or len(message) < 2 or message[0] != "execution_error":
                continue
            detail = message[1] if isinstance(message[1], dict) else {}
            node_type = str(detail.get("node_type") or "")
            exception = str(detail.get("exception_message") or detail.get("exception_type") or "")
            if node_type or exception:
                return f"ComfyUI error at {node_type}: {exception}".strip()
        return "ComfyUI generation failed"

    def on_comfyui_colorize_started(self, path_text: str) -> None:
        self.comfyui_colorize_running = True
        if hasattr(self, "comfyui_colorize_button"):
            self.comfyui_colorize_button.setEnabled(False)
        path = Path(path_text)
        self.append_log_if_visible(f"ComfyUI colorize started: {self.display_name(path)}")
        self.comfyui_status_label.setText(f"ComfyUIで彩色中: {path.name}")
        self.update_prefetch_progress_bars()

    def on_comfyui_colorize_done(self, result: object) -> None:
        self.comfyui_colorize_running = bool(self.colorize_processing_paths or self.colorize_queued_paths)
        if hasattr(self, "comfyui_colorize_button"):
            self.comfyui_colorize_button.setEnabled(not self.comfyui_colorize_running)
        if not isinstance(result, dict):
            self.comfyui_status_label.setText(str(result))
            return
        if result.get("status") == "ok":
            source_text = str(result.get("source") or "")
            source = Path(source_text) if source_text else None
            path = Path(str(result.get("path") or ""))
            if source is not None:
                normalized_source = self.normalized_path(source)
                self.colorized_session_paths[normalized_source] = path
                self.colorize_done_paths.add(normalized_source)
                self.processed_cache.pop(self.processing_key(normalized_source), None)
                self.original_cache.pop(normalized_source, None)
                self.original_cache.pop(self.normalized_path(path), None)
                self.image_height_cache.pop(normalized_source, None)
                self.image_height_cache.pop(self.normalized_path(path), None)
                self.viewer.pixmap_cache.clear()
                self.viewer.clear_pixmap_prefetch_state()
                colorized = load_image(path, self.config_data.hdr_tonemap_brightness)
                if not colorized.isNull():
                    self.original_cache[self.normalized_path(path)] = colorized
                    self.remember_image_height(path, colorized.height())
                if self.current_index >= 0 and normalized_source in {
                    self.normalized_path(self.image_paths[self.current_index]),
                    self.normalized_path(self.image_paths[self.secondary_page_index()]) if self.secondary_page_index() is not None else Path(),
                }:
                    self.display_current_image(preserve_view=False)
            self.append_log_if_visible(f"ComfyUI colorize done: {self.display_name(source) if source is not None else path.name}")
            if result.get("saved"):
                self.comfyui_status_label.setText(f"彩色結果を保存しました: {path}")
            else:
                self.comfyui_status_label.setText(f"彩色結果を一時表示しています: {path}")
        else:
            source_text = str(result.get("source") or "")
            source = Path(source_text) if source_text else None
            if source is not None:
                self.colorize_done_paths.discard(self.normalized_path(source))
            self.append_log_if_visible(f"ComfyUI colorize failed: {self.display_name(source) if source is not None else ''} {result.get('message', '')}")
            self.comfyui_status_label.setText(f"ComfyUI彩色に失敗しました: {result.get('message', '')}")
        self.update_prefetch_progress_bars()

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
            self.config_data.side_panel_visible = True
            self.attach_side_panel_to_splitter(visible=True)
            self.request_pinned_side_panel_repair()
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

    def schedule_persist_config(self, delay_ms: int = CONFIG_SAVE_DEBOUNCE_MS) -> None:
        if getattr(self, "initializing", False) or getattr(self, "closing", False):
            return
        self.config_save_timer.start(max(0, int(delay_ms)))

    def persist_config(self, log: bool = False) -> None:
        if getattr(self, "initializing", False):
            return
        if self.config_save_timer.isActive():
            self.config_save_timer.stop()
        self.save_active_command_template()
        self.config_data.engine = self.current_engine()
        self.config_data.command_template = self.config_data.realcugan_command_template
        self.save_engine_controls(self.current_engine())
        self.config_data.tile = self.current_tile_size()
        self.config_data.realcugan_prefetch_count = self.realcugan_prefetch_spin.value()
        self.config_data.save_colorized_to_folder = self.save_colorized_check.isChecked()
        self.config_data.use_colorized_folder_cache = self.use_colorized_cache_check.isChecked()
        self.config_data.colorize_prefetch_enabled = self.colorize_prefetch_check.isChecked()
        self.config_data.colorize_prefetch_count = self.colorize_prefetch_spin.value()
        self.config_data.viewer_prefetch_count = self.viewer_prefetch_spin.value()
        if not self.archive_mode_active():
            self.config_data.save_upscaled_to_scale_folder = self.save_scale_check.isChecked()
            self.config_data.use_scale_folder_cache = self.use_scale_cache_check.isChecked()
        self.config_data.skip_realcugan_for_tall_images = self.skip_tall_check.isChecked()
        self.config_data.skip_realcugan_height_threshold = self.skip_height_spin.value()
        self.config_data.auto_realcugan_scale = self.auto_scale_check.isChecked()
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
        self.config_data.display_brightness = self.display_brightness_value()
        self.config_data.display_contrast = self.display_contrast_value()
        self.config_data.display_gamma = self.display_gamma_value()
        self.config_data.display_sharpness = self.display_sharpness_value()
        self.config_data.hdr_tonemap_brightness = self.hdr_tonemap_brightness_slider.value() / 100.0
        self.config_data.page_scroll_interval_ms = self.page_interval_spin.value()
        self.config_data.wrap_page_navigation = self.wrap_page_check.isChecked()
        self.config_data.preserve_view_on_page_navigation = self.preserve_view_check.isChecked()
        self.config_data.refit_view_on_rotation = self.refit_rotation_check.isChecked()
        self.config_data.invert_page_position_slider = self.invert_page_position_check.isChecked()
        self.config_data.horizontal_wheel_navigation = self.horizontal_wheel_check.isChecked()
        self.config_data.horizontal_wheel_inverted = self.horizontal_wheel_invert_check.isChecked()
        self.config_data.hide_cursor_in_fullscreen = self.hide_cursor_fullscreen_check.isChecked()
        self.config_data.show_log_panel = self.show_log_check.isChecked()
        self.config_data.show_profile_panel = self.show_profile_check.isChecked()
        if hasattr(self, "language_combo"):
            self.config_data.ui_language = self.language_combo.currentData() or "ja"
        if hasattr(self, "theme_combo"):
            self.config_data.ui_theme = self.theme_combo.currentData() or THEME_SYSTEM
        self.config_data.thumbnail_enabled = self.thumbnail_enabled_check.isChecked()
        self.config_data.thumbnail_pinned = self.thumbnail_pinned_check.isChecked()
        self.config_data.thumbnail_height = self.clamped_thumbnail_height()
        self.config_data.thumbnail_size = self.thumbnail_icon_size()
        self.config_data.single_instance_enabled = self.single_instance_check.isChecked()
        self.config_data.restore_last_image_on_start = self.restore_last_image_check.isChecked()
        self.config_data.remember_last_image_per_folder = self.folder_history_check.isChecked()
        self.config_data.folder_history_limit = self.folder_history_limit_spin.value()
        self.config_data.confirm_delete_current_image = self.confirm_delete_check.isChecked()
        self.config_data.delete_processed_with_source = self.delete_processed_check.isChecked()
        self.config_data.hide_colorize_tab = self.hide_colorize_tab_check.isChecked()
        self.config_data.hide_novelai_tab = self.hide_novelai_tab_check.isChecked()
        self.config_data.hide_keyconfig_tab = self.hide_keyconfig_tab_check.isChecked()
        if hasattr(self, "comfyui_api_edit"):
            self.config_data.comfyui_api_url = self.comfyui_api_edit.text().strip() or DEFAULT_COMFYUI_API_URL
            self.config_data.comfyui_base_dir = self.comfyui_base_dir_edit.text().strip()
            self.config_data.comfyui_workflow_path = self.comfyui_workflow_edit.text().strip()
            self.config_data.comfyui_input_node_id = str(self.comfyui_input_combo.currentData() or "")
            self.config_data.comfyui_output_node_id = str(self.comfyui_output_combo.currentData() or "")
            self.config_data.colorize_denoise = self.colorize_denoise_spin.value()
            self.config_data.colorize_controlnet_strength = self.colorize_controlnet_strength_spin.value()
            self.config_data.colorize_controlnet_end = self.colorize_controlnet_end_spin.value()
            self.config_data.colorize_saturation_boost = self.colorize_saturation_spin.value()
            self.config_data.colorize_luminance_preserve = self.colorize_luminance_spin.value()
            self.config_data.colorize_positive_prompt = self.colorize_positive_edit.toPlainText().strip() or DEFAULT_COLORIZE_POSITIVE_PROMPT
            self.config_data.colorize_negative_prompt = self.colorize_negative_edit.toPlainText().strip() or DEFAULT_COLORIZE_NEGATIVE_PROMPT
        if hasattr(self, "novelai_token_edit"):
            token = self.novelai_token_edit.text().strip()
            if token != getattr(self, "saved_novelai_api_token", ""):
                try:
                    save_novelai_api_token(token)
                    self.saved_novelai_api_token = token
                except Exception as exc:
                    self.append_log_if_visible(f"Failed to save NovelAI token with DPAPI: {exc}")
            self.config_data.novelai_api_token = ""
            self.config_data.novelai_output_dir = self.novelai_output_dir_edit.text().strip() or str(DEFAULT_NOVELAI_GENERATED_DIR)
            self.config_data.novelai_output_name_mode = self.novelai_filename_combo.currentData() or "custom"
            self.config_data.novelai_output_name_template = self.novelai_filename_template_edit.text().strip() or "{seed}"
            self.config_data.novelai_prompt = self.novelai_prompt_storage_text()
            self.config_data.novelai_negative_prompt = self.novelai_negative_prompt_storage_text()
            self.config_data.novelai_split_prompts = self.novelai_split_prompts_check.isChecked()
            self.config_data.novelai_show_reconstructed_prompts = self.novelai_show_reconstructed_prompts_check.isChecked()
            self.config_data.novelai_add_prompt_items_at_top = self.novelai_add_prompt_items_at_top_check.isChecked()
            self.config_data.novelai_prompt_items = self.novelai_prompt_list_edit.to_items()
            self.config_data.novelai_negative_prompt_items = self.novelai_negative_list_edit.to_items()
            self.config_data.novelai_prompt_editor_height = self.clamp_novelai_prompt_editor_height(self.config_data.novelai_prompt_editor_height)
            self.config_data.novelai_negative_prompt_editor_height = self.clamp_novelai_prompt_editor_height(self.config_data.novelai_negative_prompt_editor_height)
            self.config_data.novelai_prompt_expanded = self.novelai_prompt_toggle_button.isChecked()
            self.config_data.novelai_negative_prompt_expanded = self.novelai_negative_prompt_toggle_button.isChecked()
            self.config_data.novelai_enter_to_generate = self.novelai_enter_generate_check.isChecked()
            self.config_data.novelai_delete_folder_contents = self.novelai_delete_folder_contents_check.isChecked()
            self.config_data.novelai_quality_tags = self.novelai_quality_tags_check.isChecked()
            self.config_data.novelai_uc_preset = self.novelai_uc_preset_combo.currentData() or "strong"
            self.config_data.novelai_dataset_mode = self.novelai_dataset_mode()
            self.config_data.novelai_model = self.novelai_model_combo.currentText().strip() or DEFAULT_NOVELAI_MODEL
            self.config_data.novelai_sampler = self.novelai_sampler_combo.currentText().strip() or DEFAULT_NOVELAI_SAMPLER
            self.config_data.novelai_scheduler = self.novelai_scheduler_combo.currentText().strip() or DEFAULT_NOVELAI_SCHEDULER
            self.config_data.novelai_seed = self.novelai_seed_value()
            self.config_data.novelai_random_seed = self.novelai_random_seed_check.isChecked()
            self.config_data.novelai_width = self.novelai_width_spin.value()
            self.config_data.novelai_height = self.novelai_height_spin.value()
            self.config_data.novelai_steps = self.novelai_steps_spin.value()
            self.config_data.novelai_scale = self.novelai_scale_spin.value()
            self.config_data.novelai_cfg_rescale = self.novelai_cfg_rescale_spin.value()
            self.config_data.novelai_variety_boost = self.novelai_variety_boost_check.isChecked()
            self.config_data.novelai_batch_count = self.novelai_number_of_images()
            self.config_data.novelai_is_opus = self.novelai_opus_check.isChecked()
            self.config_data.novelai_auto_open = self.novelai_auto_open_check.isChecked()
            self.config_data.novelai_auto_upscale = self.novelai_auto_upscale_check.isChecked()
            self.config_data.novelai_save_metadata_json = self.novelai_metadata_check.isChecked()
            self.config_data.novelai_detail_expanded = self.novelai_detail_button.isChecked()
            self.config_data.novelai_continuous_delay_seconds = self.novelai_continuous_delay_spin.value()
        self.config_data.cleanup_temp_on_start = self.cleanup_check.isChecked()
        self.config_data.settings_tab = SETTINGS_TAB_IDS[max(0, min(len(SETTINGS_TAB_IDS) - 1, self.tabs.currentIndex()))]
        if not self.is_app_fullscreen():
            rect = self.normalGeometry() if self.isMaximized() else self.geometry()
            if rect.isValid():
                self.config_data.window_rect = [rect.x(), rect.y(), rect.width(), rect.height()]
                self.config_data.window_maximized = self.isMaximized()
        self.config_data.window_geometry = ""
        side_panel = getattr(self, "side_panel", None)
        pin_button = getattr(self, "pin_button", None)
        side_panel_pinned = pin_button.isChecked() if pin_button is not None else self.config_data.side_panel_pinned
        self.config_data.side_panel_pinned = side_panel_pinned
        if side_panel_pinned:
            self.config_data.side_panel_visible = True
        elif self.is_app_fullscreen():
            self.config_data.side_panel_visible = self.side_panel_visible_before_fullscreen
        elif side_panel is not None:
            self.config_data.side_panel_visible = side_panel.isVisible()
        splitter = getattr(self, "splitter", None)
        if side_panel is not None:
            self.config_data.side_panel_width = int(self.side_panel_width)
            self.config_data.side_panel_on_left = self.side_panel_on_left()
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
        self.viewer.set_pixmap_cache_limit(viewer_pixmap_cache_limit(self.viewer_prefetch_spin.value()))
        self.viewer.set_horizontal_wheel_options(
            self.config_data.horizontal_wheel_navigation,
            self.config_data.horizontal_wheel_inverted,
        )
        self.viewer.set_tone_curve_options(self.config_data.tone_curve_enabled, self.current_tone_curve)
        self.viewer.set_display_adjustments(
            self.config_data.display_brightness,
            self.config_data.display_contrast,
            self.config_data.display_gamma,
            self.config_data.display_sharpness,
        )
        self.update_thumbnail_metrics()
        self.layout_viewer_host()
        self.on_compare_changed()

    def restore_last_image_if_needed(self) -> None:
        if not self.config_data.restore_last_image_on_start:
            return
        path_text = self.config_data.last_image_path.strip()
        if not path_text:
            return
        path = Path(path_text)
        if path.is_file() and self.is_image(path):
            QTimer.singleShot(0, lambda p=path: self.open_path_deferred(p))

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
        self.thumbnail_prefetch_timer.stop()
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
            self.thumbnail_queue.put((
                priority,
                sequence,
                self.thumbnail_generation,
                index,
                str(self.image_paths[index]),
                int(self.config_data.thumbnail_size),
                float(self.config_data.hdr_tonemap_brightness),
            ))

    def _thumbnail_worker_loop(self) -> None:
        while True:
            priority, sequence, generation, index, path_text, size, hdr_brightness = self.thumbnail_queue.get()
            if getattr(self, "closing", False):
                return
            if generation != self.thumbnail_generation:
                continue
            started = time.perf_counter()
            try:
                image = load_thumbnail_image(Path(path_text), size, hdr_brightness)
            except Exception:
                image = QImage()
            self.signals.profile_event.emit("サムネイル生成", (time.perf_counter() - started) * 1000)
            self.signals.thumbnail_done.emit(generation, index, image)

    def on_thumbnail_done(self, generation: int, index: int, image: QImage) -> None:
        if generation != self.thumbnail_generation or index < 0 or index >= len(self.thumbnail_items):
            return
        self.thumbnail_pending.discard(index)
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
        self.config_data.last_image_path = str(self.image_paths[self.current_index].resolve())
        self.record_folder_history(self.image_paths[self.current_index])
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
            self.thumbnail_prefetch_timer.start(THUMBNAIL_PREFETCH_DEBOUNCE_MS)

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

    def current_display_has_hdr_image(self) -> bool:
        if not self.image_paths or self.current_index < 0:
            return False
        try:
            for _index, path in self.current_display_index_entries():
                if is_hdr_image_path(self.display_source_path(path)):
                    return True
        except Exception:
            return False
        return False

    def update_hdr_tonemap_controls(self) -> None:
        slider = getattr(self, "hdr_tonemap_brightness_slider", None)
        label = getattr(self, "hdr_tonemap_brightness_label", None)
        reset_button = getattr(self, "hdr_tonemap_reset_button", None)
        if slider is None or label is None:
            return
        enabled = self.current_display_has_hdr_image()
        slider.setEnabled(enabled)
        if reset_button is not None:
            reset_button.setEnabled(enabled and slider.value() != 100)
        percent = slider.value()
        text = "HDR compatible brightness" if self.ui_language() == "en" else "HDR互換表示の明るさ"
        label.setText(f"{text}: {percent}%")

    def on_page_position_slider_changed(self, value: int) -> None:
        if not self.image_paths or value <= 0:
            return
        index = max(0, min(len(self.image_paths) - 1, value - 1))
        if index == self.current_index:
            return
        self.last_navigation_step = 1 if index > self.current_index else -1
        self.current_index = index
        self.config_data.last_image_path = str(self.image_paths[self.current_index].resolve())
        self.record_folder_history(self.image_paths[self.current_index])
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
        if engine == ENGINE_REALESRGAN:
            return DEFAULT_REALESRGAN_TEMPLATE
        if engine == ENGINE_GIGAPIXEL:
            return DEFAULT_GIGAPIXEL_TEMPLATE
        return DEFAULT_REALCUGAN_TEMPLATE

    def active_command_template(self) -> str:
        engine = self.current_engine()
        if engine == ENGINE_REALESRGAN:
            return self.config_data.realesrgan_command_template
        if engine == ENGINE_GIGAPIXEL:
            return self.config_data.gigapixel_command_template
        return self.config_data.realcugan_command_template

    def engine_label(self) -> str:
        return ENGINE_LABELS.get(self.current_engine(), ENGINE_LABELS[ENGINE_REALCUGAN])

    def engine_model_options(self, engine: str) -> list[tuple[str, str]]:
        if engine == ENGINE_REALESRGAN:
            return [(model, model) for model in REALESRGAN_MODELS]
        if engine == ENGINE_GIGAPIXEL:
            return GIGAPIXEL_MODELS
        return [("-", "")]

    def configured_model_for_engine(self, engine: str) -> str:
        if engine == ENGINE_REALESRGAN:
            return self.config_data.realesrgan_model
        if engine == ENGINE_GIGAPIXEL:
            return self.config_data.gigapixel_model
        return ""

    def current_engine_model(self) -> str:
        data = self.realesrgan_model_combo.currentData() if hasattr(self, "realesrgan_model_combo") else None
        return str(data or "")

    def available_scales(self, engine: str | None = None, model: str | None = None) -> list[int]:
        engine = engine or self.current_engine()
        model = self.current_engine_model() if model is None else model
        if engine == ENGINE_REALESRGAN:
            return list(REALESRGAN_MODEL_SCALES.get(model, [REALESRGAN_FIXED_SCALE]))
        if engine == ENGINE_GIGAPIXEL:
            return list(GIGAPIXEL_MODEL_SCALES.get(model, [2, 3, 4, 6]))
        return list(REALCUGAN_SCALES)

    def configured_scale_for_engine(self, engine: str) -> int:
        if engine == ENGINE_REALESRGAN:
            return self.config_data.realesrgan_scale
        if engine == ENGINE_GIGAPIXEL:
            return self.config_data.gigapixel_scale
        return self.config_data.scale

    def populate_engine_model_combo(self, engine: str) -> None:
        options = self.engine_model_options(engine)
        current_options = [str(self.realesrgan_model_combo.itemData(index) or "") for index in range(self.realesrgan_model_combo.count())]
        target_options = [value for _label, value in options]
        if current_options == target_options:
            return
        selected = self.configured_model_for_engine(engine)
        self.realesrgan_model_combo.blockSignals(True)
        self.realesrgan_model_combo.clear()
        for label, value in options:
            self.realesrgan_model_combo.addItem(label, value)
        selected_index = self.realesrgan_model_combo.findData(selected)
        self.realesrgan_model_combo.setCurrentIndex(max(0, selected_index))
        self.realesrgan_model_combo.blockSignals(False)

    def populate_scale_combo(self, engine: str) -> None:
        scales = self.available_scales(engine)
        current_scales = [int(self.scale_combo.itemText(index)) for index in range(self.scale_combo.count())]
        if current_scales == scales:
            return
        preferred = self.configured_scale_for_engine(engine)
        selected = min(scales, key=lambda value: abs(value - preferred))
        self.scale_combo.blockSignals(True)
        self.scale_combo.clear()
        self.scale_combo.addItems([str(value) for value in scales])
        self.scale_combo.setCurrentText(str(selected))
        self.scale_combo.blockSignals(False)

    def auto_realcugan_scale_for_height(self, height: int) -> int:
        threshold = max(1, int(self.skip_height_spin.value() if hasattr(self, "skip_height_spin") else self.config_data.skip_realcugan_height_threshold))
        height = max(1, int(height))
        scales = self.available_scales()
        for scale in scales:
            if height * scale >= threshold:
                return scale
        return scales[-1]

    def remember_image_height(self, source: Path, height: int) -> None:
        if height <= 0:
            return
        source_path = self.normalized_path(source)
        self.image_height_cache[source_path] = int(height)
        self.image_height_cache.move_to_end(source_path)
        while len(self.image_height_cache) > max(64, self.config_data.viewer_prefetch_count * 4 + 16):
            self.image_height_cache.popitem(last=False)

    def image_height_for_scale(self, source: Path) -> int:
        source_path = self.normalized_path(self.display_source_path(source))
        cached_image = self.original_cache.get(source_path)
        if cached_image is not None and not cached_image.isNull():
            self.remember_image_height(source_path, cached_image.height())
            return cached_image.height()
        cached_height = self.image_height_cache.get(source_path)
        if cached_height is not None:
            self.image_height_cache.move_to_end(source_path)
            return cached_height
        size = read_image_size(source_path)
        if size.isValid() and size.height() > 0:
            self.remember_image_height(source_path, size.height())
            return size.height()
        image = load_image(source_path, self.config_data.hdr_tonemap_brightness)
        if image.isNull():
            return 0
        self.remember_image_height(source_path, image.height())
        return image.height()

    def effective_scale(self, source: Path | None = None) -> int:
        if (
            source is not None
            and hasattr(self, "auto_scale_check")
            and self.auto_scale_check.isChecked()
            and len(self.available_scales()) > 1
        ):
            height = self.image_height_for_scale(source)
            if height > 0:
                return self.auto_realcugan_scale_for_height(height)
        return int(self.scale_combo.currentText())

    def current_tile_size(self) -> int:
        combo = getattr(self, "tile_combo", None)
        if combo is None:
            return max(0, int(self.config_data.tile))
        text = combo.currentText().strip()
        try:
            return max(0, int(text))
        except ValueError:
            return 0

    def current_engine_tile_size(self) -> int:
        return self.current_tile_size() if self.current_engine() in {ENGINE_REALCUGAN, ENGINE_REALESRGAN} else 0

    def current_engine_denoise(self) -> int:
        if self.current_engine() == ENGINE_REALCUGAN:
            return int(self.denoise_combo.currentText())
        if self.current_engine() == ENGINE_GIGAPIXEL:
            return self.gigapixel_denoise_spin.value()
        return 0

    def current_gigapixel_adjustments(self) -> tuple[int, int, int]:
        if self.current_engine() != ENGINE_GIGAPIXEL:
            return 0, 0, 0
        return (
            self.gigapixel_sharpen_spin.value(),
            self.gigapixel_compression_spin.value(),
            self.gigapixel_face_recovery_spin.value(),
        )

    def processing_settings_tuple(self, source: Path) -> tuple:
        sharpen, compression, face_recovery = self.current_gigapixel_adjustments()
        return (
            self.normalized_path_text(source),
            self.current_engine(),
            self.effective_scale(source),
            self.current_engine_denoise(),
            self.current_engine_tile_size(),
            self.current_engine_model(),
            sharpen,
            compression,
            face_recovery,
        )

    def create_upscale_task(self, source: Path, force: bool = False) -> UpscaleTask:
        source = self.normalized_path(source)
        engine_input = self.normalized_path(self.display_source_path(source))
        engine = self.current_engine()
        scale = self.effective_scale(source)
        denoise = self.current_engine_denoise()
        tile = self.current_engine_tile_size()
        model = self.current_engine_model()
        sharpen, compression, face_recovery = self.current_gigapixel_adjustments()
        key = (
            self.normalized_path_text(source),
            engine,
            scale,
            denoise,
            tile,
            model,
            sharpen,
            compression,
            face_recovery,
        )
        if engine == ENGINE_REALESRGAN:
            raw_cache_name = f"realesrgan_{model}"
        elif engine == ENGINE_GIGAPIXEL:
            raw_cache_name = f"gigapixel_{model}_d{denoise}_s{sharpen}_c{compression}_f{face_recovery}"
        else:
            raw_cache_name = "realcugan"
        cache_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_cache_name)
        archive_mode = self.archive_mode_active()
        cache_folder = engine_input.parent / f"{cache_name}_x{scale}"
        output_name = engine_input.with_suffix(".png").name if engine == ENGINE_GIGAPIXEL else engine_input.name
        cache_path = None if archive_mode else cache_folder / output_name
        return UpscaleTask(
            source=source,
            engine_input=engine_input,
            key=key,
            engine=engine,
            engine_label=ENGINE_LABELS.get(engine, ENGINE_LABELS[ENGINE_REALCUGAN]),
            command_template=self.active_command_template(),
            scale=scale,
            denoise=denoise,
            tile=tile,
            model=model,
            sharpen=sharpen,
            compression=compression,
            face_recovery=face_recovery,
            cache_path=cache_path,
            read_cache=bool(not archive_mode and self.use_scale_cache_check.isChecked()),
            save_to_cache=bool(not archive_mode and self.save_scale_check.isChecked()),
            force=bool(force),
            skip_tall_images=bool(self.skip_tall_check.isChecked()),
            skip_height_threshold=int(self.skip_height_spin.value()),
            hdr_tonemap_brightness=float(self.config_data.hdr_tonemap_brightness),
        )

    def save_active_command_template(self) -> None:
        if not hasattr(self, "command_edit"):
            return
        text = self.command_edit.text().strip() or self.default_template_for_engine(self.current_engine())
        if self.current_engine() == ENGINE_REALESRGAN:
            self.config_data.realesrgan_command_template = text
        elif self.current_engine() == ENGINE_GIGAPIXEL:
            self.config_data.gigapixel_command_template = text
        else:
            self.config_data.realcugan_command_template = text

    def save_engine_controls(self, engine: str) -> None:
        if not hasattr(self, "scale_combo") or not self.scale_combo.currentText():
            return
        scale = int(self.scale_combo.currentText())
        if engine == ENGINE_REALESRGAN:
            model = self.current_engine_model()
            if model in REALESRGAN_MODELS:
                self.config_data.realesrgan_model = model
            self.config_data.realesrgan_scale = scale
        elif engine == ENGINE_GIGAPIXEL:
            model = self.current_engine_model()
            if model in {value for _label, value in GIGAPIXEL_MODELS}:
                self.config_data.gigapixel_model = model
            self.config_data.gigapixel_scale = scale
            self.config_data.gigapixel_denoise = self.gigapixel_denoise_spin.value()
            self.config_data.gigapixel_sharpen = self.gigapixel_sharpen_spin.value()
            self.config_data.gigapixel_compression = self.gigapixel_compression_spin.value()
            self.config_data.gigapixel_face_recovery = self.gigapixel_face_recovery_spin.value()
        else:
            self.config_data.scale = scale
            self.config_data.denoise = int(self.denoise_combo.currentText())

    def apply_engine_ui(self) -> None:
        if not hasattr(self, "engine_combo"):
            return
        engine = self.current_engine()
        self.populate_engine_model_combo(engine)
        self.populate_scale_combo(engine)
        scales = self.available_scales(engine)
        auto_scale = bool(getattr(self, "auto_scale_check", None) and self.auto_scale_check.isChecked())
        self.scale_combo.setEnabled(len(scales) > 1 and not auto_scale)
        if hasattr(self, "auto_scale_check"):
            self.auto_scale_check.setEnabled(len(scales) > 1)
        self.engine_form.setRowVisible(self.realesrgan_model_combo, engine != ENGINE_REALCUGAN)
        self.engine_form.setRowVisible(self.denoise_combo, engine == ENGINE_REALCUGAN)
        self.engine_form.setRowVisible(self.tile_combo, engine in {ENGINE_REALCUGAN, ENGINE_REALESRGAN})
        self.tile_help.setVisible(engine in {ENGINE_REALCUGAN, ENGINE_REALESRGAN})
        self.denoise_help.setVisible(engine == ENGINE_REALCUGAN)
        self.realesrgan_model_help.setVisible(engine == ENGINE_REALESRGAN)
        self.realesrgan_model_detail.setVisible(engine == ENGINE_REALESRGAN)
        for control in (
            self.gigapixel_denoise_spin,
            self.gigapixel_sharpen_spin,
            self.gigapixel_compression_spin,
            self.gigapixel_face_recovery_spin,
        ):
            self.engine_form.setRowVisible(control, engine == ENGINE_GIGAPIXEL)
        self.gigapixel_help.setVisible(engine == ENGINE_GIGAPIXEL)
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

        colorize_total = len(self.colorize_plan)
        colorize_done = sum(1 for path in self.colorize_plan if self.normalized_path(path) in self.colorize_done_paths)
        self.set_progress_bar(self.colorize_progress_bar, colorize_done, colorize_total, "AI彩色画像生成")

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
            self.effective_scale(path),
            self.current_engine_denoise(),
            self.current_engine_tile_size(),
            self.current_engine_model(),
            *self.current_gigapixel_adjustments(),
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
            index = self.folder_history_index(path, images)
        elif path.is_file() and self.is_image(path):
            images = [path]
            index = 0
        else:
            QMessageBox.information(self, APP_NAME, self.tr_ui("画像ファイル、画像フォルダ、またはアーカイブを指定してください。"))
            return
        if not images:
            if path.is_dir():
                self.set_empty_folder(path)
                self.config_data.last_dir = str(path)
                self.persist_config()
            else:
                QMessageBox.information(self, APP_NAME, self.tr_ui("対応画像がありません。"))
            return
        self.set_image_list(images, index)
        self.config_data.last_dir = str(images[index].parent)
        self.config_data.last_image_path = str(images[index])
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
            self.config_data.last_image_path = str(path)
            QTimer.singleShot(0, lambda p=path: self.collect_folder_images_async(p.parent, p))
            QTimer.singleShot(0, self.persist_config)
            return
        QTimer.singleShot(0, lambda p=path: self.open_path(p))

    def set_image_list(self, images: list[Path], index: int, defer_work: bool = False) -> None:
        self.image_paths = images
        self.refresh_image_path_sets()
        self.current_index = index
        self.current_folder_path = images[index].resolve().parent if images and 0 <= index < len(images) else None
        if images and 0 <= index < len(images):
            self.config_data.last_image_path = str(images[index].resolve())
            self.record_folder_history(images[index])
        self.pending_page_steps = 0
        self.folder_list_loading = False
        self.deferred_page_steps = 0
        self.original_cache.clear()
        self.image_height_cache.clear()
        self.processed_cache.clear()
        self.colorized_session_paths.clear()
        self.viewer.pixmap_cache.clear()
        self.viewer.clear_pixmap_prefetch_state()
        self.prefetching_original_paths.clear()
        self.prefetching_processed_keys.clear()
        self.prefetch_viewer_plan = []
        self.prefetch_engine_plan = []
        self.prefetch_engine_done_paths.clear()
        self.colorize_plan = []
        self.colorize_done_paths.clear()
        self.clear_work_queue()
        self.clear_colorize_queue()
        self.prefetch_generation += 1
        self.update_prefetch_progress_bars()
        self.rebuild_thumbnail_items()
        if defer_work:
            self.display_current_image(defer_work=True)
        else:
            self.display_current_image()

    def set_empty_folder(self, folder: Path) -> None:
        folder = folder.resolve()
        self.image_paths = []
        self.refresh_image_path_sets()
        self.current_index = -1
        self.current_folder_path = folder
        self.config_data.last_image_path = ""
        self.pending_page_steps = 0
        self.folder_list_loading = False
        self.deferred_page_steps = 0
        self.original_cache.clear()
        self.image_height_cache.clear()
        self.processed_cache.clear()
        self.colorized_session_paths.clear()
        self.viewer.pixmap_cache.clear()
        self.viewer.clear_pixmap_prefetch_state()
        self.prefetching_original_paths.clear()
        self.prefetching_processed_keys.clear()
        self.prefetch_viewer_plan = []
        self.prefetch_engine_plan = []
        self.prefetch_engine_done_paths.clear()
        self.colorize_plan = []
        self.colorize_done_paths.clear()
        self.clear_work_queue()
        self.clear_colorize_queue()
        self.prefetch_generation += 1
        self.update_prefetch_progress_bars()
        self.rebuild_thumbnail_items()
        english = self.ui_language() == "en"
        empty_state = "No images" if english else "対応画像なし"
        title = "No supported images in this folder" if english else "このフォルダには対応画像がありません"
        self.viewer.set_empty_message(title, str(folder))
        self.status_label.setText(f"0/0 {empty_state}: {folder.name}")
        self.update_page_position_slider()
        self.setWindowTitle(f"{folder.name} (0 / 0) - {APP_NAME}")

    def folder_history_enabled(self) -> bool:
        check = getattr(self, "folder_history_check", None)
        return bool(check.isChecked() if check is not None else self.config_data.remember_last_image_per_folder)

    def folder_history_key(self, folder: Path) -> str:
        try:
            return str(folder.resolve())
        except OSError:
            return str(folder)

    def folder_history_index(self, folder: Path, images: list[Path]) -> int:
        if not self.folder_history_enabled() or not images:
            return 0
        entry = self.folder_history.get(self.folder_history_key(folder))
        if not isinstance(entry, dict):
            return 0
        remembered = entry.get("image")
        if not isinstance(remembered, str):
            return 0
        remembered_path = Path(remembered)
        try:
            remembered_resolved = remembered_path.resolve()
        except OSError:
            remembered_resolved = remembered_path
        for index, image in enumerate(images):
            if image.resolve() == remembered_resolved:
                return index
        return 0

    def record_folder_history(self, image_path: Path) -> None:
        if self.archive_mode_active() or not self.folder_history_enabled():
            return
        try:
            image = image_path.resolve()
            folder = image.parent
        except OSError:
            return
        self.folder_history[self.folder_history_key(folder)] = {
            "image": str(image),
            "updated": time.time(),
        }
        self.folder_history_dirty = True
        self.prune_folder_history()
        self.folder_history_save_timer.start(700)

    def prune_folder_history(self) -> bool:
        limit = int(getattr(self, "folder_history_limit_spin", None).value() if hasattr(self, "folder_history_limit_spin") else self.config_data.folder_history_limit)
        if limit <= 0 or len(self.folder_history) <= limit:
            return False
        ordered = sorted(
            self.folder_history.items(),
            key=lambda item: float(item[1].get("updated", 0)) if isinstance(item[1], dict) else 0,
            reverse=True,
        )
        self.folder_history = dict(ordered[:limit])
        self.folder_history_dirty = True
        return True

    def save_folder_history_now(self) -> None:
        if not self.folder_history_dirty:
            return
        self.prune_folder_history()
        save_folder_history(self.folder_history)
        self.folder_history_dirty = False

    def collect_folder_images_async(self, folder: Path, selected_path: Path) -> None:
        def worker() -> None:
            started = time.perf_counter()
            try:
                images = self.collect_images(folder)
                resolved_selected = selected_path.resolve()
            except Exception:
                images = []
                resolved_selected = selected_path
            self.signals.profile_event.emit("フォルダ画像列挙", (time.perf_counter() - started) * 1000)
            self.signals.folder_images_ready.emit(images, resolved_selected)

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
        self.current_folder_path = images[selected_index].resolve().parent
        self.config_data.last_image_path = str(images[selected_index].resolve())
        self.record_folder_history(images[selected_index])
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
        self.update_hdr_tonemap_controls()
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
                entry_source = source if entry_path == path and source is not None else self.load_original(self.display_source_path(entry_path))
                entry_processed = (
                    processed
                    if entry_path == path and processed is not None
                    else self.processed_image_from_cache(self.processing_key(entry_path))
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
            source = self.load_original(self.display_source_path(path))
        if processed is None:
            processed = self.processed_image_from_cache(self.processing_key(path))
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
        image = load_image(path, self.config_data.hdr_tonemap_brightness)
        self.record_profile("元画像読込(UI)", (time.perf_counter() - started) * 1000)
        self.original_cache[path] = image
        if not image.isNull():
            self.remember_image_height(path, image.height())
        while len(self.original_cache) > max(6, self.config_data.viewer_prefetch_count * 2 + 3):
            self.original_cache.popitem(last=False)
        return image

    def processed_image_from_cache(self, key: tuple) -> QImage | None:
        return self.processed_cache.get(key)

    def cache_processed_image(self, key: tuple, image: QImage) -> None:
        if image.isNull():
            return
        self.processed_cache[key] = image

    def should_skip_realcugan(self, path: Path) -> bool:
        source_path = self.display_source_path(path)
        if is_hdr_image_path(source_path):
            return True
        if not self.skip_tall_check.isChecked():
            return False
        return self.image_height_for_scale(path) >= self.skip_height_spin.value()

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
        image = self.load_original(self.display_source_path(self.image_paths[index]))
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
        source_path = self.display_source_path(path)
        source = self.load_original(source_path)
        cache_key = self.processing_key(path)
        processed = self.processed_image_from_cache(cache_key)
        skipped = False
        if processed is None:
            existing = self.existing_processed_path(path)
            if existing is not None:
                processed = load_image(existing, self.config_data.hdr_tonemap_brightness)
                if not processed.isNull():
                    self.cache_processed_image(cache_key, processed)
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
        self.config_data.last_image_path = str(self.image_paths[self.current_index].resolve())
        self.record_folder_history(self.image_paths[self.current_index])
        self.display_current_image(preserve_view=self.preserve_view_check.isChecked(), navigation=True)
        return True

    def show_first_image(self) -> None:
        if self.image_paths:
            self.current_index = 0
            self.last_navigation_step = -1
            self.config_data.last_image_path = str(self.image_paths[self.current_index].resolve())
            self.record_folder_history(self.image_paths[self.current_index])
            self.display_current_image(preserve_view=self.preserve_view_check.isChecked(), navigation=True)

    def show_last_image(self) -> None:
        if self.image_paths:
            self.current_index = len(self.image_paths) - 1
            self.last_navigation_step = 1
            self.config_data.last_image_path = str(self.image_paths[self.current_index].resolve())
            self.record_folder_history(self.image_paths[self.current_index])
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
        refit_rotation = bool(getattr(self.config_data, "refit_view_on_rotation", False))
        actions = {
            "open_image": self.open_image_dialog,
            "open_folder": self.open_folder_dialog,
            "parent_folder": self.open_parent_folder,
            "next_folder": self.open_next_folder,
            "child_folder": self.open_child_folder,
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
            "rotate_right": lambda: self.viewer.rotate_display(1),
            "rotate_left": lambda: self.viewer.rotate_display(-1),
            "rotate_right_90": lambda: self.viewer.rotate_display(90, reset_view=refit_rotation),
            "rotate_left_90": lambda: self.viewer.rotate_display(-90, reset_view=refit_rotation),
            "flip_horizontal": lambda: self.viewer.flip_display(True),
            "flip_vertical": lambda: self.viewer.flip_display(False),
            "generate_novelai": self.generate_novelai_images,
            "delete_current_image": self.delete_current_image,
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

    def display_brightness_value(self) -> float:
        return float(self.display_brightness_slider.value())

    def display_contrast_value(self) -> float:
        return self.display_contrast_slider.value() / 100.0

    def display_gamma_value(self) -> float:
        return self.display_gamma_slider.value() / 100.0

    def display_sharpness_value(self) -> float:
        return self.display_sharpness_slider.value() / 10.0

    def update_display_adjustment_labels(self) -> None:
        if not hasattr(self, "display_brightness_slider"):
            return
        self.display_brightness_value_label.setText(f"{self.display_brightness_value():+.0f}")
        self.display_contrast_value_label.setText(f"{self.display_contrast_value():.2f}")
        self.display_gamma_value_label.setText(f"{self.display_gamma_value():.2f}")
        self.display_sharpness_value_label.setText(f"{self.display_sharpness_value():.1f}")

    def on_display_adjustments_changed(self) -> None:
        if getattr(self, "initializing", False) or not hasattr(self, "display_brightness_slider"):
            return
        self.config_data.display_brightness = self.display_brightness_value()
        self.config_data.display_contrast = self.display_contrast_value()
        self.config_data.display_gamma = self.display_gamma_value()
        self.config_data.display_sharpness = self.display_sharpness_value()
        self.update_display_adjustment_labels()
        self.display_adjustment_apply_timer.start(160)

    def apply_display_adjustments(self) -> None:
        if getattr(self, "closing", False):
            return
        self.viewer.set_display_adjustments(
            self.config_data.display_brightness,
            self.config_data.display_contrast,
            self.config_data.display_gamma,
            self.config_data.display_sharpness,
        )
        self.persist_config()

    def reset_display_adjustment(self, adjustment: str) -> None:
        sliders_values = {
            "brightness": (self.display_brightness_slider, 0),
            "contrast": (self.display_contrast_slider, 100),
            "gamma": (self.display_gamma_slider, 100),
            "sharpness": (self.display_sharpness_slider, 0),
        }
        slider_value = sliders_values.get(adjustment)
        if slider_value is None:
            return
        slider, value = slider_value
        if slider.value() == value:
            self.update_display_adjustment_labels()
            return
        slider.setValue(value)

    def reset_display_adjustments(self) -> None:
        if not hasattr(self, "display_brightness_slider"):
            return
        widgets_values = (
            (self.display_brightness_slider, 0),
            (self.display_contrast_slider, 100),
            (self.display_gamma_slider, 100),
            (self.display_sharpness_slider, 0),
        )
        for widget, value in widgets_values:
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self.update_display_adjustment_labels()
        self.on_display_adjustments_changed()

    def on_hdr_tonemap_brightness_changed(self) -> None:
        if getattr(self, "initializing", False) or not hasattr(self, "hdr_tonemap_brightness_slider"):
            return
        self.config_data.hdr_tonemap_brightness = self.hdr_tonemap_brightness_slider.value() / 100.0
        self.update_hdr_tonemap_controls()
        self.persist_config()
        if self.current_display_has_hdr_image():
            self.hdr_tonemap_apply_timer.start(180)

    def reset_hdr_tonemap_brightness(self) -> None:
        slider = getattr(self, "hdr_tonemap_brightness_slider", None)
        if slider is None:
            return
        if slider.value() == 100:
            self.update_hdr_tonemap_controls()
            return
        slider.setValue(100)

    def apply_hdr_tonemap_brightness(self) -> None:
        if getattr(self, "closing", False):
            return
        if not self.current_display_has_hdr_image():
            return
        self.original_cache.clear()
        self.image_height_cache.clear()
        self.prefetching_original_paths.clear()
        self.prefetch_generation += 1
        self.clear_prefetch_io_queue()
        self.viewer.pixmap_cache.clear()
        self.viewer.clear_pixmap_prefetch_state()
        if self.thumbnails_enabled():
            self.refresh_thumbnail_icons_for_size()
        if self.image_paths and self.current_index >= 0:
            self.display_current_image(preserve_view=True)

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
            "Images/Archives (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.jxr *.wdp *.hdp *.zip *.cbz *.rar *.cbr *.7z *.cb7);;All files (*.*)",
        )
        if path:
            self.open_path(Path(path))

    def open_folder_dialog(self) -> None:
        start = self.config_data.last_dir or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "フォルダを開く", start)
        if path:
            self.open_path(Path(path))

    def current_real_folder(self) -> Path | None:
        if self.archive_mode_active():
            return None
        if self.current_folder_path is not None:
            return self.current_folder_path
        if not self.image_paths or self.current_index < 0:
            return None
        try:
            return self.image_paths[self.current_index].resolve().parent
        except OSError:
            return None

    def is_raiv_scale_folder(self, path: Path) -> bool:
        name = path.name.casefold()
        if name == "raiv_colorized":
            return True
        if re.fullmatch(r"x\d+", name):
            return True
        if re.fullmatch(r"realcugan(?:_[a-z0-9_.-]+)?_x\d+", name):
            return True
        if re.fullmatch(r"realesrgan_[a-z0-9_.-]+_x\d+", name):
            return True
        if re.fullmatch(r"gigapixel_[a-z0-9_.-]+_x\d+", name):
            return True
        return False

    def collect_child_folders(self, folder: Path) -> list[Path]:
        folders: list[Path] = []
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if not entry.is_dir():
                        continue
                    path = folder / entry.name
                    if self.is_raiv_scale_folder(path):
                        continue
                    folders.append(path)
        except OSError:
            return []
        return windows_logical_sorted(folders, lambda path: path.name)

    def first_descendant_folder(self, folder: Path, depth: int) -> Path | None:
        target = folder
        for _index in range(depth):
            children = self.collect_child_folders(target)
            if not children:
                return None
            target = children[0]
        return target

    def open_folder_from_navigation(self, folder: Path) -> bool:
        folder = folder.resolve()
        if not folder.is_dir():
            self.append_log_if_visible(f"Folder navigation skipped: folder does not exist: {folder}.")
            return False
        images = self.collect_images(folder)
        self.leave_archive_mode()
        if images:
            self.set_image_list(images, self.folder_history_index(folder, images))
        else:
            self.set_empty_folder(folder)
            self.append_log_if_visible(f"Folder navigation opened empty folder: {folder}.")
        self.config_data.last_dir = str(folder)
        self.persist_config()
        return True

    def open_parent_folder(self) -> None:
        current = self.current_real_folder()
        if current is None:
            self.append_log_if_visible("Folder navigation skipped: no normal folder is open.")
            return
        if current.parent == current:
            self.append_log_if_visible("Folder navigation skipped: parent folder does not exist.")
            return
        self.open_folder_from_navigation(current.parent)

    def open_child_folder(self) -> None:
        current = self.current_real_folder()
        if current is None:
            self.append_log_if_visible("Folder navigation skipped: no normal folder is open.")
            return
        children = self.collect_child_folders(current)
        if children:
            self.open_folder_from_navigation(children[0])
        else:
            self.append_log_if_visible(f"Folder navigation skipped: no child folder in {current}.")

    def open_next_folder(self) -> None:
        current = self.current_real_folder()
        if current is None:
            self.append_log_if_visible("Folder navigation skipped: no normal folder is open.")
            return
        child = current
        parent = current.parent
        depth_to_restore = 0
        while parent != child:
            siblings = self.collect_child_folders(parent)
            try:
                sibling_index = [folder.resolve() for folder in siblings].index(child.resolve())
            except ValueError:
                sibling_index = -1
            for sibling in siblings[sibling_index + 1:]:
                target = self.first_descendant_folder(sibling, depth_to_restore)
                if target is not None and self.open_folder_from_navigation(target):
                    return
            depth_to_restore += 1
            child = parent
            parent = parent.parent
        self.append_log_if_visible(f"Folder navigation skipped: no next folder after {current}.")

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
        self.set_overlay_side_panel_visible(False)
        self.schedule_persist_config()

    def show_side_panel(self) -> None:
        if self.pin_button.isChecked():
            return
        self._show_fullscreen_cursor()
        if not self.side_panel.isVisible():
            self.overlay_hide_suppressed_until = time.monotonic() + SIDE_PANEL_HIDE_GRACE_SEC
            self.detach_side_panel_for_overlay(visible=True)
            self.side_panel.show()
            self.position_overlay_side_panel()
            self.side_panel.raise_()
            self.request_borderless_fullscreen_enforce()
            self.schedule_persist_config()

    def toggle_side_panel(self) -> None:
        self.pin_button.setChecked(not self.pin_button.isChecked())

    def update_side_panel_side_button(self) -> None:
        if hasattr(self, "side_panel_side_button"):
            self.side_panel_side_button.setText(self.tr_ui("右へ移動する" if self.side_panel_on_left() else "左へ移動する"))

    def toggle_side_panel_side(self) -> None:
        if not hasattr(self, "splitter"):
            return
        self.side_panel_width = self.current_side_panel_width()
        visible = self.side_panel.isVisible()
        overlay = self.side_panel_overlay
        self.side_panel.hide()
        self.side_panel.setParent(None)
        self.side_panel_overlay = False
        self.config_data.side_panel_on_left = not self.side_panel_on_left()
        self.update_side_panel_side_button()
        if overlay and not self.pin_button.isChecked():
            self.side_panel.setParent(self)
            self.side_panel.installEventFilter(self)
            self.side_panel_overlay = True
            self.position_overlay_side_panel()
            self.set_overlay_side_panel_visible(visible)
        else:
            if self.side_panel_on_left():
                self.splitter.insertWidget(0, self.side_panel)
            else:
                self.splitter.addWidget(self.side_panel)
            self.side_panel.installEventFilter(self)
            self.side_panel.setVisible(visible)
            self._apply_splitter_panel_width()
        self.persist_config()

    def toggle_thumbnail_panel(self) -> None:
        if not self.thumbnails_enabled():
            self.thumbnail_enabled_check.setChecked(True)
        self.thumbnail_pinned_check.setChecked(not self.thumbnail_pinned_check.isChecked())

    def is_cursor_over_side_panel(self) -> bool:
        if not self.side_panel.isVisible():
            return False
        global_pos = QCursor.pos()
        local = self.side_panel.mapFromGlobal(global_pos)
        if self.side_panel.rect().contains(local):
            return True
        handle = getattr(self, "side_panel_overlay_resize_handle", None)
        if handle is not None and handle.isVisible():
            return handle.rect().contains(handle.mapFromGlobal(global_pos))
        return False

    def should_hide_overlay_panel(self) -> bool:
        if (
            self.overlay_resizing
            or self.overlay_modal_guard
            or self.novelai_prompt_drag_active
            or self.novelai_filename_tooltip_active
            or self.pin_button.isChecked()
            or not self.side_panel_overlay
        ):
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
        if self.side_panel_on_left():
            return local.x() < rect.width() - SIDE_PANEL_HIDE_MARGIN
        return local.x() > SIDE_PANEL_HIDE_MARGIN

    def _ensure_side_panel_width(self) -> None:
        self._apply_splitter_panel_width()

    def request_pinned_side_panel_repair(self) -> None:
        QTimer.singleShot(0, self.ensure_pinned_side_panel_visible)
        QTimer.singleShot(120, self.ensure_pinned_side_panel_visible)
        QTimer.singleShot(500, self.ensure_pinned_side_panel_visible)

    def ensure_pinned_side_panel_visible(self) -> None:
        if not hasattr(self, "side_panel") or not hasattr(self, "pin_button") or not hasattr(self, "splitter"):
            return
        if not self.pin_button.isChecked():
            return
        if self.side_panel_overlay:
            self.attach_side_panel_to_splitter(visible=True)
        elif not self.side_panel.isVisible():
            self.side_panel.setVisible(True)
        sizes = self.splitter.sizes()
        side_index = self.side_panel_splitter_index()
        if len(sizes) < 2 or sizes[side_index] < max(80, self.side_panel.minimumWidth() // 2):
            self._apply_splitter_panel_width()

    def side_panel_on_left(self) -> bool:
        return bool(getattr(self.config_data, "side_panel_on_left", False))

    def side_panel_splitter_index(self) -> int:
        return 0 if self.side_panel_on_left() else 1

    def viewer_splitter_index(self) -> int:
        return 1 if self.side_panel_on_left() else 0

    def current_side_panel_width(self) -> int:
        if self.side_panel_overlay:
            return int(self.side_panel_width)
        sizes = self.splitter.sizes()
        side_index = self.side_panel_splitter_index()
        if len(sizes) >= 2 and sizes[side_index] > 0:
            self.side_panel_width = self.clamped_side_panel_width(sizes[side_index])
            return self.side_panel_width
        return self.clamped_side_panel_width()

    def clamped_side_panel_width(self, width: int | None = None) -> int:
        total = max(1, self.splitter.width() if hasattr(self, "splitter") else self.width())
        maximum = max(1, round(total * 0.6))
        minimum = min(max(240, self.side_panel.minimumWidth()), maximum)
        value = int(self.side_panel_width if width is None else width)
        return max(minimum, min(value, maximum))

    def _apply_splitter_panel_width(self) -> None:
        total = self.splitter.width() or sum(self.splitter.sizes()) or self.width()
        if total <= 0:
            return
        panel_width = self.clamped_side_panel_width()
        self.adjusting_splitter = True
        if self.side_panel_on_left():
            self.splitter.setSizes([panel_width, max(1, total - panel_width)])
        else:
            self.splitter.setSizes([max(1, total - panel_width), panel_width])
        self.adjusting_splitter = False

    def attach_side_panel_to_splitter(self, visible: bool = True) -> None:
        handle = getattr(self, "side_panel_overlay_resize_handle", None)
        if handle is not None:
            handle.hide()
        if self.side_panel_overlay:
            self.side_panel.hide()
            self.side_panel.setParent(None)
            if self.side_panel_on_left():
                self.splitter.insertWidget(0, self.side_panel)
            else:
                self.splitter.addWidget(self.side_panel)
            self.side_panel.installEventFilter(self)
            self.side_panel_overlay = False
            self.update_side_panel_resize_handle_tooltips()
        self.side_panel.setVisible(visible)
        if visible:
            self._apply_splitter_panel_width()
            self.request_pinned_side_panel_repair()

    def update_side_panel_resize_handle_tooltips(self) -> None:
        tooltip = self.tr_ui("ドラッグして設定ペインの幅を調整")
        splitter = getattr(self, "splitter", None)
        if splitter is not None:
            for index in range(1, splitter.count()):
                splitter.handle(index).setToolTip(tooltip)
        overlay_handle = getattr(self, "side_panel_overlay_resize_handle", None)
        if overlay_handle is not None:
            overlay_handle.setToolTip(tooltip)

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
            if self.side_panel_on_left():
                self.splitter.setSizes([0, max(1, self.splitter.width())])
            else:
                self.splitter.setSizes([max(1, self.splitter.width()), 0])
            self.adjusting_splitter = False
        self.position_overlay_side_panel()
        self.set_overlay_side_panel_visible(visible)

    def position_overlay_side_panel(self) -> None:
        if not self.side_panel_overlay:
            return
        central = self.centralWidget().geometry()
        width = min(self.clamped_side_panel_width(), max(1, central.width() // 2))
        if self.side_panel_on_left():
            self.side_panel.setGeometry(central.left(), central.top(), width, central.height())
        else:
            self.side_panel.setGeometry(central.right() - width + 1, central.top(), width, central.height())
        self.position_overlay_side_panel_resize_handle()

    def position_overlay_side_panel_resize_handle(self) -> None:
        handle = getattr(self, "side_panel_overlay_resize_handle", None)
        if handle is None:
            return
        if not self.side_panel_overlay or not self.side_panel.isVisible():
            handle.hide()
            return
        handle_width = 18
        panel_rect = self.side_panel.geometry()
        x = panel_rect.right() + 1 if self.side_panel_on_left() else panel_rect.left() - handle_width
        handle.setGeometry(x, panel_rect.top(), handle_width, panel_rect.height())
        handle.show()
        handle.raise_()

    def set_overlay_side_panel_visible(self, visible: bool) -> None:
        self.side_panel.setVisible(visible)
        handle = getattr(self, "side_panel_overlay_resize_handle", None)
        if handle is None:
            return
        if visible and self.side_panel_overlay:
            self.position_overlay_side_panel_resize_handle()
        else:
            handle.hide()

    def resize_overlay_side_panel(self, delta: int) -> None:
        self.overlay_resizing = True
        width_delta = delta if self.side_panel_on_left() else -delta
        self.side_panel_width = self.clamped_side_panel_width(self.side_panel_width + width_delta)
        self.config_data.side_panel_width = self.side_panel_width
        self.position_overlay_side_panel()

    def finish_overlay_side_panel_resize(self) -> None:
        self.overlay_resizing = False
        self.overlay_hide_suppressed_until = time.monotonic() + SIDE_PANEL_HIDE_GRACE_SEC
        self.persist_config()

    def on_splitter_moved(self, _pos: int, _index: int) -> None:
        if self.adjusting_splitter or self.side_panel_overlay:
            return
        sizes = self.splitter.sizes()
        if len(sizes) < 2:
            return
        total = sum(sizes)
        side_index = self.side_panel_splitter_index()
        viewer_index = self.viewer_splitter_index()
        max_panel = max(self.side_panel.minimumWidth(), total // 2)
        panel = min(sizes[side_index], max_panel)
        panel = max(self.side_panel.minimumWidth(), panel)
        if panel != sizes[side_index]:
            self.adjusting_splitter = True
            new_sizes = [0, 0]
            new_sizes[side_index] = panel
            new_sizes[viewer_index] = max(1, total - panel)
            self.splitter.setSizes(new_sizes)
            self.adjusting_splitter = False
        self.side_panel_width = panel
        self.config_data.side_panel_width = panel
        self.persist_config()

    def toggle_fullscreen(self) -> None:
        if self.is_app_fullscreen():
            self._show_fullscreen_cursor()
            self.borderless_fullscreen = False
            self.fullscreen_enforce_pending = False
            restored_native = self.restore_native_windowed()
            if not restored_native:
                self.setWindowState(Qt.WindowNoState)
                self.setWindowFlags(self.before_fullscreen_flags)
                if self.before_fullscreen_geometry.isValid():
                    self.setGeometry(self.before_fullscreen_geometry)
            self.setStyleSheet("")
            restore_state = self.before_fullscreen_state & ~Qt.WindowFullScreen
            if restored_native:
                self.setWindowState(restore_state)
            else:
                self.show()
            if restore_state != Qt.WindowNoState and not restored_native:
                self.setWindowState(restore_state)
            if self.pin_button.isChecked():
                self.attach_side_panel_to_splitter(visible=True)
            else:
                self.detach_side_panel_for_overlay(visible=False)
        else:
            self.before_fullscreen_geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
            self.before_fullscreen_native_geometry = self.native_window_rect()
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
            self.setStyleSheet("QMainWindow { background: #000000; }")
            target = self.borderless_fullscreen_geometry()
            applied_native = self.apply_native_borderless_fullscreen(target)
            if not applied_native:
                self.setWindowState(Qt.WindowNoState)
                self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
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

    def window_handle_int(self) -> int:
        return int(self.winId()) if os.name == "nt" else 0

    def native_window_style(self) -> int | None:
        hwnd = self.window_handle_int()
        if not hwnd:
            return None
        user32 = ctypes.windll.user32
        if hasattr(user32, "GetWindowLongPtrW"):
            return int(user32.GetWindowLongPtrW(wintypes.HWND(hwnd), GWL_STYLE))
        return int(user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_STYLE))

    def set_native_window_style(self, style: int) -> bool:
        hwnd = self.window_handle_int()
        if not hwnd:
            return False
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetWindowLongPtrW"):
            user32.SetWindowLongPtrW(wintypes.HWND(hwnd), GWL_STYLE, ctypes.c_void_p(style))
        else:
            user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_STYLE, style)
        return True

    def set_native_window_rect(self, rect: QRect, flags: int = 0) -> bool:
        hwnd = self.window_handle_int()
        if not hwnd or not rect.isValid():
            return False
        user32 = ctypes.windll.user32
        return bool(user32.SetWindowPos(
            wintypes.HWND(hwnd),
            None,
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height(),
            SWP_NOZORDER | SWP_NOOWNERZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW | flags,
        ))

    def native_window_rect(self) -> QRect:
        hwnd = self.window_handle_int()
        if os.name != "nt" or not hwnd:
            return QRect()
        rect = wintypes.RECT()
        if not ctypes.windll.user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
            return QRect()
        return QRect(
            int(rect.left),
            int(rect.top),
            int(rect.right - rect.left),
            int(rect.bottom - rect.top),
        )

    def native_borderless_fullscreen_rect(self) -> QRect:
        hwnd = self.window_handle_int()
        if not hwnd:
            return QRect()
        user32 = ctypes.windll.user32
        monitor = user32.MonitorFromWindow(wintypes.HWND(hwnd), MONITOR_DEFAULTTONEAREST)
        if not monitor:
            return QRect()
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return QRect()
        rect = info.rcMonitor
        overscan = BORDERLESS_FULLSCREEN_OVERSCAN
        return QRect(
            int(rect.left) - overscan,
            int(rect.top) - overscan,
            int(rect.right - rect.left) + overscan * 2,
            int(rect.bottom - rect.top) + overscan * 2,
        )

    def native_rect_from_qt_rect(self, rect: QRect) -> QRect:
        if os.name != "nt" or not rect.isValid():
            return QRect()
        screen = QApplication.screenAt(rect.center()) or self.screen() or QApplication.primaryScreen()
        if screen is None:
            return QRect()
        native_screen = self.native_borderless_fullscreen_rect()
        if not native_screen.isValid():
            return QRect()
        logical_screen = screen.geometry()
        ratio = max(1.0, float(screen.devicePixelRatio()))
        return QRect(
            native_screen.x() + round((rect.x() - logical_screen.x()) * ratio) + BORDERLESS_FULLSCREEN_OVERSCAN,
            native_screen.y() + round((rect.y() - logical_screen.y()) * ratio) + BORDERLESS_FULLSCREEN_OVERSCAN,
            max(1, round(rect.width() * ratio)),
            max(1, round(rect.height() * ratio)),
        )

    def apply_native_borderless_fullscreen(self, target: QRect) -> bool:
        if os.name != "nt" or not target.isValid():
            return False
        native_target = self.native_borderless_fullscreen_rect()
        if not native_target.isValid():
            return False
        style = self.native_window_style()
        if style is None:
            return False
        self.before_fullscreen_native_style = style
        if not self.set_native_window_style(style & ~(WS_CAPTION | WS_THICKFRAME)):
            return False
        return self.set_native_window_rect(native_target)

    def restore_native_windowed(self) -> bool:
        if os.name != "nt" or self.before_fullscreen_native_style is None:
            return False
        if not self.set_native_window_style(self.before_fullscreen_native_style):
            return False
        self.before_fullscreen_native_style = None
        if self.before_fullscreen_state & Qt.WindowMaximized:
            return self.set_native_window_rect(self.geometry(), SWP_NOMOVE | SWP_NOSIZE)
        if self.before_fullscreen_native_geometry.isValid():
            return self.set_native_window_rect(self.before_fullscreen_native_geometry)
        if self.before_fullscreen_geometry.isValid():
            native_geometry = self.native_rect_from_qt_rect(self.before_fullscreen_geometry)
            return self.set_native_window_rect(native_geometry if native_geometry.isValid() else self.before_fullscreen_geometry)
        return self.set_native_window_rect(self.geometry(), SWP_NOMOVE | SWP_NOSIZE)

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
        state = self.windowState()
        if state & Qt.WindowFullScreen:
            self.setWindowState(state & ~Qt.WindowFullScreen)
        target = self.borderless_fullscreen_geometry()
        if os.name == "nt" and self.before_fullscreen_native_style is not None:
            style = self.native_window_style()
            desired_style = style & ~(WS_CAPTION | WS_THICKFRAME) if style is not None else None
            if desired_style is not None:
                self.set_native_window_style(desired_style)
            native_target = self.native_borderless_fullscreen_rect()
            if native_target.isValid():
                self.set_native_window_rect(native_target)
            if self.side_panel_overlay:
                self.position_overlay_side_panel()
            return
        changed_flags = False
        desired_flags = Qt.Window | Qt.FramelessWindowHint
        if self.windowFlags() != desired_flags:
            self.setWindowFlags(desired_flags)
            changed_flags = True
        if target.isValid() and self.geometry() != target:
            self.setGeometry(target)
        if changed_flags or not self.isVisible():
            self.show()
        if self.side_panel_overlay:
            self.position_overlay_side_panel()

    def eventFilter(self, watched, event) -> bool:
        filename_editor = getattr(self, "novelai_filename_template_edit", None)
        filename_tooltip = getattr(self, "novelai_filename_template_tooltip", None)
        if watched is filename_editor:
            if event.type() in {QEvent.Enter, QEvent.ToolTip}:
                self.show_novelai_filename_template_tooltip()
                return event.type() == QEvent.ToolTip
            if event.type() == QEvent.Leave:
                QTimer.singleShot(100, self.hide_novelai_filename_template_tooltip_if_unused)
            elif event.type() == QEvent.Hide:
                self.hide_novelai_filename_template_tooltip()
        elif watched is filename_tooltip:
            if event.type() == QEvent.Enter:
                self.novelai_filename_tooltip_active = True
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(100, self.hide_novelai_filename_template_tooltip_if_unused)
        if watched is getattr(self, "novelai_generate_button", None):
            if event.type() in {QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick}:
                if not self.novelai_generate_button.isEnabled():
                    self.novelai_generate_click_pending = False
                    self.ignore_next_novelai_generate_release = False
                    return True
                if event.button() != Qt.LeftButton:
                    return super().eventFilter(watched, event)
                if event.type() == QEvent.MouseButtonPress:
                    return True
                if event.type() == QEvent.MouseButtonRelease:
                    if self.ignore_next_novelai_generate_release:
                        self.ignore_next_novelai_generate_release = False
                        return True
                    self.on_novelai_generate_button_clicked()
                    return True
            if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                self.novelai_generate_click_pending = False
                self.ignore_next_novelai_generate_release = True
                self.toggle_novelai_continuous_generation()
                return True
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
            if event.type() in {QEvent.Enter, QEvent.MouseButtonPress, QEvent.MouseMove}:
                self._show_fullscreen_cursor()
            if self.side_panel_overlay and not self.pin_button.isChecked():
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
                should_show = x <= trigger_width if self.side_panel_on_left() else x >= self.viewer.width() - trigger_width
                if should_show:
                    self.show_side_panel()
                elif self.side_panel_overlay and self.side_panel.isVisible() and self.should_hide_overlay_panel():
                    self.set_overlay_side_panel_visible(False)
                    self.persist_config()
            if self.is_app_fullscreen() and self.fullscreen_cursor_hidden:
                self._show_fullscreen_cursor()
                QTimer.singleShot(1200, self._apply_fullscreen_cursor)
        return super().eventFilter(watched, event)

    def show_novelai_filename_template_tooltip(self) -> None:
        editor = getattr(self, "novelai_filename_template_edit", None)
        if editor is None:
            return
        tooltip = getattr(self, "novelai_filename_template_tooltip", None)
        if tooltip is None:
            tooltip = QLabel(None, Qt.Tool | Qt.FramelessWindowHint)
            tooltip.setTextFormat(Qt.PlainText)
            tooltip.setTextInteractionFlags(Qt.TextSelectableByMouse)
            tooltip.setCursor(Qt.IBeamCursor)
            tooltip.setMargin(6)
            tooltip.setStyleSheet(
                "QLabel { background-color: palette(tool-tip-base); color: palette(tool-tip-text); "
                "border: 1px solid palette(mid); }"
            )
            tooltip.installEventFilter(self)
            self.novelai_filename_template_tooltip = tooltip
        tooltip.setText(editor.toolTip())
        tooltip.adjustSize()
        position = editor.mapToGlobal(QPoint(0, editor.height() + 4))
        screen = QApplication.screenAt(editor.mapToGlobal(editor.rect().center()))
        if screen is not None:
            available = screen.availableGeometry()
            if position.y() + tooltip.height() > available.bottom():
                position.setY(editor.mapToGlobal(QPoint(0, -tooltip.height() - 4)).y())
            position.setX(min(position.x(), available.right() - tooltip.width()))
            position.setY(min(position.y(), available.bottom() - tooltip.height()))
            position.setX(max(position.x(), available.left()))
            position.setY(max(position.y(), available.top()))
        tooltip.move(position)
        self.novelai_filename_tooltip_active = True
        tooltip.show()

    def hide_novelai_filename_template_tooltip_if_unused(self) -> None:
        editor = getattr(self, "novelai_filename_template_edit", None)
        tooltip = getattr(self, "novelai_filename_template_tooltip", None)
        cursor = QCursor.pos()
        for widget in (editor, tooltip):
            if widget is not None and widget.isVisible() and widget.rect().contains(widget.mapFromGlobal(cursor)):
                return
        self.hide_novelai_filename_template_tooltip()

    def hide_novelai_filename_template_tooltip(self) -> None:
        tooltip = getattr(self, "novelai_filename_template_tooltip", None)
        if tooltip is not None:
            tooltip.hide()
        self.novelai_filename_tooltip_active = False

    def hide_overlay_side_panel_if_needed(self) -> None:
        if self.should_hide_overlay_panel():
            self.set_overlay_side_panel_visible(False)
            self.schedule_persist_config()

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
        if self.fullscreen_cursor_hide_suspended:
            self._show_fullscreen_cursor()
            return
        if self.is_app_fullscreen() and self.hide_cursor_fullscreen_check.isChecked() and not self.fullscreen_cursor_hidden:
            if self.is_cursor_over_cursor_visible_area():
                QTimer.singleShot(1200, self._apply_fullscreen_cursor)
                return
            QApplication.setOverrideCursor(QCursor(Qt.BlankCursor))
            self.fullscreen_cursor_hidden = True

    def _show_fullscreen_cursor(self) -> None:
        if self.fullscreen_cursor_hidden:
            QApplication.restoreOverrideCursor()
            self.fullscreen_cursor_hidden = False

    def is_cursor_over_cursor_visible_area(self) -> bool:
        if QApplication.activePopupWidget() is not None:
            return True
        global_pos = QCursor.pos()
        widget = QApplication.widgetAt(global_pos)
        for area in (getattr(self, "side_panel", None), getattr(self, "thumbnail_panel", None)):
            if area is None or not area.isVisible():
                continue
            local = area.mapFromGlobal(global_pos)
            if area.rect().contains(local):
                return True
            current = widget
            while current is not None:
                if current is area:
                    return True
                current = current.parentWidget()
        return False

    def is_app_fullscreen(self) -> bool:
        return self.borderless_fullscreen

    def update_zoom_label(self, scale: float) -> None:
        percent = self.viewer.actual_percent_for_scale(scale)
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
        self.schedule_persist_config()

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
        if self.restore_last_image_check.isChecked() and self.image_paths and self.current_index >= 0:
            self.config_data.last_image_path = str(self.image_paths[self.current_index].resolve())
        self.persist_config()
        if self.folder_history_check.isChecked() and self.image_paths and self.current_index >= 0:
            self.record_folder_history(self.image_paths[self.current_index])
        elif self.prune_folder_history():
            self.folder_history_save_timer.start(700)
        if self.is_app_fullscreen():
            if self.hide_cursor_fullscreen_check.isChecked():
                self._apply_fullscreen_cursor()
            else:
                self._show_fullscreen_cursor()

    def on_tab_visibility_settings_changed(self) -> None:
        self.apply_settings_tab_visibility()
        self.persist_config()

    def apply_settings_tab_visibility(self) -> None:
        if not hasattr(self, "tabs"):
            return
        hidden = {
            "colorize": bool(self.hide_colorize_tab_check.isChecked()) if hasattr(self, "hide_colorize_tab_check") else self.config_data.hide_colorize_tab,
            "novelai": bool(self.hide_novelai_tab_check.isChecked()) if hasattr(self, "hide_novelai_tab_check") else self.config_data.hide_novelai_tab,
            "keyconfig": bool(self.hide_keyconfig_tab_check.isChecked()) if hasattr(self, "hide_keyconfig_tab_check") else self.config_data.hide_keyconfig_tab,
        }
        for index, tab_id in enumerate(SETTINGS_TAB_IDS):
            if hasattr(self.tabs, "setTabVisible"):
                self.tabs.setTabVisible(index, not hidden.get(tab_id, False))
        current_id = SETTINGS_TAB_IDS[max(0, min(len(SETTINGS_TAB_IDS) - 1, self.tabs.currentIndex()))]
        if hidden.get(current_id, False):
            for fallback in ("other", "general", "realcugan"):
                index = SETTINGS_TAB_IDS.index(fallback)
                if not hidden.get(fallback, False):
                    self.tabs.setCurrentIndex(index)
                    break

    def on_language_changed(self) -> None:
        self.config_data.ui_language = self.language_combo.currentData() or "ja"
        self.apply_language()
        self.persist_config()

    def on_theme_changed(self) -> None:
        theme = self.theme_combo.currentData() or THEME_SYSTEM
        self.config_data.ui_theme = theme
        apply_application_color_scheme(theme)
        self.persist_config()

    def on_settings_tab_changed(self, index: int) -> None:
        self.config_data.settings_tab = SETTINGS_TAB_IDS[max(0, min(len(SETTINGS_TAB_IDS) - 1, index))]
        self.persist_config()

    def on_engine_changed(self, *_args) -> None:
        previous_engine = self.config_data.engine
        previous_text = self.command_edit.text().strip()
        if previous_engine == ENGINE_REALESRGAN:
            self.config_data.realesrgan_command_template = previous_text or DEFAULT_REALESRGAN_TEMPLATE
        elif previous_engine == ENGINE_GIGAPIXEL:
            self.config_data.gigapixel_command_template = previous_text or DEFAULT_GIGAPIXEL_TEMPLATE
        else:
            self.config_data.realcugan_command_template = previous_text or DEFAULT_REALCUGAN_TEMPLATE
        self.save_engine_controls(previous_engine)
        self.config_data.engine = self.current_engine()
        self.apply_engine_ui()
        self.on_processing_settings_changed()

    def on_engine_model_changed(self, *_args) -> None:
        engine = self.current_engine()
        model = self.current_engine_model()
        if engine == ENGINE_REALESRGAN and model in REALESRGAN_MODELS:
            self.config_data.realesrgan_model = model
        elif engine == ENGINE_GIGAPIXEL and model in {value for _label, value in GIGAPIXEL_MODELS}:
            self.config_data.gigapixel_model = model
        self.populate_scale_combo(engine)
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

    def on_command_template_changed(self) -> None:
        self.save_active_command_template()
        self.on_processing_settings_changed()

    def on_processing_settings_changed(self) -> None:
        self.apply_engine_ui()
        self.persist_config()
        self.processed_cache.clear()
        self.prefetching_processed_keys.clear()
        self.prefetch_engine_done_paths.clear()
        self.clear_work_queue()
        self.prefetch_generation += 1
        if self.image_paths:
            self.display_current_image()

    def on_viewer_prefetch_changed(self) -> None:
        self.persist_config()
        self.viewer.set_pixmap_cache_limit(viewer_pixmap_cache_limit(self.viewer_prefetch_spin.value()))
        if self.image_paths:
            self.request_schedule_prefetch(0)

    def on_colorize_prefetch_settings_changed(self) -> None:
        self.persist_config()
        self.colorize_plan = []
        self.colorize_done_paths.clear()
        self.clear_colorize_queue()
        if self.image_paths:
            self.request_schedule_prefetch(0)

    def on_colorized_cache_settings_changed(self) -> None:
        self.persist_config()
        self.original_cache.clear()
        self.image_height_cache.clear()
        self.processed_cache.clear()
        self.viewer.pixmap_cache.clear()
        self.viewer.clear_pixmap_prefetch_state()
        self.prefetching_processed_keys.clear()
        self.prefetch_engine_done_paths.clear()
        self.prefetch_generation += 1
        if self.image_paths:
            self.display_current_image()

    def choose_engine_exe(self) -> None:
        engine = self.current_engine()
        title = f"{ENGINE_LABELS[engine]} exeを選択"
        path, _filter = QFileDialog.getOpenFileName(self, title, self.config_data.last_dir or str(APP_DIR), "Executable (*.exe);;All files (*.*)")
        if path:
            if engine == ENGINE_REALESRGAN:
                self.command_edit.setText(f'"{path}" -i "{{input}}" -o "{{output}}" -s {{scale}} -t {{tile}} -n {{model}}')
            elif engine == ENGINE_GIGAPIXEL:
                self.command_edit.setText(
                    f'"{path}" -i "{{input}}" -o "{{output_dir}}" --scale {{scale}} --model "{{model}}" '
                    '--denoise {denoise} --sharpen {sharpen} --compression {compression} --face-recovery {face_recovery} --image-format png'
                )
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

    def clear_work_queue(self) -> None:
        with self.work_queue.mutex:
            self.work_queue.queue.clear()
            self.queued_tasks.clear()

    def clear_colorize_queue(self) -> None:
        with self.colorize_queue.mutex:
            self.colorize_queue.queue.clear()
            self.colorize_queued_paths.clear()

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
            processed: dict[tuple, QImage] = {}
            attempted_originals: list[Path] = []
            attempted_processed: list[tuple] = []
            try:
                if kind == "original":
                    path = self.normalized_path(Path(source))
                    attempted_originals.append(path)
                    image = load_image(path, self.config_data.hdr_tonemap_brightness)
                    if not image.isNull():
                        originals[path] = image
                    self.signals.profile_event.emit("元画像IO", (time.perf_counter() - started) * 1000)
                elif kind == "processed":
                    processed_key = key
                    if isinstance(processed_key, tuple):
                        attempted_processed.append(processed_key)
                        target_path = Path(target)
                        if target_path.exists():
                            image = load_image(target_path, self.config_data.hdr_tonemap_brightness)
                            if not image.isNull():
                                processed[processed_key] = image
                        self.signals.profile_event.emit("拡大画像IO", (time.perf_counter() - started) * 1000)
            except Exception:
                pass
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
        self.clear_colorize_queue()
        realcugan_plan = self.make_plan(self.realcugan_prefetch_spin.value())
        viewer_plan = self.make_prefetch_plan(self.viewer_prefetch_spin.value())
        self.prefetch_viewer_plan = viewer_plan
        self.prefetch_engine_plan = realcugan_plan[1:]
        self.prefetch_engine_done_paths = {
            self.normalized_path(path)
            for path in self.prefetch_engine_plan
            if self.processing_key(path) in self.processed_cache
        }
        if self.colorize_prefetch_check.isChecked():
            self.colorize_plan = self.make_plan(self.colorize_prefetch_spin.value())
            self.colorize_done_paths = {
                self.normalized_path(path)
                for path in self.colorize_plan
                if self.has_colorized_result(path)
            }
            for position, path in enumerate(self.colorize_plan):
                self.enqueue_colorize(path, front=position == 0, force=False)
            self.reorder_colorize_queue(self.colorize_plan)
        else:
            self.colorize_plan = []
            self.colorize_done_paths.clear()
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
        processed_candidates: list[tuple[tuple, Path]] = []
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
        processed: dict[tuple, QImage],
        attempted_originals: list[Path],
        attempted_processed: list[tuple],
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
                if not image.isNull():
                    self.remember_image_height(path, image.height())
                added_originals += 1
        while len(self.original_cache) > max(6, self.config_data.viewer_prefetch_count * 2 + 3):
            self.original_cache.popitem(last=False)
        added_processed = 0
        engine_plan_paths = {self.normalized_path(path) for path in self.prefetch_engine_plan}
        for key, image in processed.items():
            if self.is_current_processing_key(key, current_path_strings) and key not in self.processed_cache:
                self.cache_processed_image(key, image)
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

    def is_current_processing_key(self, key: tuple, current_paths: set[str] | None = None) -> bool:
        if len(key) != 9:
            return False
        current_paths = current_paths or self.image_path_string_set
        return key[0] in current_paths and key == self.processing_settings_tuple(Path(key[0]))

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
        task = self.create_upscale_task(path, force=force)
        if not force and task.key in self.processed_cache:
            return
        if check_existing and not force and task.read_cache and task.cache_path is not None and task.cache_path.exists():
            return
        if check_skip and self.should_skip_realcugan(path):
            return
        if self.processing_task_keys.get(path) == task.key:
            return
        if path in self.queued_tasks:
            queued_task = self.queued_tasks[path]
            if not (queued_task.key == task.key and queued_task.force and not task.force):
                self.queued_tasks[path] = task
            if front:
                self.promote_work_item(path)
            return
        self.queued_tasks[path] = task
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
            task = self.queued_tasks.pop(path, None)
            if task is None:
                continue
            if self.should_skip_upscale_in_worker(task):
                self.signals.process_done.emit({
                    "path": path,
                    "skipped": True,
                    "key": task.key,
                    "engine_label": task.engine_label,
                })
                continue
            if not task.force and task.read_cache and task.cache_path is not None and task.cache_path.exists():
                image = load_image(task.cache_path, task.hdr_tonemap_brightness)
                if not image.isNull():
                    self.signals.process_done.emit({
                        "path": path,
                        "code": 0,
                        "output": "",
                        "image": image,
                        "key": task.key,
                        "engine_label": task.engine_label,
                        "elapsed_ms": 0.0,
                    })
                    continue
            self.processing_paths.add(path)
            self.processing_task_keys[path] = task.key
            self.signals.process_started.emit(task)
            try:
                result = self.run_upscale_engine(task)
            except Exception as exc:
                result = {
                    "path": path,
                    "code": 1,
                    "output": str(exc),
                    "image": QImage(),
                    "key": task.key,
                    "engine_label": task.engine_label,
                }
            finally:
                self.processing_paths.discard(path)
                self.processing_task_keys.pop(path, None)
            self.signals.process_done.emit(result)

    def should_skip_upscale_in_worker(self, task: UpscaleTask) -> bool:
        source_path = task.engine_input
        if is_hdr_image_path(source_path):
            return True
        if not task.skip_tall_images:
            return False
        size = read_image_size(source_path)
        if size.isValid() and size.height() > 0:
            return size.height() >= task.skip_height_threshold
        image = load_image(source_path, task.hdr_tonemap_brightness)
        return not image.isNull() and image.height() >= task.skip_height_threshold

    def run_upscale_engine(self, task: UpscaleTask) -> dict:
        source = task.source
        if task.save_to_cache and task.cache_path is not None:
            task.cache_path.parent.mkdir(parents=True, exist_ok=True)
            output_path = task.cache_path
            temporary_output = False
        else:
            fd, text_path = tempfile.mkstemp(prefix=TEMP_OUTPUT_PREFIX, suffix=".png", dir=self.process_temp_dir)
            os.close(fd)
            output_path = Path(text_path)
            output_path.unlink(missing_ok=True)
            temporary_output = True
        values = {
            "input": str(task.engine_input),
            "output": str(output_path),
            "output_dir": str(output_path.parent),
            "scale": task.scale,
            "denoise": task.denoise,
            "tile": task.tile,
            "model": task.model,
            "sharpen": task.sharpen,
            "compression": task.compression,
            "face_recovery": task.face_recovery,
        }
        try:
            command = task.command_template.format(**values)
            started = time.perf_counter()
            started_wall_time = time.time()
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
            if completed.returncode == 0 and task.engine == ENGINE_GIGAPIXEL and not output_path.exists():
                generated_output = self.find_gigapixel_output(task.engine_input, output_path.parent, started_wall_time)
                if generated_output is not None:
                    shutil.move(str(generated_output), str(output_path))
            image = load_image(output_path, task.hdr_tonemap_brightness) if completed.returncode == 0 and output_path.exists() else QImage()
            return {
                "path": source,
                "code": completed.returncode,
                "output": completed.stdout.strip(),
                "image": image,
                "key": task.key,
                "engine_label": task.engine_label,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
            }
        except Exception as exc:
            return {
                "path": source,
                "code": 1,
                "output": str(exc),
                "image": QImage(),
                "key": task.key,
                "engine_label": task.engine_label,
            }
        finally:
            if temporary_output:
                output_path.unlink(missing_ok=True)

    def find_gigapixel_output(self, source: Path, output_dir: Path, started: float) -> Path | None:
        source_stem = source.stem.casefold()
        candidates: list[Path] = []
        try:
            for path in output_dir.iterdir():
                if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                try:
                    if path.stat().st_mtime < started - 1.0:
                        continue
                except OSError:
                    continue
                if path.stem.casefold().startswith(source_stem):
                    candidates.append(path)
        except OSError:
            return None
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)

    def on_process_started(self, task: object) -> None:
        if isinstance(task, UpscaleTask):
            path = task.source
            engine_label = task.engine_label
        else:
            path = Path(str(task))
            engine_label = self.engine_label()
        self.append_log(f"{engine_label} started: {self.display_name(path)}")
        self.update_window_title()

    def on_process_done(self, result: dict) -> None:
        path: Path = result["path"]
        engine_label = str(result.get("engine_label") or self.engine_label())
        if result.get("skipped"):
            key = result.get("key")
            if isinstance(key, tuple) and self.is_current_processing_key(key):
                self.prefetch_engine_done_paths.add(self.normalized_path(path))
            self.update_prefetch_progress_bars()
            return
        output = result.get("output") or ""
        if output:
            self.append_log(output)
        if result["code"] == 0 and not result["image"].isNull():
            self.record_profile(f"{engine_label}処理", float(result.get("elapsed_ms", 0.0)))
            self.append_log(f"Done: {self.display_name(path)}")
            normalized = self.normalized_path(path)
            if normalized not in self.image_path_set:
                self.update_prefetch_progress_bars()
                return
            key = result.get("key")
            if not isinstance(key, tuple):
                key = self.processing_key(path)
            self.cache_processed_image(key, result["image"])
            current_result = self.is_current_processing_key(key)
            if current_result:
                self.prefetch_engine_done_paths.add(self.normalized_path(path))
            self.update_prefetch_progress_bars()
            if current_result and self.current_index >= 0:
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
        path = self.cache_output_path(self.display_source_path(source), create_dir=False)
        return path if path.exists() else None

    def cache_output_path(self, source: Path, create_dir: bool) -> Path:
        engine_model = self.cache_model_name()
        folder_name = f"{engine_model}_x{self.effective_scale(source)}"
        folder = source.parent / folder_name
        if create_dir:
            folder.mkdir(parents=True, exist_ok=True)
        output_name = source.with_suffix(".png").name if self.current_engine() == ENGINE_GIGAPIXEL else source.name
        return folder / output_name

    def processing_key(self, source: Path) -> tuple:
        return self.processing_settings_tuple(source)

    def cache_model_name(self) -> str:
        if self.current_engine() == ENGINE_REALESRGAN:
            raw = f"realesrgan_{self.current_engine_model()}"
        elif self.current_engine() == ENGINE_GIGAPIXEL:
            sharpen, compression, face_recovery = self.current_gigapixel_adjustments()
            raw = (
                f"gigapixel_{self.current_engine_model()}_d{self.current_engine_denoise()}"
                f"_s{sharpen}_c{compression}_f{face_recovery}"
            )
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

    def send_paths_to_recycle_bin(self, paths: list[Path]) -> bool:
        existing = []
        for path in paths:
            try:
                if path.exists():
                    existing.append(str(path.resolve()))
            except OSError:
                continue
        if not existing:
            return True
        if os.name != "nt":
            return False
        joined = "\0".join(existing) + "\0\0"
        operation = SHFILEOPSTRUCTW()
        operation.hwnd = wintypes.HWND(int(self.winId()))
        operation.wFunc = FO_DELETE
        operation.pFrom = joined
        operation.pTo = None
        operation.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
        return result == 0 and not operation.fAnyOperationsAborted

    def processed_result_paths_for_delete(self, source: Path) -> list[Path]:
        if self.archive_mode_active():
            return []
        folder = source.parent
        paths: list[Path] = []
        try:
            entries = list(folder.iterdir())
        except OSError:
            return []
        for entry in entries:
            if not entry.is_dir() or not self.is_raiv_scale_folder(entry):
                continue
            candidate = entry / source.name
            if candidate.exists():
                paths.append(candidate)
        return paths

    def delete_current_image(self) -> None:
        if self.archive_mode_active() or not self.image_paths or self.current_index < 0:
            return
        source = self.normalized_path(self.image_paths[self.current_index])
        if not source.is_file():
            return
        delete_paths = [source]
        if self.delete_processed_check.isChecked():
            delete_paths.extend(self.processed_result_paths_for_delete(source))
        if self.confirm_delete_check.isChecked():
            if self.ui_language() == "en":
                message = f"Delete this image?\n\n{source}"
            else:
                message = f"この画像を削除しますか？\n\n{source}"
            extra_count = len(delete_paths) - 1
            if extra_count > 0:
                if self.ui_language() == "en":
                    message += f"\n\n{extra_count} processed result(s) will also be deleted."
                else:
                    message += f"\n\n拡大結果 {extra_count} 件も削除されます。"
            self.fullscreen_cursor_hide_suspended = True
            self._show_fullscreen_cursor()
            try:
                answer = QMessageBox.question(self, APP_NAME, message)
            finally:
                self.fullscreen_cursor_hide_suspended = False
                self._apply_fullscreen_cursor()
            if answer != QMessageBox.Yes:
                return
        deleted_processing_key = self.processing_key(source)
        next_index = self.current_index
        if not self.send_paths_to_recycle_bin(delete_paths):
            QMessageBox.warning(self, APP_NAME, self.tr_ui("画像を削除できませんでした。"))
            return
        self.append_log_if_visible(f"Deleted image: {source}")
        self.image_paths.pop(self.current_index)
        self.refresh_image_path_sets()
        self.original_cache.pop(source, None)
        self.image_height_cache.pop(source, None)
        self.processed_cache.pop(deleted_processing_key, None)
        self.viewer.pixmap_cache.clear()
        self.viewer.clear_pixmap_prefetch_state()
        self.rebuild_thumbnail_items()
        if not self.image_paths:
            self.set_empty_folder(source.parent)
            return
        self.current_index = min(next_index, len(self.image_paths) - 1)
        self.config_data.last_image_path = str(self.image_paths[self.current_index].resolve())
        self.record_folder_history(self.image_paths[self.current_index])
        self.display_current_image(preserve_view=False, navigation=True)
        self.schedule_prefetch()

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
                    lock_path = entry / TEMP_LOCK_FILE
                    try:
                        owner_pid = int(lock_path.read_text(encoding="utf-8").strip())
                    except (OSError, ValueError):
                        owner_pid = 0
                    if process_is_running(owner_pid):
                        continue
                    shutil.rmtree(entry, ignore_errors=True)
            except OSError:
                pass

    def closeEvent(self, event) -> None:
        self.closing = True
        self.novelai_continuous_delay_timer.stop()
        self._show_fullscreen_cursor()
        self.persist_config()
        self.folder_history_save_timer.stop()
        self.save_folder_history_now()
        self.work_queue.put(None)
        self.colorize_queue.put(None)
        self.novelai_queue.put(None)
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

