from datetime import datetime
from pathlib import Path
from tkinter import PhotoImage
from typing import Protocol

from PIL import Image, ImageOps

from protocolo import FRAME_BYTES, FRAME_HEIGHT, FRAME_WIDTH


_FONT_5X7 = {
    " ": ("00000",) * 7,
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}

BACKGROUND = (7, 13, 23)
PANEL = (7, 13, 23)
WHITE = (238, 242, 247)
CYAN = (68, 205, 245)
PURPLE = (181, 142, 255)
BAR_BG = (50, 62, 76)
IMAGE_LAYOUTS = (
    "Preencher",
    "Ajustar",
    "Estender",
    "Lado a lado",
    "Centralizar",
    "Ampliar",
)
IMAGE_LAYOUT_CODES = {
    "Preencher": "fill",
    "Ajustar": "fit",
    "Estender": "stretch",
    "Lado a lado": "tile",
    "Centralizar": "center",
    "Ampliar": "span",
}


class ImagePixels(Protocol):
    def width(self) -> int: ...

    def height(self) -> int: ...

    def get(self, x: int, y: int) -> tuple[int, int, int]: ...


class RasterImage:
    def __init__(self, image: Image.Image) -> None:
        self._image = image.convert("RGB")
        self._pixels = self._image.load()

    def width(self) -> int:
        return self._image.width

    def height(self) -> int:
        return self._image.height

    def get(self, x: int, y: int) -> tuple[int, int, int]:
        red, green, blue = self._pixels[x, y]
        return red, green, blue


def load_jpeg_image(path: Path) -> RasterImage:
    with Image.open(path) as image:
        oriented = ImageOps.exif_transpose(image)
        return RasterImage(oriented)


def load_image_pixels(path: Path) -> RasterImage:
    with Image.open(path) as image:
        image.seek(0)
        oriented = ImageOps.exif_transpose(image)
        return RasterImage(oriented)


def _rgb565(red: int, green: int, blue: int) -> bytes:
    value = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
    return value.to_bytes(2, "big")


def _image_pixels(
    image: ImagePixels | None,
    layout: str = "fill",
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
) -> bytearray:
    if layout not in set(IMAGE_LAYOUT_CODES.values()):
        raise ValueError(f"Modo de ajuste de imagem desconhecido: {layout}")
    pixels = bytearray(_rgb565(*BACKGROUND) * (width * height))
    if image is None:
        return pixels

    image_width = image.width()
    image_height = image.height()
    if image_width <= 0 or image_height <= 0:
        raise ValueError("A imagem precisa ter largura e altura maiores que zero.")
    if layout in {"center", "tile"}:
        target_x_offset = (width - image_width) // 2
        target_y_offset = (height - image_height) // 2
        for y in range(height):
            if layout == "tile":
                source_y = y % image_height
            else:
                source_y = y - target_y_offset
            if not 0 <= source_y < image_height:
                continue
            for x in range(width):
                if layout == "tile":
                    source_x = x % image_width
                else:
                    source_x = x - target_x_offset
                if 0 <= source_x < image_width:
                    red, green, blue = image.get(source_x, source_y)
                    offset = (y * width + x) * 2
                    pixels[offset : offset + 2] = _rgb565(red, green, blue)
        return pixels

    if layout == "stretch":
        target_width = width
        target_height = height
        target_x_offset = 0
        target_y_offset = 0
    elif layout in {"fill", "fit", "span"}:
        scale_x = width / image_width
        scale_y = height / image_height
        scale = max(scale_x, scale_y) if layout in {"fill", "span"} else min(
            scale_x,
            scale_y,
        )
        target_width = max(1, round(image_width * scale))
        target_height = max(1, round(image_height * scale))
        target_x_offset = (FRAME_WIDTH - target_width) // 2
        target_y_offset = (FRAME_HEIGHT - target_height) // 2
    for y in range(height):
        scaled_y = y - target_y_offset
        if not 0 <= scaled_y < target_height:
            continue
        source_y = min(
            image_height - 1,
            int((scaled_y + 0.5) * image_height / target_height),
        )
        for x in range(width):
            scaled_x = x - target_x_offset
            if not 0 <= scaled_x < target_width:
                continue
            source_x = min(
                image_width - 1,
                int((scaled_x + 0.5) * image_width / target_width),
            )
            red, green, blue = image.get(source_x, source_y)
            offset = (y * width + x) * 2
            pixels[offset : offset + 2] = _rgb565(red, green, blue)
    return pixels


def _rotate_pixels(
    pixels: bytes | bytearray,
    width: int,
    height: int,
    *,
    clockwise: bool,
) -> tuple[bytes, int, int]:
    rotated_width = height
    rotated_height = width
    rotated = bytearray(len(pixels))
    for y in range(height):
        for x in range(width):
            if clockwise:
                target_x = height - 1 - y
                target_y = x
            else:
                target_x = y
                target_y = width - 1 - x
            source_offset = (y * width + x) * 2
            target_offset = (target_y * rotated_width + target_x) * 2
            rotated[target_offset : target_offset + 2] = pixels[
                source_offset : source_offset + 2
            ]
    return bytes(rotated), rotated_width, rotated_height


def orient_frame_for_preview(frame: bytes, orientation: str) -> tuple[bytes, int, int]:
    if orientation == "landscape":
        return frame, FRAME_WIDTH, FRAME_HEIGHT
    if orientation != "portrait":
        raise ValueError(f"Orientação desconhecida: {orientation}")
    return _rotate_pixels(frame, FRAME_WIDTH, FRAME_HEIGHT, clockwise=True)


def prepare_image_pixels(
    image: ImagePixels | None,
    layout: str = "fill",
    orientation: str = "landscape",
) -> bytes:
    if orientation == "landscape":
        return bytes(_image_pixels(image, layout))
    if orientation != "portrait":
        raise ValueError(f"Orientação desconhecida: {orientation}")
    portrait, width, height = _image_pixels(
        image,
        layout,
        FRAME_HEIGHT,
        FRAME_WIDTH,
    ), FRAME_HEIGHT, FRAME_WIDTH
    landscape, _, _ = _rotate_pixels(portrait, width, height, clockwise=False)
    return landscape


def _darken_content_area(
    pixels: bytearray,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
) -> None:
    dark_red, dark_green, dark_blue = PANEL
    for y in range(5, height - 5):
        for x in range(5, width - 5):
            offset = (y * width + x) * 2
            value = int.from_bytes(pixels[offset : offset + 2], "big")
            red = ((value >> 11) & 0x1F) * 255 // 31
            green = ((value >> 5) & 0x3F) * 255 // 63
            blue = (value & 0x1F) * 255 // 31
            red = (red + dark_red * 2) // 3
            green = (green + dark_green * 2) // 3
            blue = (blue + dark_blue * 2) // 3
            pixels[offset : offset + 2] = _rgb565(red, green, blue)


def prepare_render_background(
    image: ImagePixels | bytes | None,
    image_layout: str = "fill",
    orientation: str = "landscape",
) -> bytes:
    if orientation not in {"landscape", "portrait"}:
        raise ValueError(f"Orientação desconhecida: {orientation}")
    frame_width = FRAME_WIDTH if orientation == "landscape" else FRAME_HEIGHT
    frame_height = FRAME_HEIGHT if orientation == "landscape" else FRAME_WIDTH
    if isinstance(image, bytes):
        if len(image) != FRAME_BYTES:
            raise ValueError(
                f"O fundo deve ter exatamente {FRAME_BYTES} bytes RGB565."
            )
        pixels = bytearray(image)
        if orientation == "portrait":
            pixels = bytearray(
                _rotate_pixels(
                    image,
                    FRAME_WIDTH,
                    FRAME_HEIGHT,
                    clockwise=True,
                )[0]
            )
    else:
        pixels = _image_pixels(image, image_layout, frame_width, frame_height)
    _darken_content_area(pixels, frame_width, frame_height)
    return bytes(pixels)


def _fill_rect(
    pixels: bytearray,
    x: int,
    y: int,
    width: int,
    height: int,
    color: tuple[int, int, int],
    frame_width: int = FRAME_WIDTH,
    frame_height: int = FRAME_HEIGHT,
) -> None:
    packed = _rgb565(*color)
    for row in range(max(y, 0), min(y + height, frame_height)):
        left = max(x, 0)
        right = min(x + width, frame_width)
        if right <= left:
            continue
        offset = (row * frame_width + left) * 2
        pixels[offset : offset + (right - left) * 2] = packed * (right - left)


def _draw_text(
    pixels: bytearray,
    text: str,
    x: int,
    y: int,
    color: tuple[int, int, int],
    scale: int = 2,
    frame_width: int = FRAME_WIDTH,
    frame_height: int = FRAME_HEIGHT,
) -> None:
    cursor_x = x
    for character in text.upper():
        glyph = _FONT_5X7.get(character, _FONT_5X7[" "])
        for row, bitmap_row in enumerate(glyph):
            for column, set_pixel in enumerate(bitmap_row):
                if set_pixel == "1":
                    _fill_rect(
                        pixels,
                        cursor_x + column * scale,
                        y + row * scale,
                        scale,
                        scale,
                        color,
                        frame_width,
                        frame_height,
                    )
        cursor_x += 6 * scale


def render_frame(
    image: ImagePixels | bytes | None,
    cpu_percent: float | None,
    memory_percent: float,
    uptime_seconds: int,
    now: datetime | None = None,
    image_layout: str = "fill",
    orientation: str = "landscape",
    metric_positions: dict[str, tuple[int, int]] | None = None,
    visible_metrics: set[str] | None = None,
    disk_free_gb: float = 0.0,
    disk_total_gb: float = 0.0,
    metric_scale: int | dict[str, int] = 2,
    prepared_background: bool = False,
) -> bytes:
    if orientation not in {"landscape", "portrait"}:
        raise ValueError(f"Orientação desconhecida: {orientation}")
    if isinstance(metric_scale, int):
        metric_scales = {
            metric: metric_scale
            for metric in ("cpu", "memory", "clock", "uptime", "disk")
        }
    else:
        metric_scales = metric_scale
    if set(metric_scales) != {"cpu", "memory", "clock", "uptime", "disk"}:
        raise ValueError("É necessário fornecer um tamanho para cada informação.")
    if any(scale not in {2, 3, 4} for scale in metric_scales.values()):
        raise ValueError("Tamanho de informação inválido.")
    frame_width = FRAME_WIDTH if orientation == "landscape" else FRAME_HEIGHT
    frame_height = FRAME_HEIGHT if orientation == "landscape" else FRAME_WIDTH
    if prepared_background:
        if not isinstance(image, bytes) or len(image) != FRAME_BYTES:
            raise ValueError("O fundo previamente preparado tem tamanho inválido.")
        pixels = bytearray(image)
    elif isinstance(image, bytes):
        if len(image) != FRAME_BYTES:
            raise ValueError(
                f"O fundo deve ter exatamente {FRAME_BYTES} bytes RGB565."
            )
        pixels = bytearray(image)
        if orientation == "portrait":
            rotated, _, _ = _rotate_pixels(
                image,
                FRAME_WIDTH,
                FRAME_HEIGHT,
                clockwise=True,
            )
            pixels = bytearray(rotated)
    else:
        pixels = _image_pixels(
            image,
            image_layout,
            frame_width,
            frame_height,
        )
    if not prepared_background:
        _darken_content_area(pixels, frame_width, frame_height)

    defaults = (
        {
            "cpu": (12, 39),
            "memory": (12, 75),
            "clock": (196, 43),
            "uptime": (12, 127),
            "disk": (196, 127),
        }
        if orientation == "landscape"
        else {
            "cpu": (12, 35),
            "memory": (12, 92),
            "clock": (12, 149),
            "uptime": (12, 206),
            "disk": (12, 263),
        }
    )
    positions = defaults | (metric_positions or {})
    enabled = (
        {"cpu", "memory", "clock", "uptime", "disk"}
        if visible_metrics is None
        else visible_metrics
    )
    current_time = now or datetime.now()
    if "cpu" in enabled:
        x, y = positions["cpu"]
        scale = metric_scales["cpu"]
        cpu_text = "--" if cpu_percent is None else f"{cpu_percent:.0f}%"
        _draw_text(
            pixels,
            f"CPU {cpu_text}",
            x,
            y,
            WHITE,
            scale=scale,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        cpu_value = (
            0.0 if cpu_percent is None else max(0.0, min(cpu_percent, 100.0))
        )
        bar_width = min(145 * scale // 2, frame_width - x)
        bar_height = 3 * scale
        bar_y = y + 10 * scale
        _fill_rect(
            pixels, x, bar_y, bar_width, bar_height, BAR_BG, frame_width, frame_height
        )
        _fill_rect(
            pixels,
            x,
            bar_y,
            round(bar_width * cpu_value / 100),
            bar_height,
            CYAN,
            frame_width,
            frame_height,
        )
    if "memory" in enabled:
        x, y = positions["memory"]
        scale = metric_scales["memory"]
        ram_value = max(0.0, min(memory_percent, 100.0))
        _draw_text(
            pixels,
            f"RAM {memory_percent:.0f}%",
            x,
            y,
            WHITE,
            scale=scale,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        bar_width = min(145 * scale // 2, frame_width - x)
        bar_height = 3 * scale
        bar_y = y + 10 * scale
        _fill_rect(
            pixels, x, bar_y, bar_width, bar_height, BAR_BG, frame_width, frame_height
        )
        _fill_rect(
            pixels,
            x,
            bar_y,
            round(bar_width * ram_value / 100),
            bar_height,
            PURPLE,
            frame_width,
            frame_height,
        )
    if "clock" in enabled:
        x, y = positions["clock"]
        scale = metric_scales["clock"]
        _draw_text(
            pixels,
            current_time.strftime("%H:%M"),
            x,
            y,
            CYAN,
            scale=scale,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        _draw_text(
            pixels,
            current_time.strftime("%d/%m"),
            x,
            y + round(11.5 * scale),
            WHITE,
            scale=max(1, scale - 1),
            frame_width=frame_width,
            frame_height=frame_height,
        )
    days, remainder = divmod(uptime_seconds, 24 * 60 * 60)
    hours = remainder // (60 * 60)
    if "uptime" in enabled:
        x, y = positions["uptime"]
        scale = metric_scales["uptime"]
        _draw_text(
            pixels,
            f"UP {days:02}D {hours:02}H",
            x,
            y,
            WHITE,
            scale=scale,
            frame_width=frame_width,
            frame_height=frame_height,
        )
    if "disk" in enabled:
        x, y = positions["disk"]
        scale = metric_scales["disk"]
        _draw_text(
            pixels,
            f"D {disk_free_gb:.0f}/{disk_total_gb:.0f}G",
            x,
            y,
            WHITE,
            scale=scale,
            frame_width=frame_width,
            frame_height=frame_height,
        )

    frame = bytes(pixels)
    if orientation == "portrait":
        frame, _, _ = _rotate_pixels(
            frame,
            frame_width,
            frame_height,
            clockwise=False,
        )
    if len(frame) != FRAME_BYTES:
        raise AssertionError("O quadro renderizado tem tamanho inesperado.")
    return frame
