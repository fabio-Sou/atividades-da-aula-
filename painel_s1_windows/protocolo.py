from datetime import datetime


FRAME_WIDTH = 320
FRAME_HEIGHT = 170
BYTES_PER_PIXEL = 2
FRAME_BYTES = FRAME_WIDTH * FRAME_HEIGHT * BYTES_PER_PIXEL
CHUNK_BYTES = 4096
HID_REPORT_BYTES = 4105
USB_TRANSFER_BYTES = 4104
REFRESH_REGIONS = (
    (12, 39, 145, 14),
    (12, 53, 145, 14),
    (12, 75, 145, 14),
    (12, 89, 145, 14),
    (196, 43, 64, 16),
    (196, 66, 64, 16),
    (12, 127, 145, 14),
)

_FONT_5X7 = {
    " ": ("00000",) * 7,
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
}


def _rgb565(color: tuple[int, int, int]) -> bytes:
    red, green, blue = color
    value = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
    return value.to_bytes(2, "big")


def _fill_rect(
    pixels: bytearray,
    x: int,
    y: int,
    width: int,
    height: int,
    color: tuple[int, int, int],
) -> None:
    packed_color = _rgb565(color)
    for row in range(max(y, 0), min(y + height, FRAME_HEIGHT)):
        left = max(x, 0)
        right = min(x + width, FRAME_WIDTH)
        if right <= left:
            continue
        start = (row * FRAME_WIDTH + left) * BYTES_PER_PIXEL
        pixels[start : start + (right - left) * BYTES_PER_PIXEL] = (
            packed_color * (right - left)
        )


def build_test_frame() -> bytes:
    pixels = bytearray(_rgb565((10, 18, 30)) * (FRAME_WIDTH * FRAME_HEIGHT))
    _fill_rect(pixels, 5, 5, FRAME_WIDTH - 10, 3, (45, 190, 245))
    _fill_rect(pixels, 5, FRAME_HEIGHT - 8, FRAME_WIDTH - 10, 3, (45, 190, 245))
    _fill_rect(pixels, 5, 5, 3, FRAME_HEIGHT - 10, (45, 190, 245))
    _fill_rect(
        pixels,
        FRAME_WIDTH - 8,
        5,
        3,
        FRAME_HEIGHT - 10,
        (45, 190, 245),
    )

    text = "S1 TEST"
    scale = 5
    text_width = len(text) * 6 * scale - scale
    start_x = (FRAME_WIDTH - text_width) // 2
    start_y = (FRAME_HEIGHT - 7 * scale) // 2
    for index, character in enumerate(text):
        glyph = _FONT_5X7[character]
        for row, bitmap_row in enumerate(glyph):
            for column, pixel in enumerate(bitmap_row):
                if pixel == "1":
                    _fill_rect(
                        pixels,
                        start_x + index * 6 * scale + column * scale,
                        start_y + row * scale,
                        scale,
                        scale,
                        (242, 245, 248),
                    )
    return bytes(pixels)


def build_heartbeat_report(now: datetime | None = None) -> bytes:
    current_time = now or datetime.now()
    header = bytes(
        (
            0x00,
            0x55,
            0xA1,
            0xF2,
            current_time.hour,
            current_time.minute,
            current_time.second,
        )
    )
    return header.ljust(HID_REPORT_BYTES, b"\x00")


def build_orientation_report(orientation: str) -> bytes:
    orientation_codes = {"landscape": 0x01, "portrait": 0x02}
    try:
        code = orientation_codes[orientation]
    except KeyError:
        raise ValueError(f"Orientação desconhecida: {orientation}") from None
    return bytes((0x00, 0x55, 0xA1, 0xF1, code)).ljust(HID_REPORT_BYTES, b"\x00")


def _refresh_report(
    frame: bytes,
    x: int,
    y: int,
    width: int,
    height: int,
) -> bytes:
    if width * height * BYTES_PER_PIXEL > CHUNK_BYTES:
        raise ValueError("A área de atualização excede um relatório HID.")
    header = bytes(
        (
            0x00,
            0x55,
            0xA2,
            x & 0xFF,
            (x >> 8) & 0xFF,
            y & 0xFF,
            (y >> 8) & 0xFF,
            width,
            height,
        )
    )
    pixels = bytearray()
    for row in range(y, y + height):
        start = (row * FRAME_WIDTH + x) * BYTES_PER_PIXEL
        end = start + width * BYTES_PER_PIXEL
        pixels.extend(frame[start:end])
    return (header + pixels).ljust(HID_REPORT_BYTES, b"\x00")


def _changed_regions(
    previous: bytes,
    current: bytes,
) -> list[tuple[int, int, int, int]]:
    active: dict[tuple[int, int], tuple[int, int]] = {}
    completed: list[tuple[int, int, int, int]] = []
    for y in range(FRAME_HEIGHT):
        runs = []
        row_start = y * FRAME_WIDTH * BYTES_PER_PIXEL
        row_end = row_start + FRAME_WIDTH * BYTES_PER_PIXEL
        if previous[row_start:row_end] != current[row_start:row_end]:
            x = 0
            while x < FRAME_WIDTH:
                offset = row_start + x * BYTES_PER_PIXEL
                if previous[offset : offset + 2] == current[offset : offset + 2]:
                    x += 1
                    continue
                start = x
                x += 1
                while x < FRAME_WIDTH:
                    offset = row_start + x * BYTES_PER_PIXEL
                    if previous[offset : offset + 2] == current[offset : offset + 2]:
                        break
                    x += 1
                while start < x:
                    end = min(start + 255, x)
                    runs.append((start, end))
                    start = end

        next_active = {}
        for run in runs:
            if run in active and active[run][1] == y:
                next_active[run] = (active[run][0], y + 1)
            else:
                next_active[run] = (y, y + 1)
        for run, bounds in active.items():
            if run not in next_active:
                completed.append(
                    (run[0], bounds[0], run[1] - run[0], bounds[1] - bounds[0])
                )
        active = next_active

    for run, bounds in active.items():
        completed.append(
            (run[0], bounds[0], run[1] - run[0], bounds[1] - bounds[0])
        )
    return completed


def build_refresh_reports(
    frame: bytes,
    previous_frame: bytes | None = None,
) -> list[bytes]:
    if len(frame) != FRAME_BYTES:
        raise ValueError(
            f"O quadro deve ter exatamente {FRAME_BYTES} bytes RGB565."
        )

    if previous_frame is not None:
        if len(previous_frame) != FRAME_BYTES:
            raise ValueError(
                f"O quadro anterior deve ter exatamente {FRAME_BYTES} bytes RGB565."
            )
        reports = []
        for x, y, width, height in _changed_regions(previous_frame, frame):
            max_height = max(1, CHUNK_BYTES // (width * BYTES_PER_PIXEL))
            for top in range(y, y + height, max_height):
                part_height = min(max_height, y + height - top)
                reports.append(_refresh_report(frame, x, top, width, part_height))
        return reports

    reports = []
    for x, y, width, height in REFRESH_REGIONS:
        pixel_count = width * height
        if pixel_count * BYTES_PER_PIXEL > CHUNK_BYTES:
            raise ValueError("A área de atualização excede um relatório HID.")
        header = bytes(
            (
                0x00,
                0x55,
                0xA2,
                x & 0xFF,
                (x >> 8) & 0xFF,
                y & 0xFF,
                (y >> 8) & 0xFF,
                width,
                height,
            )
        )
        pixels = bytearray()
        for row in range(y, y + height):
            start = (row * FRAME_WIDTH + x) * BYTES_PER_PIXEL
            end = start + width * BYTES_PER_PIXEL
            pixels.extend(frame[start:end])
        report = (header + pixels).ljust(HID_REPORT_BYTES, b"\x00")
        if len(report) != HID_REPORT_BYTES:
            raise AssertionError("Tamanho inesperado no relatório HID.")
        reports.append(report)

    return reports


def build_hid_reports(frame: bytes) -> list[bytes]:
    if len(frame) != FRAME_BYTES:
        raise ValueError(
            f"O quadro deve ter exatamente {FRAME_BYTES} bytes RGB565."
        )

    reports: list[bytes] = []
    for sequence, offset in enumerate(range(0, FRAME_BYTES, CHUNK_BYTES), start=1):
        chunk = frame[offset : offset + CHUNK_BYTES]
        if sequence == 1:
            kind = 0xF0
        elif offset + len(chunk) == FRAME_BYTES:
            kind = 0xF2
        else:
            kind = 0xF1
        header = bytes(
            (
                0x55,
                0xA3,
                kind,
                sequence,
                offset & 0xFF,
                (offset >> 8) & 0xFF,
                len(chunk) & 0xFF,
                (len(chunk) >> 8) & 0xFF,
            )
        )
        packet = (header + chunk).ljust(USB_TRANSFER_BYTES, b"\x00")
        report = b"\x00" + packet
        if len(report) != HID_REPORT_BYTES:
            raise AssertionError("Tamanho inesperado no relatório HID.")
        reports.append(report)

    return reports
