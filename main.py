#!/usr/bin/env python3
import cv2
import sys
import os
from PIL import Image
import numpy as np

# Target passport photo settings
PIX_W, PIX_H = 413, 531     # 35x45mm at 300 DPI
DPI = 300
HEAD_FACTOR = 0.72          # head ~72% of image height
BG_COLOR = (255, 255, 255)  # white

def detect_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))
    if len(faces) == 0:
        return None
    return max(faces, key=lambda r: r[2]*r[3])  # largest face

def process_image(infile, outfile):
    img = cv2.imread(infile)
    if img is None:
        raise ValueError(f"Could not read {infile}")

    h, w = img.shape[:2]
    face = detect_face(img)

    if face is not None:
        x, y, fw, fh = face
        desired_head = int(PIX_H * HEAD_FACTOR)
        scale = desired_head / fh if fh > 0 else 1.0
        crop_w = int(PIX_W / scale)
        crop_h = int(PIX_H / scale)
        cx, cy = x + fw // 2, y + fh // 2
        x1, y1 = max(0, cx - crop_w // 2), max(0, cy - crop_h // 2)
        x2, y2 = min(w, x1 + crop_w), min(h, y1 + crop_h)
        crop = img[y1:y2, x1:x2]
    else:
        # fallback: center crop 35:45 aspect ratio
        target_ar = PIX_W / PIX_H
        src_ar = w / h
        if src_ar > target_ar:
            new_w = int(h * target_ar)
            x1 = (w - new_w) // 2
            crop = img[:, x1:x1+new_w]
        else:
            new_h = int(w / target_ar)
            y1 = (h - new_h) // 2
            crop = img[y1:y1+new_h, :]

    # resize to passport size
    crop_resized = cv2.resize(crop, (PIX_W, PIX_H), interpolation=cv2.INTER_CUBIC)

    # paste on white background (ensures consistent background)
    canvas = np.full((PIX_H, PIX_W, 3), BG_COLOR, dtype=np.uint8)
    canvas[:,:,:] = crop_resized

    # save as JPEG with DPI
    im = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    im.save(outfile, "JPEG", dpi=(DPI,DPI), quality=95)
    print(f"✅ Saved {outfile} ({PIX_W}x{PIX_H} px, {DPI} DPI)")

def cli_mode():
    if len(sys.argv) != 3:
        print("Usage: make_passport_photo.py input.jpg output.jpg")
        sys.exit(1)
    process_image(sys.argv[1], sys.argv[2])

def gui_mode():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()

    infile = filedialog.askopenfilename(
        title="Select input photo",
        filetypes=[("Images", "*.jpg *.jpeg *.png")]
    )
    if not infile:
        return

    outdir = filedialog.askdirectory(title="Select output folder")
    if not outdir:
        return

    outfile = os.path.join(outdir, "passport_photo.jpg")
    try:
        process_image(infile, outfile)
        messagebox.showinfo("Done", f"Passport photo saved:\n{outfile}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    try:
        import tkinter
        if len(sys.argv) == 1:
            gui_mode()
        else:
            cli_mode()
    except ImportError:
        cli_mode()
