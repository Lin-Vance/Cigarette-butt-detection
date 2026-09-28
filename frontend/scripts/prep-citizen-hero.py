"""整理市民端首屏插画：裁掉右下角的生成水印，规范文件名。

生成图带「AI 生成」角标，裁掉即可（页面里会在 alt 与说明文字中明确标注这是示意图，
不冒充现场照片）。
"""

import glob
import os
from pathlib import Path

from PIL import Image

MEDIA = Path(__file__).resolve().parent.parent / "public/media"
TARGET = MEDIA / "citizen-hero.png"
# 水印位于右下角，图上统一裁掉底部约 15%（同时把过空的路面一起收掉，构图更紧）
KEEP_RATIO = 0.84


def main() -> None:
    srcs = [p for p in glob.glob(str(MEDIA / "A_bright*.png"))]
    if not srcs:
        print("找不到生成的插画，跳过。")
        return
    src = max(srcs, key=os.path.getmtime)

    img = Image.open(src).convert("RGB")
    w, h = img.size
    keep = int(h * KEEP_RATIO)
    out = img.crop((0, 0, w, keep))
    out.save(TARGET)
    print(f"{Path(src).name} {w}x{h} -> {TARGET.name} {out.size}")

    for p in srcs:
        Path(p).unlink()
        print("removed source:", Path(p).name)


if __name__ == "__main__":
    main()
