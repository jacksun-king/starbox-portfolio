# -*- coding: utf-8 -*-
"""星匣 · 图像能力：水印样片 / 主色提取 / EXIF / 竖版长图。

全部基于 Pillow，Pillow 缺失时降级为 no-op，不影响站点启动。
"""
import colorsys
import os

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
    PIL_OK = True
except Exception:
    PIL_OK = False

FONT_CANDIDATES = [
    (r'C:\Windows\Fonts\msyhbd.ttc', 0),
    (r'C:\Windows\Fonts\msyh.ttc', 0),
    (r'C:\Windows\Fonts\simhei.ttf', 0),
    (r'C:\Windows\Fonts\segoeuib.ttf', 0),
    ('/System/Library/Fonts/PingFang.ttc', 0),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 0),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 0),
]

_FONT = None


def font(size):
    global _FONT
    if not PIL_OK:
        return None
    if _FONT is None:
        for path, idx in FONT_CANDIDATES:
            if os.path.isfile(path):
                try:
                    _FONT = (path, idx)
                    break
                except Exception:
                    continue
    if not _FONT:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(_FONT[0], size, index=_FONT[1])
    except Exception:
        try:
            return ImageFont.truetype(_FONT[0], size)
        except Exception:
            return ImageFont.load_default()


def _open(src):
    im = Image.open(src)
    try:
        im = ImageOps.exif_transpose(im)
    except Exception:
        pass
    return im


def _watermark_layer(size, text, fs=30, angle=26, gap=96, opacity=104):
    """生成斜向平铺水印层（RGBA）。白字 + 暗描边，亮暗背景都看得见。"""
    f = font(fs)
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    try:
        tw = int(probe.textlength(text, font=f))
    except Exception:
        tw = fs * len(text)
    tw = max(tw, fs * 4)
    pad = fs
    tile = Image.new('RGBA', (tw + pad * 2, fs * 2 + pad), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    try:
        td.text((pad, pad // 2), text, font=f, fill=(255, 255, 255, opacity),
                stroke_width=max(1, fs // 22), stroke_fill=(12, 12, 14, 92))
    except Exception:
        td.text((pad, pad // 2), text, font=f, fill=(255, 255, 255, opacity))
    tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    tw2, th2 = tile.size
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    step_x = tw2 + int(gap * 0.5)
    step_y = th2 + gap
    y = -th2
    while y < size[1] + th2:
        x = -tw2
        while x < size[0] + tw2:
            layer.alpha_composite(tile, (int(x), int(y)))
            x += step_x
        y += step_y
    return layer


def make_preview(src, dst, max_side=1680, text='', quality=86):
    """生成展示用图：限边 + 可选水印。返回 (w, h, watermark_applied)。"""
    if not PIL_OK:
        return (0, 0, False)
    try:
        im = _open(src).convert('RGB')
        w, h = im.size
        scale = min(1.0, float(max_side) / max(w, h))
        if scale < 1.0:
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        if text:
            im = im.convert('RGBA')
            fs = max(22, min(48, int(im.size[0] * 0.032)))
            im.alpha_composite(_watermark_layer(im.size, text, fs=fs, gap=max(70, fs * 2)))
            im = im.convert('RGB')
        im.save(dst, 'JPEG', quality=quality, optimize=True)
        return im.size[0], im.size[1], bool(text)
    except Exception:
        return (0, 0, False)


def dimension(src):
    if not PIL_OK:
        return (0, 0)
    try:
        with Image.open(src) as im:
            return im.size
    except Exception:
        return (0, 0)


def dominant_color(src, fallback='#d4af7a'):
    """提一个有辨识度的强调色，向可读区间拉。"""
    if not PIL_OK:
        return fallback
    try:
        im = _open(src).convert('RGB')
        im.thumbnail((96, 96))
        q = im.quantize(colors=10, method=Image.MEDIANCUT)
        pal = q.getpalette() or []
        entries = q.getcolors() or []
        total = sum(n for n, _ in entries) or 1
        best, best_score = None, -1.0
        for cnt, idx in entries:
            r, g, b = pal[idx * 3:idx * 3 + 3]
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if vv < 0.14 or vv > 0.975:
                continue
            if ss < 0.10:
                continue
            weight = cnt / total
            score = weight * (0.35 + ss) * (1.0 - abs(vv - 0.62) * 1.1)
            if score > best_score:
                best_score, best = score, (hh, ss, vv)
        if not best:
            return fallback
        hh, ss, vv = best
        ss = max(0.28, min(0.82, ss))
        vv = max(0.62, min(0.86, vv if vv > 0.5 else vv + 0.28))
        r, g, b = colorsys.hsv_to_rgb(hh, ss, vv)
        return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))
    except Exception:
        return fallback


def _ratio(v):
    try:
        f = float(v)
    except Exception:
        return ''
    if f <= 0:
        return ''
    if f < 1:
        return '1/%d' % int(round(1 / f))
    return ('%g' % round(f, 1)) + 's'


def read_exif(src):
    """读取常用拍摄参数，返回 dict（无数据则为空）。"""
    if not PIL_OK:
        return {}
    out = {}
    try:
        im = Image.open(src)
        ex = im.getexif()
        if not ex:
            return {}
        make = str(ex.get(271) or '').strip()
        model = str(ex.get(272) or '').strip()
        camera = ' '.join([x for x in (make, model) if x])
        if camera:
            out['camera'] = camera[:60]
        sub = ex.get_ifd(0x8769) if hasattr(ex, 'get_ifd') else {}
        if sub:
            fn = sub.get(33437)
            if fn:
                try:
                    out['aperture'] = 'f/%g' % round(float(fn), 1)
                except Exception:
                    pass
            et = sub.get(33434)
            if et:
                s = _ratio(et)
                if s:
                    out['shutter'] = s
            iso = sub.get(34855)
            if iso:
                try:
                    val = iso[0] if isinstance(iso, (list, tuple)) else iso
                    out['iso'] = 'ISO %d' % int(val)
                except Exception:
                    pass
            fl = sub.get(37386)
            if fl:
                try:
                    out['focal'] = '%dmm' % int(round(float(fl)))
                except Exception:
                    pass
            lens = sub.get(42036)
            if lens:
                out['lens'] = str(lens).strip()[:60]
        taken = ex.get(36867) or ex.get(306)
        if taken:
            out['taken'] = str(taken).replace(':', '-', 2)[:19]
    except Exception:
        return {}
    return out


def _cover_crop(im, box_w, box_h):
    return ImageOps.fit(im.convert('RGB'), (box_w, box_h), method=Image.LANCZOS, centering=(0.5, 0.42))


def _wrap(draw, text, fnt, max_w, max_lines):
    lines, cur = [], ''
    for ch in text:
        if ch == '\n':
            lines.append(cur)
            cur = ''
            continue
        trial = cur + ch
        try:
            w = draw.textlength(trial, font=fnt)
        except Exception:
            w = len(trial) * 20
        if w > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if lines and len(lines) == max_lines:
        last = lines[-1]
        try:
            if draw.textlength(last + '…', font=fnt) < max_w:
                lines[-1] = last
            else:
                lines[-1] = last[:-1] + '…'
        except Exception:
            pass
    return lines


def build_poster(dst, cover_path, title, subtitle, story, thumbs, accent='#d4af7a', footer=''):
    """生成 1080 宽竖版长图（用于小红书/朋友圈/微博）。"""
    if not PIL_OK:
        return False
    W = 1080
    pad = 56
    inner = W - pad * 2

    f_title = font(66)
    f_sub = font(30)
    f_body = font(30)
    f_small = font(24)
    f_grid = font(22)

    title_lines = []
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    title_lines = _wrap(probe, title or '作品集', f_title, inner, 3)
    story_lines = _wrap(probe, story or '', f_body, inner, 4) if story else []
    sub_lines = _wrap(probe, subtitle or '', f_sub, inner, 2) if subtitle else []

    cover_h = 1120
    h = cover_h + 60 + len(title_lines) * 84 + (len(sub_lines) * 44 + 18 if sub_lines else 0)
    h += (len(story_lines) * 50 + 40) if story_lines else 0
    cols = 3
    cell = (inner - 16 * (cols - 1)) // cols
    cp = os.path.realpath(cover_path) if cover_path else ''
    seq = [p for p in (thumbs or []) if os.path.realpath(p) != cp][:9]
    if not seq:
        seq = list(thumbs or [])[:9]
    rows = max(1, (len(seq) + cols - 1) // cols) if seq else 0
    grid_h = rows * cell + (rows - 1) * 16 if seq else 0
    h += (grid_h + 46) if seq else 0
    h += 140

    canvas = Image.new('RGB', (W, h), (12, 13, 17))
    d = ImageDraw.Draw(canvas)

    # 封面
    if cover_path and os.path.isfile(cover_path):
        try:
            cov = _cover_crop(_open(cover_path), W, cover_h)
            canvas.paste(cov, (0, 0))
            shade = Image.new('L', (1, cover_h))
            for y in range(cover_h):
                t = y / float(cover_h)
                shade.putpixel((0, y), int(255 * max(0.0, (t - 0.35) / 0.65) ** 1.6))
            shade = shade.resize((W, cover_h))
            canvas.paste(Image.new('RGB', (W, cover_h), (12, 13, 17)), (0, 0), shade)
            # 顶部压暗，保证白色标记在亮天空上也可读
            top = Image.new('L', (1, 170))
            for yy in range(170):
                top.putpixel((0, yy), int(155 * (1 - yy / 170.0) ** 1.35))
            canvas.paste(Image.new('RGB', (W, 170), (10, 11, 14)), (0, 0), top.resize((W, 170)))
        except Exception:
            pass

    # 顶部标记
    d.rectangle([pad, 58, pad + 46, 62], fill=accent)
    d.text((pad, 82), 'STARBOX  ·  PORTFOLIO', font=f_small, fill=(235, 230, 220))
    y = cover_h - 40

    for ln in title_lines:
        d.text((pad, y), ln, font=f_title, fill=(246, 242, 234))
        y += 84
    y += 10
    for ln in sub_lines:
        d.text((pad, y), ln, font=f_sub, fill=(178, 174, 165))
        y += 44
    if sub_lines:
        y += 18
    for ln in story_lines:
        d.text((pad, y), ln, font=f_body, fill=(198, 193, 183))
        y += 50
    if story_lines:
        y += 40

    # 网格
    if seq:
        for i, p in enumerate(seq):
            cx = pad + (i % cols) * (cell + 16)
            cy = y + (i // cols) * (cell + 16)
            try:
                canvas.paste(_cover_crop(_open(p), cell, cell), (cx, cy))
            except Exception:
                d.rectangle([cx, cy, cx + cell, cy + cell], fill=(26, 27, 33))
        y += grid_h + 46

    # 底部
    d.rectangle([pad, y + 6, pad + 46, y + 10], fill=accent)
    d.text((pad, y + 26), footer or '星匣 · 私人作品集', font=f_small, fill=(160, 156, 148))
    try:
        canvas.save(dst, 'JPEG', quality=90, optimize=True)
        return True
    except Exception:
        return False
