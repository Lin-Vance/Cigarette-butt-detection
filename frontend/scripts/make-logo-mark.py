"""从管理端品牌 logo 派生全站统一使用的两个图形资产。

产出：
  public/logo-horizontal.png  640x188 透明底横版（浅色背景通用：顶栏 / 登录页 / 预览）
  public/logo-mark.png        256x256 透明底方形圆徽（深色背景 / 应用图标）
  public/favicon.png          64x64   浏览器标签图标
  public/apple-touch-icon.png 180x180

品牌唯一标准是 design-assets/2/smoke_control_brand_logo.png（管理端顶栏所用），
其余位置的 logo 一律引用它或其衍生图形，不再各自为政。
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "public" / "design-assets" / "2" / "smoke_control_brand_logo.png"
OUT = ROOT / "public"


def to_transparent(img: Image.Image, threshold: int = 238) -> Image.Image:
    """把接近纯白的底转成透明，保留徽标本身。

    品牌图是白底 + 绿色圆环 + 蓝色城市。白底不去掉的话，
    放到浅蓝水彩背景（登录页）或深色顶栏上都会出现一个白方块。
    """
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if r >= threshold and g >= threshold and b >= threshold:
                px[x, y] = (r, g, b, 0)
            elif r > 215 and g > 215 and b > 215:
                # 边缘半透明过渡，避免锯齿
                k = (255 - max(r, g, b)) / (255 - threshold)
                px[x, y] = (r, g, b, int(255 * max(0.0, min(1.0, k))))
    return img


def tight(img: Image.Image) -> Image.Image:
    """裁掉四周空白，让图形撑满画布。"""
    box = img.getbbox()
    return img.crop(box) if box else img


def main() -> None:
    src = Image.open(SRC).convert("RGBA")

    # ---- 横版整标（含中文字）：保持 160:47 比例，只去白底 ----
    horizontal = tight(to_transparent(src))
    scale = 4  # 原图 160x47 偏小，放大保证高分屏清晰
    horizontal = horizontal.resize(
        (horizontal.width * scale, horizontal.height * scale), Image.LANCZOS
    )
    horizontal.save(OUT / "logo-horizontal.png")
    print(f"wrote logo-horizontal.png {horizontal.size}")

    # ---- 方形圆徽：取最左侧正方形（徽标部分） ----
    _, h = src.size
    mark = tight(to_transparent(src.crop((0, 0, h, h))))

    pad_ratio = 0.06  # 留白，避免标签栏里顶到边
    for name, size in (("logo-mark.png", 256), ("favicon.png", 64), ("apple-touch-icon.png", 180)):
        inner = int(size * (1 - pad_ratio * 2))
        square = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
        resized = mark.resize((inner, inner), Image.LANCZOS)
        square.paste(resized, (0, 0), resized)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        off = (size - inner) // 2
        canvas.paste(square, (off, off), square)
        canvas.save(OUT / name)
        print(f"wrote {name} {size}x{size}")

    print("source:", SRC.relative_to(ROOT), src.size)


if __name__ == "__main__":
    main()
