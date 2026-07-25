"""Generates icon.ico for the desktop shortcut. Pure stdlib (struct only).

Each size is rendered separately so small views stay sharp instead of being
downscaled by the shell. All entries use the classic 32bpp BMP form rather
than PNG compression: every Windows icon reader handles it, including the
older ones that silently fail on PNG-in-ICO and leave a blank shortcut.
"""

import math
import os
import struct

SIZES = (16, 20, 32, 48, 64, 128, 256)
SS = 4  # supersampling factor per axis
BG = (31, 111, 92)  # deep teal
FG = (255, 255, 255)


def _in_rounded_rect(x, y, size, margin, radius):
    left = top = margin
    right = bottom = size - margin
    if not (left <= x <= right and top <= y <= bottom):
        return False
    cx = min(max(x, left + radius), right - radius)
    cy = min(max(y, top + radius), bottom - radius)
    return math.hypot(x - cx, y - cy) <= radius


def _seg_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _sample(x, y, size):
    """(r, g, b, a) at one sub-sample point. Geometry scales with size."""
    k = size / 256.0
    if not _in_rounded_rect(x, y, size, 10 * k, 58 * k):
        return (0, 0, 0, 0)
    c = size / 2.0
    if abs(math.hypot(x - c, y - c) - 76 * k) <= 9 * k:
        return FG + (255,)
    hour = _seg_distance(x, y, c, c, c + 30 * k, c - 26 * k)
    minute = _seg_distance(x, y, c, c, c, c - 50 * k)
    if min(hour, minute) <= 8 * k:
        return FG + (255,)
    return BG + (255,)


def render(size):
    """Straight (non-premultiplied) RGBA rows, top-down."""
    out = bytearray()
    for py in range(size):
        for px in range(size):
            r = g = b = a = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    sr, sg, sb, sa = _sample(px + (sx + 0.5) / SS, py + (sy + 0.5) / SS, size)
                    r += sr * sa
                    g += sg * sa
                    b += sb * sa
                    a += sa
            if a <= 0:
                out += bytes(4)
            else:
                out += bytes(
                    (
                        min(255, round(r / a)),
                        min(255, round(g / a)),
                        min(255, round(b / a)),
                        min(255, round(a / (SS * SS))),
                    )
                )
    return bytes(out)


def to_bmp(pixels, size):
    """32bpp BGRA DIB: doubled height, bottom-up rows, then the AND mask."""
    header = struct.pack(
        "<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, size * size * 4, 0, 0, 0, 0
    )
    rows = []
    for y in range(size - 1, -1, -1):
        row = bytearray()
        for x in range(size):
            r, g, b, a = pixels[(y * size + x) * 4 : (y * size + x) * 4 + 4]
            row += bytes((b, g, r, a))
        rows.append(bytes(row))
    mask_stride = ((size + 31) // 32) * 4  # 1bpp, padded to 4 bytes
    return header + b"".join(rows) + bytes(mask_stride * size)


def build():
    images = [(size, to_bmp(render(size), size)) for size in SIZES]

    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, blob in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
        blobs += blob
    return struct.pack("<HHH", 0, 1, len(images)) + entries + blobs


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    data = build()
    with open(path, "wb") as handle:
        handle.write(data)
    print("wrote %s (%d bytes, sizes %s)" % (path, len(data), ", ".join(map(str, SIZES))))


if __name__ == "__main__":
    main()
