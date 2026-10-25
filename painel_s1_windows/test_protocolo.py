import unittest
from datetime import datetime

from protocolo import (
    CHUNK_BYTES,
    FRAME_BYTES,
    HID_REPORT_BYTES,
    build_heartbeat_report,
    build_hid_reports,
    build_orientation_report,
    build_refresh_reports,
    build_test_frame,
)


class ProtocolTests(unittest.TestCase):
    def test_test_frame_has_expected_size(self):
        self.assertEqual(len(build_test_frame()), FRAME_BYTES)

    def test_heartbeat_report_contains_local_time_and_expected_size(self):
        report = build_heartbeat_report(datetime(2026, 10, 24, 22, 0, 37))

        self.assertEqual(len(report), HID_REPORT_BYTES)
        self.assertEqual(report[:7], bytes.fromhex("0055A1F2160025"))
        self.assertEqual(report[7:], bytes(HID_REPORT_BYTES - 7))

    def test_orientation_reports_use_supported_firmware_commands(self):
        landscape = build_orientation_report("landscape")
        portrait = build_orientation_report("portrait")

        self.assertEqual(landscape[:5], bytes.fromhex("0055A1F101"))
        self.assertEqual(portrait[:5], bytes.fromhex("0055A1F102"))
        self.assertEqual(len(landscape), HID_REPORT_BYTES)
        self.assertEqual(len(portrait), HID_REPORT_BYTES)

    def test_orientation_report_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            build_orientation_report("diagonal")

    def test_frame_is_split_into_hid_reports(self):
        reports = build_hid_reports(build_test_frame())
        self.assertEqual(len(reports), 27)
        self.assertTrue(all(len(report) == HID_REPORT_BYTES for report in reports))
        self.assertTrue(all(report[0] == 0 for report in reports))

    def test_first_middle_and_last_packet_headers(self):
        reports = build_hid_reports(build_test_frame())
        first_packet = reports[0][1:]
        middle_packet = reports[1][1:]
        last_packet = reports[-1][1:]

        self.assertEqual(first_packet[:8], bytes.fromhex("55A3F00100000010"))
        self.assertEqual(
            middle_packet[:8],
            bytes.fromhex("55A3F10200100010"),
        )
        self.assertEqual(last_packet[:8], bytes.fromhex("55A3F21B00A00009"))
        self.assertEqual(int.from_bytes(last_packet[6:8], "little"), 2304)
        self.assertEqual(
            int.from_bytes(middle_packet[4:6], "little"),
            CHUNK_BYTES,
        )

    def test_rejects_wrong_frame_length(self):
        with self.assertRaises(ValueError):
            build_hid_reports(b"too short")

    def test_metric_updates_use_seven_bounded_refresh_reports(self):
        frame = bytes(index % 256 for index in range(FRAME_BYTES))
        reports = build_refresh_reports(frame)

        self.assertEqual(len(reports), 7)
        self.assertTrue(all(len(report) == HID_REPORT_BYTES for report in reports))
        self.assertEqual(reports[0][:9], bytes.fromhex("0055A20C002700910E"))
        pixel_offset = (39 * 320 + 12) * 2
        self.assertEqual(
            reports[0][9:11],
            frame[pixel_offset : pixel_offset + 2],
        )

    def test_metric_updates_reject_wrong_frame_length(self):
        with self.assertRaises(ValueError):
            build_refresh_reports(b"too short")

    def test_metric_updates_send_only_changed_regions_when_baseline_is_known(self):
        previous = bytearray(FRAME_BYTES)
        current = bytearray(previous)
        x, y = 17, 22
        current[(y * 320 + x) * 2 : (y * 320 + x + 2) * 2] = b"\xff\xff" * 2
        current[((y + 1) * 320 + x) * 2 : ((y + 1) * 320 + x + 2) * 2] = (
            b"\xff\xff" * 2
        )

        reports = build_refresh_reports(bytes(current), bytes(previous))

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][:9], bytes.fromhex("0055A2110016000202"))
        self.assertEqual(reports[0][9:17], b"\xff\xff" * 4)
        self.assertEqual(build_refresh_reports(bytes(current), bytes(current)), [])

    def test_changed_full_frame_regions_stay_within_hid_payload_limit(self):
        reports = build_refresh_reports(bytes([0xff]) * FRAME_BYTES, bytes(FRAME_BYTES))

        self.assertGreater(len(reports), 1)
        for report in reports:
            width = report[7]
            height = report[8]
            self.assertLessEqual(width * height * 2, 4096)
            self.assertEqual(len(report), HID_REPORT_BYTES)


if __name__ == "__main__":
    unittest.main()
