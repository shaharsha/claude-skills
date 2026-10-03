#!/usr/bin/env python3
"""Crop every face in a set of photos to its own square image, for use as --ref in character work.

  python3 crop_faces.py photos/ faces/ [--margin 0.6] [--min 120] [--sheet faces/_sheet.jpg]

Writes faces/<photo-stem>-<n>.png per detected face (largest first) and, with --sheet, a numbered contact
sheet so a human can say which crop is which person. Needs OpenCV: pip install opencv-python-headless.

Never pass whole photos as references: the edit endpoint restyles the photo (copies its pose, clothes and
background, even invents caption text) instead of drawing the person into your character.
"""
import argparse, os, sys


def expand_box(x, y, w, h, img_w, img_h, margin=0.6):
    """Square box around a face, grown by `margin` of the face size on every side, kept inside the image."""
    side = min(int(max(w, h) * (1 + 2 * margin)), img_w, img_h)
    cx, cy = x + w / 2, y + h / 2
    x0 = int(min(max(cx - side / 2, 0), img_w - side))
    y0 = int(min(max(cy - side / 2, 0), img_h - side))
    return x0, y0, side, side


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photos"); ap.add_argument("faces")
    ap.add_argument("--margin", type=float, default=0.6)
    ap.add_argument("--min", type=int, default=120, help="smallest face side in pixels")
    ap.add_argument("--sheet")
    a = ap.parse_args()
    try:
        import cv2
    except ImportError:
        sys.exit("needs OpenCV: pip install opencv-python-headless")
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    os.makedirs(a.faces, exist_ok=True)
    thumbs = []
    for f in sorted(os.listdir(a.photos)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")):
            continue
        img = cv2.imread(os.path.join(a.photos, f))
        if img is None:
            print(f"  {f}: unreadable (convert HEIC with: sips -s format jpeg in.heic --out out.jpg)")
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        found = casc.detectMultiScale(g, 1.1, 5, minSize=(a.min, a.min))
        if len(found) == 0:  # a strict pass misses tilted or small faces: retry leniently
            found = casc.detectMultiScale(g, 1.05, 3, minSize=(a.min, a.min))
        stem = os.path.splitext(f)[0]
        for n, (x, y, w, h) in enumerate(sorted(found, key=lambda r: -r[2] * r[3]), 1):
            x0, y0, s, _ = expand_box(x, y, w, h, img.shape[1], img.shape[0], a.margin)
            crop = img[y0:y0 + s, x0:x0 + s]
            out = os.path.join(a.faces, f"{stem}-{n}.png")
            cv2.imwrite(out, crop)
            thumbs.append((f"{stem}-{n}", cv2.resize(crop, (200, 200))))
        print(f"  {f}: {len(found)} face(s)")
    if a.sheet and thumbs:
        import numpy as np
        rows = []
        for i in range(0, len(thumbs), 6):
            row = [t.copy() for _, t in thumbs[i:i + 6]]
            for (label, _), t in zip(thumbs[i:i + 6], row):
                cv2.putText(t, label, (4, 194), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            row += [np.zeros_like(row[0])] * (6 - len(row))
            rows.append(np.hstack(row))
        cv2.imwrite(a.sheet, np.vstack(rows))
        print(f"  sheet: {a.sheet}")


if __name__ == "__main__":
    main()
