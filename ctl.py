#!/usr/bin/env python3
"""命令行遥控器 —— 改播放状态，所有网页一起跟着走。

  ./ctl.py open <URL> [时间]    打开远程片源并播放，时间可选（默认从头）
  ./ctl.py seek <时间>          跳到绝对时间：90 / 1:30 / 1:02:03
  ./ctl.py fwd [秒]             快进，默认 30 秒
  ./ctl.py back [秒]            倒退，默认 30 秒
  ./ctl.py play|pause|toggle    播放 / 暂停 / 切换
  ./ctl.py status               查看当前状态

片源只收 http(s) 地址（比如 OSS 上那个）：浏览器直接去那边拉，不占
服务器带宽。时间线在服务端走，谁什么时候进来都从当前进度接上。
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import state


def parse_time(text):
    """90 / 1:30 / 1:02:03 → 秒。"""
    parts = text.split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(text)
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return total


def fmt(secs):
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def commit(st):
    """记下这一刻。at 是时间线的锚点，网页据此推算现在该播到哪。"""
    st["at"] = time.time()
    state.write(st)


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0 if argv else 1

    cmd, rest = argv[0], argv[1:]
    st = state.read()

    if cmd == "open":
        if not rest:
            print("用法: ctl.py open <URL> [时间]")
            return 1
        src = rest[0]
        if src.startswith("http://"):
            # 页面是 https，加载 http 资源会被浏览器当混合内容拦掉，
            # 而且失败得很安静（就是黑屏）。索性在这里换掉，并说一声。
            src = "https://" + src[len("http://"):]
            print("（地址已由 http:// 换成 https:// —— 否则页面是 https 时会被浏览器拦掉）")
        if not src.startswith("https://"):
            print(f"片源得是 http(s) 地址，浏览器直接去那边拉：{src}")
            return 1
        st["file"] = src
        st["pos"] = parse_time(rest[1]) if len(rest) > 1 else 0.0
        st["playing"] = True
        st["epoch"] += 1
        commit(st)
        print(f"▶ {src}  @ {fmt(st['pos'])}")

    elif cmd == "seek":
        if not rest:
            print("用法: ctl.py seek <时间>")
            return 1
        st["pos"] = parse_time(rest[0])
        st["playing"] = True
        commit(st)
        print(f"→ {fmt(st['pos'])}")

    elif cmd in ("fwd", "back"):
        delta = parse_time(rest[0]) if rest else 30.0
        if cmd == "back":
            delta = -delta
        st["pos"] = max(0.0, state.now_pos(st) + delta)
        st["playing"] = True
        commit(st)
        print(f"→ {fmt(st['pos'])}")

    elif cmd in ("play", "pause", "toggle"):
        # 先把时间线收拢到此刻。播放中 st["pos"] 是过期的（真正的位置得靠
        # now_pos 现算），不收拢就改 playing，暂停会把进度丢回上次下命令的地方。
        st["pos"] = state.now_pos(st)
        st["playing"] = (not st["playing"]) if cmd == "toggle" else (cmd == "play")
        commit(st)
        print("▶ 播放" if st["playing"] else "⏸ 暂停")

    elif cmd == "status":
        print(f"片源  {st['file'] or '(未打开)'}")
        print(f"进度  {fmt(state.now_pos(st))}  {'播放中' if st['playing'] else '暂停'}")

    else:
        print(f"未知命令: {cmd}\n")
        print(__doc__)
        return 1

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ValueError as e:
        print(f"时间格式不对: {e}")
        sys.exit(1)
