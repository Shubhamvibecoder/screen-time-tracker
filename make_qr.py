"""Turns a download link into a QR code image.

    py make_qr.py "https://drive.google.com/file/d/..../view"
    py make_qr.py "<link>" -o share.png --label "Screen Time - scan to download"

Anyone can point a phone camera at the result and land on the download page.
"""

import argparse
import os

import segno


def build(url, out_path, scale=10, label=None):
    qr = segno.make(url, error="h")  # high error correction: still scans if smudged
    if label:
        try:
            qr.save(out_path, scale=scale, border=3, dark="#1f6f5c")
            _add_label(out_path, label)
            return out_path
        except Exception:
            pass
    qr.save(out_path, scale=scale, border=3, dark="#1f6f5c")
    return out_path


def _add_label(path, label):
    """Caption underneath, only if Pillow happens to be installed."""
    from PIL import Image, ImageDraw

    qr = Image.open(path).convert("RGB")
    pad = 46
    canvas = Image.new("RGB", (qr.width, qr.height + pad), "white")
    canvas.paste(qr, (0, 0))
    draw = ImageDraw.Draw(canvas)
    box = draw.textbbox((0, 0), label)
    draw.text(((qr.width - (box[2] - box[0])) / 2, qr.height + 8), label, fill="#1f6f5c")
    canvas.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="the download link the QR should open")
    parser.add_argument("-o", "--out", default="share-qr.png")
    parser.add_argument("--scale", type=int, default=10, help="pixels per module")
    parser.add_argument("--label", default=None)
    args = parser.parse_args()

    if not args.url.lower().startswith(("http://", "https://")):
        raise SystemExit("the link must start with http:// or https://")

    path = build(args.url, args.out, args.scale, args.label)
    print("wrote %s (%d bytes)" % (path, os.path.getsize(path)))
    print("points to: %s" % args.url)


if __name__ == "__main__":
    main()
