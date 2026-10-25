import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from protocolo import FRAME_BYTES, FRAME_HEIGHT, FRAME_WIDTH
from renderizar import (
    BACKGROUND,
    IMAGE_LAYOUT_CODES,
    load_jpeg_image,
    orient_frame_for_preview,
    prepare_image_pixels,
    prepare_render_background,
    render_frame,
)


class SolidImage:
    def width(self) -> int:
        return 320

    def height(self) -> int:
        return 170

    def get(self, _x: int, _y: int) -> tuple[int, int, int]:
        return (20, 80, 160)


class TwoColorImage:
    def width(self) -> int:
        return 2

    def height(self) -> int:
        return 1

    def get(self, x: int, _y: int) -> tuple[int, int, int]:
        return (255, 0, 0) if x == 0 else (0, 0, 255)


def packed_pixel(frame: bytes, x: int, y: int) -> bytes:
    offset = (y * FRAME_WIDTH + x) * 2
    return frame[offset : offset + 2]


def rgb565(red: int, green: int, blue: int) -> bytes:
    value = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
    return value.to_bytes(2, "big")


class RenderTests(unittest.TestCase):
    def test_renders_exact_frame_size_with_image_and_metrics(self):
        frame = render_frame(
            SolidImage(),
            47.0,
            63.0,
            90_061,
            datetime(2026, 10, 25, 12, 34),
        )
        self.assertEqual(len(frame), FRAME_BYTES)
        self.assertGreater(len(set(frame)), 10)

    def test_renders_without_background_image(self):
        frame = render_frame(
            None,
            None,
            0.0,
            0,
            datetime(2026, 10, 25, 0, 0),
        )
        self.assertEqual(len(frame), FRAME_BYTES)

    def test_prepared_background_matches_regular_frame_in_each_orientation(self):
        for orientation in ("landscape", "portrait"):
            with self.subTest(orientation=orientation):
                background = prepare_image_pixels(
                    SolidImage(),
                    "fill",
                    orientation,
                )
                prepared = prepare_render_background(
                    background,
                    orientation=orientation,
                )
                direct_frame = render_frame(
                    background,
                    47.0,
                    63.0,
                    90_061,
                    datetime(2026, 10, 25, 12, 34),
                    orientation=orientation,
                )
                cached_frame = render_frame(
                    prepared,
                    47.0,
                    63.0,
                    90_061,
                    datetime(2026, 10, 25, 12, 34),
                    orientation=orientation,
                    prepared_background=True,
                )

                self.assertEqual(cached_frame, direct_frame)

    def test_prepares_pixels_for_all_six_image_layouts(self):
        for layout in IMAGE_LAYOUT_CODES.values():
            with self.subTest(layout=layout):
                pixels = prepare_image_pixels(TwoColorImage(), layout)
                self.assertEqual(len(pixels), FRAME_BYTES)

    def test_fit_preserves_aspect_ratio_and_centers_image(self):
        pixels = prepare_image_pixels(TwoColorImage(), "fit")

        self.assertEqual(packed_pixel(pixels, 0, 4), rgb565(*BACKGROUND))
        self.assertEqual(packed_pixel(pixels, 0, 5), rgb565(255, 0, 0))
        self.assertEqual(packed_pixel(pixels, FRAME_WIDTH - 1, 5), rgb565(0, 0, 255))

    def test_stretch_fills_frame_without_preserving_aspect_ratio(self):
        pixels = prepare_image_pixels(TwoColorImage(), "stretch")

        self.assertEqual(packed_pixel(pixels, 0, 0), rgb565(255, 0, 0))
        self.assertEqual(
            packed_pixel(pixels, FRAME_WIDTH - 1, 0),
            rgb565(0, 0, 255),
        )

    def test_tile_repeats_image_from_top_left(self):
        pixels = prepare_image_pixels(TwoColorImage(), "tile")

        self.assertEqual(packed_pixel(pixels, 0, 0), rgb565(255, 0, 0))
        self.assertEqual(packed_pixel(pixels, 1, 0), rgb565(0, 0, 255))
        self.assertEqual(packed_pixel(pixels, 2, 0), rgb565(255, 0, 0))

    def test_center_preserves_native_size_and_crops_overflow(self):
        pixels = prepare_image_pixels(TwoColorImage(), "center")
        offset_x = (FRAME_WIDTH - 2) // 2
        offset_y = (FRAME_HEIGHT - 1) // 2

        self.assertEqual(packed_pixel(pixels, offset_x - 1, offset_y), rgb565(*BACKGROUND))
        self.assertEqual(packed_pixel(pixels, offset_x, offset_y), rgb565(255, 0, 0))
        self.assertEqual(packed_pixel(pixels, offset_x + 1, offset_y), rgb565(0, 0, 255))

    def test_fill_and_span_crop_to_cover_the_frame(self):
        for layout in ("fill", "span"):
            with self.subTest(layout=layout):
                pixels = prepare_image_pixels(TwoColorImage(), layout)
                self.assertEqual(packed_pixel(pixels, 0, 0), rgb565(255, 0, 0))
                self.assertEqual(
                    packed_pixel(pixels, FRAME_WIDTH - 1, 0),
                    rgb565(0, 0, 255),
                )

    def test_rejects_unknown_image_layout(self):
        with self.assertRaises(ValueError):
            prepare_image_pixels(TwoColorImage(), "unknown")

    def test_loads_jpeg_and_converts_it_to_panel_pixels(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "background.jpg"
            Image.new("RGB", (24, 16), (220, 60, 30)).save(path, format="JPEG")

            image = load_jpeg_image(path)
            pixels = prepare_image_pixels(image, "stretch")

        self.assertEqual((image.width(), image.height()), (24, 16))
        self.assertEqual(len(pixels), FRAME_BYTES)

    def test_portrait_layout_keeps_protocol_frame_and_previews_upright(self):
        background = prepare_image_pixels(TwoColorImage(), "fit", "portrait")
        frame = render_frame(
            background,
            25.0,
            60.0,
            1_800,
            datetime(2026, 10, 25, 12, 34),
            orientation="portrait",
        )
        preview, width, height = orient_frame_for_preview(frame, "portrait")

        self.assertEqual(len(background), FRAME_BYTES)
        self.assertEqual(len(frame), FRAME_BYTES)
        self.assertEqual((width, height), (FRAME_HEIGHT, FRAME_WIDTH))
        self.assertEqual(len(preview), FRAME_BYTES)

    def test_hidden_metrics_are_not_rendered_onto_the_background(self):
        background = prepare_image_pixels(None)
        first_frame = render_frame(
            background,
            25.0, 60.0, 1_800,
            datetime(2026, 10, 25, 12, 34),
            visible_metrics=set(),
        )
        second_frame = render_frame(
            background,
            90.0, 10.0, 80_000,
            datetime(2027, 1, 1, 1, 2),
            visible_metrics=set(),
        )

        self.assertEqual(first_frame, second_frame)

    def test_custom_metric_positions_change_rendered_frame(self):
        background = prepare_image_pixels(None)
        default_frame = render_frame(background, 25.0, 60.0, 1_800)
        moved_frame = render_frame(
            background,
            25.0,
            60.0,
            1_800,
            metric_positions={"cpu": (160, 30)},
        )

        self.assertNotEqual(default_frame, moved_frame)

    def test_larger_metric_scale_produces_larger_rendered_text(self):
        background = prepare_image_pixels(None)
        normal = render_frame(
            background,
            25.0,
            60.0,
            1_800,
            metric_scale=2,
            visible_metrics={"cpu"},
        )
        large = render_frame(
            background,
            25.0,
            60.0,
            1_800,
            metric_scale=3,
            visible_metrics={"cpu"},
        )

        self.assertGreater(
            sum(normal[index] != 0 for index in range(0, len(normal), 2)),
            0,
        )
        self.assertNotEqual(normal, large)

    def test_metric_scales_can_be_configured_independently(self):
        background = prepare_image_pixels(None)
        sizes = {
            "cpu": 4,
            "memory": 2,
            "clock": 2,
            "uptime": 2,
            "disk": 2,
        }
        frame = render_frame(
            background,
            25.0,
            60.0,
            1_800,
            metric_scale=sizes,
            visible_metrics={"cpu", "memory"},
        )
        uniform_frame = render_frame(
            background,
            25.0,
            60.0,
            1_800,
            metric_scale=2,
            visible_metrics={"cpu", "memory"},
        )

        self.assertNotEqual(frame, uniform_frame)

    def test_rejects_unsupported_metric_scale(self):
        with self.assertRaises(ValueError):
            render_frame(None, 25.0, 60.0, 1_800, metric_scale=5)


if __name__ == "__main__":
    unittest.main()
