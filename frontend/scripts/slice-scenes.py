"""产出两个页面要用的配图（都从项目已有素材派生，不引入外部图片）。

1. `media/scenes-strip.png`
   源：`design-assets/2/smoke_control_ai_campaign_hero_background_ai_original.png`
   内容：持烟识别 / 吸烟亭 / 烟头落地 / 摄像头识别 / 环卫协同处置 五段实景通栏。
   用途：入口页 §03 机制屏底部——五段现场对应五个阶段，一眼看全流程。
   处理：去掉最左侧的标题文字块（深蓝底）只留实景。

2. `media/city-skyline.png`
   源：`design-assets/1/blue_city_skyline_login_background_local_composite.png`
   内容：浅蓝水彩城市天际线（上半留白、下半剪影）。
   用途：市民端首屏 banner——市民端需要的是「城市公共空间」的明亮感，
   与入口页那张黄昏写实街景刻意区分开。
   处理：取中部偏下一块，保留大片浅色留白给文字。

关于「切段」的教训：通栏图里 5 段实景**并非等分**，接缝在 573/780/972/1172 附近，
靠肉眼估坐标切出来会混进邻段内容。所以这里只切「文字块 / 实景」这一个有明显色差的边界，
不再拆单段。
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public/media"

STRIP_SRC = ROOT / "public/design-assets/2/smoke_control_ai_campaign_hero_background_ai_original.png"
SKY_SRC = ROOT / "public/design-assets/1/blue_city_skyline_login_background_local_composite.png"

# 实测：文字块右边界 x=402（逐列深蓝占比 0.50 → 0.41）
STRIP_CUT = 402
# 天际线取景：避开右侧面板、保留天空留白与底部剪影
SKY_BOX = (400, 380, 1520, 941)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    strip_src = Image.open(STRIP_SRC).convert("RGB")
    w, h = strip_src.size
    strip = strip_src.crop((STRIP_CUT, 0, w, h))
    strip.save(OUT / "scenes-strip.png")
    print(f"scenes-strip.png {strip.size}  (源 {w}x{h}，去掉 0-{STRIP_CUT} 的文字块)")

    sky_src = Image.open(SKY_SRC).convert("RGB")
    sky = sky_src.crop(SKY_BOX)
    sky.save(OUT / "city-skyline.png")
    print(f"city-skyline.png {sky.size}  (源 {sky_src.size}，取 {SKY_BOX})")

    # 上一轮逐段拆的产物已无用途，清掉避免混淆
    for i in range(1, 6):
        p = OUT / f"scene-{i}.png"
        if p.exists():
            p.unlink()
            print("removed stale:", p.name)
    p = OUT / "scene-pavilion.png"
    if p.exists():
        p.unlink()
        print("removed stale:", p.name)


if __name__ == "__main__":
    main()
