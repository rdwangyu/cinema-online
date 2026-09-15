#!/usr/bin/env python3
"""命令行遥控器 —— 改播放状态，网页跟着走。

  ./ctl.py open <片源> [时间]   打开文件并播放，时间可选（默认从头）
  ./ctl.py seek <时间>          跳到绝对时间：90 / 1:30 / 1:02:03
  ./ctl.py fwd [秒]             快进，默认 30 秒
  ./ctl.py back [秒]            倒退，默认 30 秒
  ./ctl.py play|pause|toggle    播放 / 暂停 / 切换
  ./ctl.py status               查看当前状态
"""

import os
import sys

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
    st["version"] += 1
    state.write(st)


def where(st):
    """相对快进/倒退的基准。

    网页回报有最多 2 秒延迟：刚下过指令就再按一次快进，回报还停在旧位置。
    所以谁的文件更新就信谁——刚下过指令就信指令，网页报过了就信网页。
    """
    try:
        if os.path.getmtime(state.STATE_FILE) > os.path.getmtime(state.PROGRESS_FILE):
            return st["pos"]
    except OSError:
        pass
    return state.read_progress()


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0 if argv else 1

    cmd, rest = argv[0], argv[1:]
    st = state.read()

    if cmd == "open":
        if not rest:
            print("用法: ctl.py open <片源> [时间]")
            return 1
        path = os.path.abspath(os.path.expanduser(rest[0]))
        if not os.path.isfile(path):
            print(f"找不到文件: {path}")
            return 1
        st["file"] = path
        st["pos"] = parse_time(rest[1]) if len(rest) > 1 else 0.0
        st["playing"] = True
        st["epoch"] += 1
        commit(st)
        print(f"▶ {path}  @ {fmt(st['pos'])}")

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
        st["pos"] = max(0.0, where(st) + delta)
        st["playing"] = True
        commit(st)
        print(f"→ {fmt(st['pos'])}")

    elif cmd in ("play", "pause", "toggle"):
        st["playing"] = (not st["playing"]) if cmd == "toggle" else (cmd == "play")
        commit(st)
        print("▶ 播放" if st["playing"] else "⏸ 暂停")

    elif cmd == "status":
        print(f"片源  {st['file'] or '(未打开)'}")
        print(f"指令  {fmt(st['pos'])}  {'播放中' if st['playing'] else '暂停'}")
        print(f"实际  {fmt(state.read_progress())}  ← 网页回报")

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
