"""抹掉管理员登录页背景图上**烘焙进去的旧 logo**。

背景图（design-assets/1/blue_city_skyline_login_background_*.png）里直接画了
「绿徽 + 烟踪智治 + SUPER ADMIN」这一组旧标识。把页面上的品牌 logo 统一成管理端
那张横版之后，背景里的旧 logo 就会和它叠成两个，必须去掉。

要点（第一版踩过的坑）：
  · 不能用饱和度自动找包围盒 —— 左边缘的水彩和底部城市剪影也会命中，
    结果把左边缘和剪影一起削平，还留下几条横向色带。
  · 抹除区用**固定比例**框定（两张图与设计稿同比例 16:9），
    填充用左右像素的**线性插值**而不是单色平均，否则会看到横向色带。
"""

from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BACKUP = Path.home() / "AppData/Local/Temp/yanzong-removed-20260927/login-bg-backup"
TARGETS = [
    "blue_city_skyline_login_background_ai_original.png",
    "blue_city_skyline_login_background_local_composite.png",
]

# 旧 logo 的横向/纵向范围（占整图比例，取自设计稿实测）
X0, X1 = 0.132, 0.404
Y0, Y1 = 0.062, 0.508
# 抹除区外扩（比例）
PAD_X, PAD_Y = 0.010, 0.014
# 取样点离抹除区的距离（比例）
SAMPLE = 0.012


def restore() -> None:
    """每次从备份重做，避免在已处理的图上二次处理。"""
    for name in TARGETS:
        src = BACKUP / name
        dst = ROOT / "public/design-assets/1" / name
        if src.exists():
            dst.write_bytes(src.read_bytes())
            print("restored:", name)
        else:
            print("backup missing:", name, file=sys.stderr)


def erase(img: Image.Image, name: str) -> None:
    w, h = img.size
    px = img.load()

    x0 = max(1, int(w * (X0 - PAD_X)))
    x1 = min(w - 2, int(w * (X1 + PAD_X)))
    y0 = max(1, int(h * (Y0 - PAD_Y)))
    y1 = min(h - 2, int(h * (Y1 + PAD_Y)))

    sl = max(2, int(w * SAMPLE))
    lx = max(0, x0 - sl)
    rx = min(w - 1, x1 + sl)
    span = x1 - lx + 1

    for y in range(y0, y1 + 1):
        left = px[lx, y]
        right = px[rx, y]
        for x in range(lx, x1 + 1):
            t = (x - lx) / span
            px[x, y] = tuple(int(left[k] * (1 - t) + right[k] * t) for k in range(3))

    img.save(ROOT / "public/design-assets/1" / name)
    print(f"  {name}: erased x[{x0},{x1}] y[{y0},{y1}] of {w}x{h}")


def main() -> None:
    restore()
    for name in TARGETS:
        path = ROOT / "public/design-assets/1" / name
        erase(Image.open(path).convert("RGB"), name)


if __name__ == "__main__":
    main()
