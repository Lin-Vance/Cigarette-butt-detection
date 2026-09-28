# -*- coding: utf-8 -*-
"""处理 ImageGen 产物：裁水印、logo 透明化、横版 logo 组合、favicon。"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = r'C:\Users\20262\Desktop\烟头行为监测'
GEN = os.path.join(ROOT, 'generated-images')
MEDIA = os.path.join(ROOT, 'frontend', 'public', 'media')
PUBLIC = os.path.join(ROOT, 'frontend', 'public')
os.makedirs(MEDIA, exist_ok=True)

def crop_watermark(im, bottom=72, right=8):
    """裁掉右下角 AI 生成水印（构图底部留白充足，裁 72px 无损失）。"""
    w, h = im.size
    return im.crop((0, 0, w - right, h - bottom))

def save_banner(src, dst):
    im = Image.open(os.path.join(GEN, src)).convert('RGB')
    im = crop_watermark(im)
    im.save(os.path.join(MEDIA, dst), optimize=True)
    print('banner', dst, im.size)

def save_thumb(src, dst, bottom=64):
    im = Image.open(os.path.join(GEN, src)).convert('RGB')
    im = crop_watermark(im, bottom=bottom)
    im.save(os.path.join(MEDIA, dst), optimize=True)
    print('thumb', dst, im.size)

# ---------- 1) 轮播图 ----------
save_banner('Wide_flat_vector_illustration__2026-09-27T14-55-38.png', 'banner-park.png')
save_banner('Wide_flat_vector_illustration__2026-09-27T14-56-12.png', 'banner-shoot.png')
save_banner('Wide_flat_vector_illustration__2026-09-27T14-56-16.png', 'banner-dawn.png')

# ---------- 2) 科普封面 ----------
save_thumb('Flat_vector_editorial_illustra_2026-09-27T14-56-41.png', 'sci-soil.png')
save_thumb('Flat_vector_editorial_illustra_2026-09-27T14-56-40.png', 'sci-fire.png')
save_banner('Flat_vector_infographic_style__2026-09-27T14-57-16.png', 'sci-life.png')

# ---------- 3) 环卫端 / 积分 ----------
save_banner('Wide_flat_vector_illustration__2026-09-27T14-57-20.png', 'worker-team.png')
save_thumb('Flat_vector_illustration__a_sh_2026-09-27T14-57-49.png', 'medal.png')
save_thumb('Flat_vector_illustration__a_ne_2026-09-27T14-57-50.png', 'coins.png')

# ---------- 4) logo ----------
logo = Image.open(os.path.join(GEN, 'Minimalist_flat_vector_logo_ma_2026-09-27T14-55-39.png')).convert('RGBA')

# 4a) 白底 -> 透明（近白像素按距离阈值转 alpha）
px = logo.load()
w, h = logo.size
for y in range(h):
    for x in range(w):
        r, g, b, a = px[x, y]
        m = min(r, g, b)
        if m > 238:
            px[x, y] = (r, g, b, 0)
        elif m > 214:
            px[x, y] = (r, g, b, int(255 * (238 - m) / 24))

# 4b) 按 alpha 裁剪 bbox
alpha = logo.getchannel('A')
bbox = alpha.getbbox()
logo = logo.crop(bbox)

# 4c) 清理边缘杂色 + 缩放
logo = logo.resize((512, int(512 * logo.size[1] / logo.size[0])), Image.LANCZOS)
logo.save(os.path.join(PUBLIC, 'logo-mark.png'))
print('logo-mark', logo.size)

# 4d) 横版组合：mark + 烟踪智治
def font(size, bold=True):
    p = r'C:\Windows\Fonts\msyhbd.ttc' if bold else r'C:\Windows\Fonts\msyh.ttc'
    return ImageFont.truetype(p, size)

SCALE = 4  # 超采样抗锯齿
mark_h = 44 * SCALE
mark = logo.resize((int(logo.size[0] * mark_h / logo.size[1]), mark_h), Image.LANCZOS)
text = '烟踪智治'
f = font(30 * SCALE)
tmp = Image.new('RGBA', (10, 10))
d = ImageDraw.Draw(tmp)
tb = d.textbbox((0, 0), text, font=f)
tw, th = tb[2] - tb[0], tb[3] - tb[1]
pad_x = 12 * SCALE
W = mark.size[0] + pad_x + tw + 2 * SCALE
H = (mark_h + 4 * SCALE)
canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
canvas.paste(mark, (0, (H - mark_h) // 2), mark)
d = ImageDraw.Draw(canvas)
d.text((mark.size[0] + pad_x - tb[0], (H - th) // 2 - tb[1]), text, font=f, fill=(23, 40, 62, 255))
canvas = canvas.resize((W // SCALE, H // SCALE), Image.LANCZOS)
canvas.save(os.path.join(PUBLIC, 'logo-horizontal.png'))
print('logo-horizontal', canvas.size)

# 4e) favicon / apple-touch-icon
fav = logo.resize((48, 48), Image.LANCZOS)
fav.save(os.path.join(PUBLIC, 'favicon.png'))
touch = Image.new('RGBA', (180, 180), (255, 255, 255, 255))
m2 = logo.resize((150, int(150 * logo.size[1] / logo.size[0])), Image.LANCZOS)
touch.paste(m2, ((180 - m2.size[0]) // 2, (180 - m2.size[1]) // 2), m2)
touch.save(os.path.join(PUBLIC, 'apple-touch-icon.png'))
print('favicon & touch icon ok')
