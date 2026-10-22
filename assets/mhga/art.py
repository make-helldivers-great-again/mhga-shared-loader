#!/usr/bin/env python3
"""Draws the MHGA Shared Loader README banner (2172x724) and box icon (1254x1254) in code.

Same visual system as the upstream Bingus Shared Loader artwork (see ../ARTWORK.md): pure typography on a
distressed charcoal ground, wide heavy cream and yellow block type, clipped yellow border rules, three yellow
hazard slashes, yellow wear in the corners and a small letter-spaced footer. Deterministic: the same inputs give
the same pixels. Needs Pillow, NumPy, SciPy and the OFL fonts in ./fonts (Archivo Black for the title, Barlow
Condensed SemiBold for the footer; licenses alongside).

    python art.py banner [--out banner.png] [--footer TEXT]
    python art.py icon   [--out thumbnail.png] [--footer TEXT]
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter

GROUND = np.array([18, 17, 16], float)        # #121110
CREAM = np.array([240, 232, 214], float)      # #f0e8d6
YELLOW = np.array([253, 208, 12], float)      # #fdd00c
HERE = Path(__file__).resolve().parent
FOOTER = 'Fork of Bingus Shared Loader by CowboyBingus'
SEED = 1984
SQUEEZE = 0.80   # horizontal squeeze of the wide title face


def field(rng, size, sigma):
    n = gaussian_filter(rng.standard_normal((size[1], size[0])), sigma)
    return n / n.std()


def corner_weight(size):
    w, h = size
    y, x = np.mgrid[0:h, 0:w]
    dx = np.minimum(x, w - 1 - x) / (w * 0.13)
    dy = np.minimum(y, h - 1 - y) / (h * 0.40)
    return np.exp(-(dx ** 2.2 + dy ** 2.2) ** 0.5 * 2.3)


def texture(rng, size):
    w, h = size
    lum = (0.4 * field(rng, size, 1.1) + 0.45 * field(rng, size, 3.5) + 1.0 * field(rng, size, 14)
           + 0.9 * field(rng, size, 55) + 0.6 * field(rng, size, 160))
    img = GROUND[None, None, :] + lum[..., None] * 6.5
    speck = rng.random((h, w))
    img += ((speck > 0.9795) * rng.uniform(25, 85, (h, w)))[..., None]
    img -= ((speck < 0.012) * rng.uniform(6, 14, (h, w)))[..., None]
    layer = Image.new('L', size, 0)
    d = ImageDraw.Draw(layer)
    for _ in range(int(380 * w * h / (2172 * 724))):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        a = np.deg2rad(rng.uniform(36, 56))
        ln = rng.uniform(30, 280)
        d.line([(x, y), (x + ln * np.cos(a), y - ln * np.sin(a))], fill=int(rng.uniform(25, 85)), width=1)
    img += gaussian_filter(np.asarray(layer, float), 0.55)[..., None] * 0.5
    wear = Image.new('L', size, 0)
    d = ImageDraw.Draw(wear)
    cw = corner_weight(size)
    for _ in range(int(16000 * w * h / (2172 * 724))):
        x, y = int(rng.uniform(0, w)), int(rng.uniform(0, h))
        if rng.random() < cw[y, x] * 0.95:
            if rng.random() < 0.35:
                a = np.deg2rad(rng.uniform(38, 58)); ln = rng.uniform(6, 70)
                d.line([(x, y), (x + ln * np.cos(a), y - ln * np.sin(a))], fill=int(rng.uniform(70, 210)), width=1)
            else:
                r = rng.uniform(0.4, 1.8)
                d.ellipse([x - r, y - r, x + r, y + r], fill=int(rng.uniform(80, 230)))
    wear = np.asarray(wear, float) / 255.0 * 0.85
    img = img * (1 - wear[..., None]) + YELLOW[None, None, :] * 0.9 * wear[..., None]
    y, x = np.mgrid[0:h, 0:w]
    vig = 1 - 0.30 * (((x - w / 2) / (w / 2)) ** 2 * 0.7 + ((y - h / 2) / (h / 2)) ** 2 * 0.5)
    return img * vig[..., None]


def worn(rng, size, alpha):
    n = field(rng, size, 0.9) + 0.6 * field(rng, size, 3.0)
    return alpha * np.clip(1.25 - (n > 1.35) * 1.0 - (n > 1.9) * 1.0, 0.0, 1.0)


def fit_font(path, text, target_w):
    lo, hi = 20, 700
    while hi - lo > 1:
        mid = (lo + hi) // 2
        f = ImageFont.truetype(str(path), mid)
        b = f.getbbox(text)
        if b[2] - b[0] > target_w:
            hi = mid
        else:
            lo = mid
    return ImageFont.truetype(str(path), lo)


def title_layer(size, path, text, target_w, cx, top, font=None, squeeze=SQUEEZE):
    """A title line fitted to target_w after the horizontal squeeze (taller, heavier letters)."""
    font = font or fit_font(path, text, target_w / squeeze)
    b = font.getbbox(text)
    w, h = b[2] - b[0], b[3] - b[1]
    tmp = Image.new('L', (w, h), 0)
    ImageDraw.Draw(tmp).text((-b[0], -b[1]), text, font=font, fill=255)
    tmp = tmp.resize((round(w * squeeze), h), Image.LANCZOS)
    layer = Image.new('L', size, 0)
    layer.paste(tmp, (round(cx - tmp.width / 2), round(top)))
    return np.asarray(layer, float) / 255.0, h, font


def distress(rng, size, mask):
    cracks = (np.abs(field(rng, size, 2.2)) < 0.07) * (field(rng, size, 9) > 0.1)
    pits = field(rng, size, 0.8) > 2.6
    cut = np.clip(cracks * 0.85 + pits * 0.9, 0, 1)
    return mask * (1 - cut), 0.93 + 0.05 * field(rng, size, 5) + 0.03 * field(rng, size, 1.0)


def footer_mask(size, font, text, cx, cy, tracking):
    widths = [font.getlength(c) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    layer = Image.new('L', size, 0)
    d = ImageDraw.Draw(layer)
    x = cx - total / 2
    for c, wd in zip(text, widths):
        d.text((x, cy), c, font=font, fill=255, anchor='lm')
        x += wd + tracking
    return np.asarray(layer, float) / 255.0, total


def compose(size, rng, lines, footer, foot_y, foot_size, rules, squeeze=SQUEEZE, center_y=None, same_font=None):
    """lines: [(text, color, target_w, top)] stacked and centred. With same_font=(text, width) every line uses the
    font that fits that text to that width (equal letter height); with center_y the block is centred there."""
    w, h = size
    img = texture(rng, size)
    cx = w / 2
    path = HERE / 'fonts' / 'ArchivoBlack-Regular.ttf'
    shared = fit_font(path, same_font[0], same_font[1] / squeeze) if same_font else None
    fonts = [shared or fit_font(path, t, tw / squeeze) for t, _, tw, _ in lines]
    heights = [f.getbbox(t)[3] - f.getbbox(t)[1] for f, (t, _, _, _) in zip(fonts, lines)]
    gap = 8
    top = lines[0][3] if center_y is None else center_y - (sum(heights) + gap * (len(lines) - 1)) / 2
    layers = []
    for (text, color, tw, _), font, lh in zip(lines, fonts, heights):
        m, _, _ = title_layer(size, path, text, tw, cx, top, font=font, squeeze=squeeze)
        layers.append((m, color))
        top += lh + gap
    shadow = gaussian_filter(np.roll(np.roll(np.maximum.reduce([m for m, _ in layers]), 9, axis=0), 6, axis=1), 11)
    img *= (1 - 0.7 * shadow)[..., None]
    for m, color in layers:
        md, tone = distress(rng, size, gaussian_filter(m, 0.7))
        img = img * (1 - md[..., None]) + color[None, None, :] * tone[..., None] * md[..., None]
    foot_font = ImageFont.truetype(str(HERE / 'fonts' / 'BarlowCondensed-SemiBold.ttf'), foot_size)
    fm, foot_w = footer_mask(size, foot_font, footer, cx, foot_y, 6.0 if foot_size > 36 else 4.5)
    fm = gaussian_filter(fm, 0.5)
    img = img * (1 - fm[..., None]) + CREAM[None, None, :] * 0.96 * fm[..., None]
    layer = Image.new('L', size, 0)
    rules(ImageDraw.Draw(layer), foot_w)
    a = worn(rng, size, np.asarray(layer.filter(ImageFilter.GaussianBlur(0.6)), float) / 255.0)
    img = img * (1 - a[..., None]) + YELLOW[None, None, :] * a[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB')


def slashes(d, x0, y0, y1, count=3, pitch=76, width=46, skew=32):
    for i in range(count):
        a = x0 + i * pitch
        d.polygon([(a, y1), (a + width, y1), (a + width + skew, y0), (a + skew, y0)], fill=255)


def banner(out, footer):
    size = (2172, 724)

    def rules(d, foot_w):
        d.line([(0, 76), (1925, 76), (2008, 155), (2172, 155)], fill=255, width=5, joint='curve')
        d.line([(0, 568), (372, 568), (423, 626), (2172, 626)], fill=255, width=5, joint='curve')
        slashes(d, 78, 600, 647)
    lines = [('MHGA Shared', CREAM, 1500, 104), ('Loader', YELLOW, 980, 0)]
    compose(size, np.random.default_rng(SEED), lines, footer, 594, 44, rules).save(out, optimize=True)


def icon(out, footer):
    size = (1254, 1254)

    def rules(d, foot_w):
        gap = foot_w / 2 + 26
        c, m, ch, by = 1254 / 2, 30, 56, 1254 - 30 - 50     # centre, inset, chamfer, bottom-rule y
        d.line([(m, 470), (m, m + ch), (m + ch, m), (470, m)], fill=255, width=5, joint='curve')
        d.line([(760, m), (1254 - m - ch, m), (1254 - m, m + ch), (1254 - m, by - ch), (1254 - m - ch, by), (c + gap, by)],
               fill=255, width=5, joint='curve')
        d.line([(m, 840), (m, by - 40), (m + 70, by + 20), (c - gap, by + 20)], fill=255, width=5, joint='curve')
        slashes(d, 84, 1104, 1146, pitch=66, width=30, skew=24)
    lines = [('MHGA', CREAM, 0, 0), ('SHARED', CREAM, 0, 0), ('LOADER', YELLOW, 0, 0)]
    compose(size, np.random.default_rng(SEED), lines, footer, 1198, 30, rules,
            squeeze=0.56, center_y=600, same_font=('SHARED', 1000)).save(out, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['banner', 'icon'])
    ap.add_argument('--out')
    ap.add_argument('--footer', default=FOOTER)
    a = ap.parse_args()
    out = a.out or str(HERE / ('banner.png' if a.kind == 'banner' else 'thumbnail.png'))
    (banner if a.kind == 'banner' else icon)(out, a.footer)
    print('wrote', out)


if __name__ == '__main__':
    main()
