"""播放状态：命令行写，Django 读。

两个 JSON 文件放在项目根目录：
  state.json    遥控器想让网页做什么（文件、位置、播放/暂停）
  progress.json 网页回报自己实际播到哪了，供相对快进/倒退用
"""

import json
import os
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE, "state.json")
PROGRESS_FILE = os.path.join(BASE, "progress.json")

EMPTY = {"file": "", "pos": 0.0, "playing": False, "epoch": 0, "version": 0}


def _load(path, fallback):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return dict(fallback)
    if not isinstance(data, dict):
        return dict(fallback)
    return {**fallback, **data}


def _save(path, data):
    """先写临时文件再 rename，避免网页读到写了一半的 JSON。"""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def read():
    return _load(STATE_FILE, EMPTY)


def write(data):
    _save(STATE_FILE, data)


def read_progress():
    try:
        return float(_load(PROGRESS_FILE, {"t": 0.0})["t"])
    except (TypeError, ValueError):
        return 0.0


def write_progress(t):
    _save(PROGRESS_FILE, {"t": float(t)})
