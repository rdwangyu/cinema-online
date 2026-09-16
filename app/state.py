"""播放状态：命令行写，Django 读。

state.json 放在项目根目录，记着遥控器想让网页做什么。

时间线在服务端走，这是"电影院"的关键：pos 是上次下命令时的位置，
at 是那一刻的时间戳，两者都不动；真正播到哪了要用 now_pos() 现算。
这样不管谁什么时候打开网页，拿到的都是"此刻应该在哪儿"，而不是
"上次按遥控器时在哪儿"。
"""

import json
import os
import tempfile
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE, "state.json")

EMPTY = {"file": "", "pos": 0.0, "playing": False, "epoch": 0, "at": 0.0}


def read():
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return dict(EMPTY)
    if not isinstance(data, dict):
        return dict(EMPTY)
    return {**EMPTY, **data}


def write(data):
    """先写临时文件再 rename，避免网页读到写了一半的 JSON。"""
    fd, tmp = tempfile.mkstemp(dir=BASE)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, STATE_FILE)
    except BaseException:
        os.unlink(tmp)
        raise


def now_pos(s):
    """这一刻实际播到哪了：播放中就把流逝的时间算上，暂停就停在 pos。"""
    if s["playing"] and s["at"]:
        return s["pos"] + time.time() - s["at"]
    return s["pos"]
