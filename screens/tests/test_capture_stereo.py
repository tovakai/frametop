#!/usr/bin/env python3
"""Offline, dependency-free tests for Frametop ScreenShot2 -> P6 conversion."""
import importlib.util
from io import BytesIO
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "test" / "capture-stereo.py"
spec = importlib.util.spec_from_file_location("capture_stereo", SOURCE)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CaptureTests(unittest.TestCase):
    def convert(self, data, width, height, stride, fmt, max_w=2048, max_h=1152):
        target = BytesIO()
        dimensions = capture.convert_stream(
            BytesIO(data), target, width, height, stride, fmt, max_w, max_h
        )
        return dimensions, target.getvalue()

    def test_bgra_and_row_padding(self):
        # Qt ARGB32 (format 5) in little-endian BGRA byte order.
        data = bytes((3, 2, 1, 255, 6, 5, 4, 255, 99, 99, 99, 99))
        shape, ppm = self.convert(data, 2, 1, 12, 5)
        self.assertEqual(shape, (2, 1))
        self.assertEqual(ppm, b"P6\n2 1\n255\n" + bytes((1, 2, 3, 4, 5, 6)))

    def test_rgba(self):
        data = bytes((1, 2, 3, 255, 4, 5, 6, 255))
        shape, ppm = self.convert(data, 2, 1, 8, 16)
        self.assertEqual(shape, (2, 1))
        self.assertEqual(ppm, b"P6\n2 1\n255\n" + bytes((1, 2, 3, 4, 5, 6)))

    def test_downscale_to_safe_bound(self):
        data = bytes((10, 11, 12, 0, 20, 21, 22, 0,
                      30, 31, 32, 0, 40, 41, 42, 0)) * 2
        shape, ppm = self.convert(data, 4, 2, 16, 16, 2, 1)
        self.assertEqual(shape, (2, 1))
        self.assertEqual(ppm, b"P6\n2 1\n255\n" + bytes((10, 11, 12, 30, 31, 32)))

    def test_truncated(self):
        with self.assertRaisesRegex(ValueError, "ended"):
            self.convert(b"\x00" * 4, 2, 1, 8, 16)

    def test_reject_bad_format_and_stride(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            self.convert(b"\x00" * 8, 2, 1, 8, 7)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            self.convert(b"\x00" * 8, 2, 1, 4, 16)


if __name__ == "__main__":
    unittest.main()
