#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

TEXT_SUBS = {"subrip", "srt", "ass", "ssa", "mov_text", "webvtt"}
IMAGE_SUBS = {"hdmv_pgs_subtitle", "dvd_subtitle", "dvb_subtitle", "xsub"}

# 浏览器只认 8bit 的 H.264。10bit 的（yuv420p10le / p010）拿 -c:v copy 搬过去
# 就是 High 10，Chrome 和 Safari 直接黑屏，还一声不吭 —— 必须重编。
PLAYABLE_PIX_FMTS = {"yuv420p", "yuvj420p"}

LANG_PREF = ("chi", "zho", "zh", "chs", "cht", "zh-cn", "zh-hans", "zh-hant")


def run(cmd):
    try:
        return subprocess.run(cmd, check=True)
    except FileNotFoundError:
        sys.exit(f"找不到命令 {cmd[0]}，先装上它")
    except subprocess.CalledProcessError as e:
        sys.exit(f"命令失败（退出码 {e.returncode}）：\n  {' '.join(cmd)}")


def probe(path):
    """问 ffprobe 片子里有哪些流。"""
    cmd = ["ffprobe", "-v", "error", "-show_entries",
           "stream=index,codec_type,codec_name,pix_fmt"
           ":stream_tags=language,title,DURATION"
           ":stream_disposition=attached_pic",
           "-of", "json", path]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    except FileNotFoundError:
        sys.exit("找不到 ffprobe，先装上 ffmpeg")
    except subprocess.CalledProcessError as e:
        sys.exit(f"ffprobe 读不了这个文件：{e.stderr.strip() or path}")
    return json.loads(out)["streams"]


def is_cover(s):
    """MP4/MOV 会用这个标记标出封面图。MKV 不认，所以光靠它不够。"""
    return str(s.get("disposition", {}).get("attached_pic", 0)) == "1"


def duration_of(s):
    """流的时长（秒）。

    MKV 里 duration 字段是空的，得从 DURATION 标签里抠（形如 00:00:03.000000000）。
    """
    raw = (s.get("tags") or {}).get("DURATION") or s.get("duration")
    if not raw:
        return 0.0
    try:
        total = 0.0
        for part in str(raw).split(":"):
            total = total * 60 + float(part)
        return total
    except ValueError:
        return 0.0


def pick_video(streams):
    """挑正片。

    封面图在容器里也是一条视频流，挑错了就会转出一个只有一帧的 mp4。MKV 不认
    attached_pic 标记，所以两条都上：先排掉被标记的，再按时长取最长的 ——
    封面图撑死几十毫秒，正片一定比它长得多。
    """
    cands = [s for s in streams
             if s.get("codec_type") == "video" and not is_cover(s)]
    return max(cands, key=duration_of) if cands else None


def describe(s):
    """一行流简介。带上时长，一眼就能看出哪条是封面图。"""
    tags = s.get("tags") or {}
    bits = [f"#{s['index']}", str(s.get("codec_type")), str(s.get("codec_name"))]
    bits += [t for t in (s.get("pix_fmt"), tags.get("language"), tags.get("title")) if t]
    bits.append(f"{duration_of(s):.2f}s")
    if is_cover(s):
        bits.append("（封面图）")
    return " ".join(bits)


def pick_sub(streams, want):
    """挑一条能转成文字的轨。返回 (流, 跳过的原因)。"""
    subs = [s for s in streams if s.get("codec_type") == "subtitle"]
    if not subs:
        return None, "片源里没有字幕轨"
    if want is not None:
        if not 0 <= want < len(subs):
            sys.exit(f"--sub {want} 越界：这片子只有 {len(subs)} 条字幕轨")
        chosen = subs[want]
        if chosen.get("codec_name") in IMAGE_SUBS:
            return None, f"第 {want} 条是图形字幕（{chosen['codec_name']}），抽不出文字，得先用 OCR"
        return chosen, None

    text = [s for s in subs if s.get("codec_name") in TEXT_SUBS]
    if not text:
        kinds = "、".join(s.get("codec_name", "?") for s in subs)
        return None, f"字幕全是图形格式（{kinds}），抽不出文字，得先用 OCR"
    for s in text:
        if ((s.get("tags") or {}).get("language") or "").lower() in LANG_PREF:
            return s, None
    return text[0], None


def main(argv):
    ap = argparse.ArgumentParser(
        description="MKV 转 MP4 + VTT（走显卡）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="MKV 文件")
    ap.add_argument("--outdir", help="输出目录，默认跟片源同目录")
    ap.add_argument("--sub", type=int, help="用第几条字幕轨（从 0 数）")
    ap.add_argument("--reencode", action="store_true",
                    help="片源本来能播也强制重编一遍")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.source):
        sys.exit(f"找不到文件：{args.source}")

    streams = probe(args.source)
    print("片源里有：")
    for s in streams:
        print(f"  {describe(s)}")

    video = pick_video(streams)
    if not video:
        sys.exit("这文件里没有视频流")
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    vcodec = video.get("codec_name")
    pix = video.get("pix_fmt")
    # 只有「本来就是 8bit H.264」才敢原样搬，其余一律重编
    copy = vcodec == "h264" and pix in PLAYABLE_PIX_FMTS and not args.reencode
    if not copy and not args.reencode:
        why = f"是 {vcodec}" if vcodec != "h264" else f"是 10bit 的（{pix}）"
        sys.exit(f"\n视频{why}，浏览器放不了，得重编。\n"
                 f"确认要转就加 --reencode（编解码都走显卡，不慢）。")

    base = os.path.splitext(os.path.basename(args.source))[0]
    outdir = args.outdir or os.path.dirname(os.path.abspath(args.source))
    os.makedirs(outdir, exist_ok=True)
    mp4 = os.path.join(outdir, base + ".mp4")
    vtt = os.path.join(outdir, base + ".vtt")

    # ── 正片 ──────────────────────────────────────────────────────────
    cmd = ["ffmpeg", "-hide_banner", "-stats", "-y"]
    if not copy:
        cmd += ["-hwaccel", "cuda"]        # NVDEC 解码。这是输入选项，必须排在 -i 前面
    cmd += ["-i", args.source, "-map", f"0:{video['index']}"]
    if audio:
        cmd += ["-map", f"0:{audio['index']}"]

    if copy:
        cmd += ["-c:v", "copy"]
    else:
        # 编码全丢给 NVENC。cq 是画质档，数字越小越好。实测 cq21 出的文件比
        # libx264 crf21 大四成，想跟以前一样大就用 cq24（画质也基本一样）。
        # preset 用 p5：实测比 p7 快一倍，SSIM/XPSNR 测不出差别。
        # 别加 -multipass fullres：时间翻倍，文件没变小，白烧。
        cmd += ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
                "-rc", "vbr", "-cq", "21",
                "-pix_fmt", "yuv420p"]     # 少了这句，10bit 片源会出 High 10

    if audio:
        if audio.get("codec_name") == "aac":
            cmd += ["-c:a", "copy"]
        else:
            cmd += ["-c:a", "aac", "-b:a", "192k", "-ac", "2"]

    cmd += ["-movflags", "+faststart", mp4]
    print(f"\n▶ {'原样搬' if copy else 'NVENC 重编'}正片 → {mp4}")
    run(cmd)

    # ── 字幕 ──────────────────────────────────────────────────────────
    sub, why = pick_sub(streams, args.sub)
    if sub is None:
        print(f"\n⏭ 跳过字幕：{why}")
    else:
        print(f"\n▶ 抽字幕 → {vtt}")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", args.source,
             "-map", f"0:{sub['index']}", "-c:s", "webvtt", vtt])

    print("\n转好了，自己传：")
    for f in [mp4] + ([vtt] if sub else []):
        print(f"  ossutil cp -f {f} oss://你的桶/目录/")
    if sub:
        print("\n（字幕按同名的 .vtt 在服务端自动找，不用另外配）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
