"""把一张「实物照片」处理成应用里能直接用的机型图。

用途：仪表盘上每台打印机显示一张真机照片（`app/static/printer/<model>.jpg`）。
手上拿到的素材一般都不是规规矩矩的产品图：官方商店图角上有水印/型号字，
官方 App 截图里已经压了温度胶囊，wiki 图带引线标注。这个脚本负责把它们
裁成「一块干净的画布 + 居中一台机器」，尺寸和界面上的展示框对齐，
于是数据库里的温度浮标就能像官方 App 那样浮在机器两侧。

两件事：
1. **修掉压上去的东西**（`--heal x0,y0,x1,y1`，可重复）：
   按矩形上下边界做竖向线性插值。影棚底的亮度基本只跟 y 有关（横向均匀），
   上下边界之间本来就接近线性，插值出来的背景和周围完全一致，不会像填纯色
   那样留下硬边；浮标压住机身侧边时那一段轮廓是竖直的，插值也自然把边接直。
2. **裁到指定画布**：`--crop x0,y0,x1,y1` 给出机身的紧外接框（自己量一次，
   比自动找更稳，因为自动找容易被画面里的文字带偏），然后按 `--fit-width`
   缩放并居中贴到 `--canvas` 上，四周用取样出来的背景色补满。

量外接框的偷懒办法：脚本带 `--probe`，先让它把非背景外接框打出来。
背景取「画布四边一圈像素的高分位亮度」——用高分位是为了躲开机器自己的投影，
投影会把中位数压低，而机器边缘之外的背景才是我们要的。

用法：
    # 1) 先量机身范围（会打印整幅 / 上下半幅三个外接框）
    python scripts/build_printer_photo.py store.jpg x.jpg --probe
    # 2) 按量出来的框裁剪成 720x876 的画布（= 界面 240x292 展示框的 3 倍）
    python scripts/build_printer_photo.py store.jpg app/static/printer/p2s.jpg \
        --crop 498,650,1857,2018 --canvas 720x876 --fit-width 0.86
    # 带温度胶囊的截图：先 --heal 掉胶囊再裁
    python scripts/build_printer_photo.py shot.jpg app/static/printer/p2s.jpg \
        --heal 96,74,317,172 --heal 96,378,317,472 --crop 0,0,1080,578

注意：只在「纯色影棚底 + 单台机器」的图上工作。杂背景照片请先自己抠图。
"""
from __future__ import annotations

import argparse
import sys

from PIL import Image

Rect = tuple[int, int, int, int]


def background_tone(img: Image.Image) -> int:
    """背景亮度：画布四边一圈像素的 90 分位灰度。

    用高分位而不是中位数：机器底部往往有一圈投影贴着下边缘，
    投影会把中位数往下拉，补出来的背景就会比真实背景暗一条。
    """
    px = img.load()
    width, height = img.size
    samples: list[float] = []
    for x in range(width):
        for y in (0, 1, height - 2, height - 1):
            r, g, b = px[x, y][:3]
            samples.append((r + g + b) / 3)
    for y in range(height):
        for x in (0, 1, width - 2, width - 1):
            r, g, b = px[x, y][:3]
            samples.append((r + g + b) / 3)
    samples.sort()
    return int(round(samples[int(len(samples) * 0.9)]))


def heal_region(img: Image.Image, rect: Rect) -> int:
    """把矩形里的内容按「上下边界之间做竖向线性插值」补上。

    比最近邻修补干净：最近邻会按「离哪条边最近」把补丁切成几块，
    块与块之间只要有一点亮度差就能看出边界。

    前提是矩形上下两条边所在的行是干净的（没被同一件东西压住）。
    """
    width, height = img.size
    x0 = max(0, rect[0])
    y0 = max(1, rect[1])
    x1 = min(width, rect[2])
    y1 = min(height - 1, rect[3])
    if x1 <= x0 or y1 <= y0:
        return 0

    px = img.load()
    span = y1 - y0 + 1
    for x in range(x0, x1):
        top = px[x, y0 - 1][:3]
        bottom = px[x, y1][:3]
        for y in range(y0, y1):
            t = (y - (y0 - 1)) / span
            px[x, y] = (
                round(top[0] + (bottom[0] - top[0]) * t),
                round(top[1] + (bottom[1] - top[1]) * t),
                round(top[2] + (bottom[2] - top[2]) * t),
            )
    return (x1 - x0) * (y1 - y0)


def find_machine_bbox(img: Image.Image, threshold: float) -> Rect:
    """整幅里「和背景差得够远」的像素的外接框（用来找机身，也会被文字带偏）。"""
    tone = background_tone(img)
    px = img.load()
    width, height = img.size
    xs: list[int] = []
    ys: list[int] = []
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            r, g, b = px[x, y][:3]
            if abs((r + g + b) / 3 - tone) > threshold:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise SystemExit("没找到机身：阈值太低，或背景不是纯色（先抠图再跑）。")
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def bbox_in(img: Image.Image, rect: Rect, threshold: float) -> Rect | None:
    """指定区域里非背景像素的外接框，用来分别量「上半幅（文字）/ 下半幅（机器）」。"""
    tone = background_tone(img)
    px = img.load()
    x0, y0, x1, y1 = rect
    xs: list[int] = []
    ys: list[int] = []
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            r, g, b = px[x, y][:3]
            if abs((r + g + b) / 3 - tone) > threshold:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def parse_rect(value: str) -> Rect:
    parts = [int(p) for p in value.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("矩形要写成 x0,y0,x1,y1")
    return parts[0], parts[1], parts[2], parts[3]


def parse_size(value: str) -> tuple[int, int]:
    parts = value.lower().replace(" ", "").split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("画布要写成 宽x高，例如 720x876")
    return int(parts[0]), int(parts[1])


def build(
    src: str,
    dst: str,
    heals: list[Rect],
    crop: Rect | None,
    canvas_size: tuple[int, int] | None,
    fit_width: float,
    pad: int,
    out_width: int,
    out_max_height: int,
    threshold: float,
    quality: int,
) -> dict:
    img = Image.open(src).convert("RGB")
    for rect in heals:
        heal_region(img, rect)

    if crop:
        # 裁掉画布外的内容后重新取样背景：裁进来的那圈才是要补的背景
        img = img.crop(crop)
    left, top, right, bottom = find_machine_bbox(img, threshold)
    box = (left, top, right, bottom)
    machine = img.crop(box)
    tone = background_tone(img)
    bg = (tone, tone, tone)

    if canvas_size:
        cw, ch = canvas_size
        target_w = max(1, int(round(cw * fit_width)))
        ratio = target_w / machine.width
        scaled = machine.resize(
            (target_w, max(1, round(machine.height * ratio))), Image.LANCZOS
        )
        # 高的一边也要放得下：放不下就反过来按高缩，宁可机器小一点
        limit_h = ch - 2 * pad
        if scaled.height > limit_h:
            ratio = limit_h / scaled.height
            scaled = machine.resize(
                (max(1, round(machine.width * ratio)), limit_h), Image.LANCZOS
            )
        out = Image.new("RGB", (cw, ch), bg)
        out.paste(scaled, ((cw - scaled.width) // 2, (ch - scaled.height) // 2))
    else:
        out = Image.new("RGB", (machine.width + 2 * pad, machine.height), bg)
        out.paste(machine, (pad, 0))
        if out_width and out.width != out_width:
            r = out_width / out.width
            out = out.resize((out_width, max(1, round(out.height * r))), Image.LANCZOS)
        if out_max_height and out.height > out_max_height:
            r = out_max_height / out.height
            out = out.resize((max(1, round(out.width * r)), out_max_height), Image.LANCZOS)

    out.save(dst, quality=quality, optimize=True)
    return {
        "机器外接框": box,
        "背景亮度": tone,
        "输出": f"{dst} {out.width}x{out.height}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="生成仪表盘用的真机照片")
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?", default="")
    ap.add_argument("--probe", action="store_true", help="只打印几个外接框，不输出文件")
    ap.add_argument("--heal", action="append", type=parse_rect, default=[],
                    help="要修掉的矩形 x0,y0,x1,y1（例如压上去的温度胶囊），可重复")
    ap.add_argument("--crop", type=parse_rect, default=None, help="只保留这一块再处理")
    ap.add_argument("--canvas", type=parse_size, default=None, help="输出画布尺寸 宽x高")
    ap.add_argument("--fit-width", type=float, default=0.86,
                    help="机器宽度占画布宽度的比例（默认 0.86，和界面上的间距对齐）")
    ap.add_argument("--pad", type=int, default=10, help="画布里机器四周至少留的边距")
    ap.add_argument("--width", type=int, default=900, help="不指定 --canvas 时的输出宽度")
    ap.add_argument("--max-height", type=int, default=1100)
    ap.add_argument("--threshold", type=float, default=20.0, help="判定「非背景」的亮度差")
    ap.add_argument("--quality", type=int, default=92)
    args = ap.parse_args()

    if args.probe:
        img = Image.open(args.src).convert("RGB")
        for rect in args.heal:
            heal_region(img, rect)
        w, h = img.size
        print(f"图像 {w}x{h}  背景亮度 {background_tone(img)}")
        print("  整幅        ", find_machine_bbox(img, args.threshold))
        print("  上半幅      ", bbox_in(img, (0, 0, w, h // 2), args.threshold))
        print("  下半幅      ", bbox_in(img, (0, h // 2, w, h), args.threshold))
        return 0

    if not args.dst:
        print("要给出输出路径，或者用 --probe。", file=sys.stderr)
        return 2

    info = build(
        args.src, args.dst, args.heal, args.crop, args.canvas,
        args.fit_width, args.pad, args.width, args.max_height,
        args.threshold, args.quality,
    )
    for key, value in info.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
