import mimetypes
import os

from django.http import HttpResponse, HttpResponseNotFound, JsonResponse, StreamingHttpResponse
from django.shortcuts import render

from . import state

CHUNK = 1 << 16


def index(request):
    return render(request, "app/index.html")


def status(request):
    """网页每秒轮询这里，判断该不该跳转、换片。不返回真实路径。"""
    s = state.read()
    return JsonResponse({
        "version": s["version"],
        "epoch": s["epoch"],
        "pos": s["pos"],
        "playing": bool(s["playing"]),
        "ready": bool(s["file"]) and os.path.isfile(s["file"]),
    })


def progress(request):
    """网页回报自己播到哪了，供命令行做相对快进/倒退。"""
    try:
        state.write_progress(float(request.GET["t"]))
    except (KeyError, ValueError):
        pass
    return HttpResponse(status=204)


def _range(header, size):
    """解析单段 Range，返回 (start, end)；不支持或越界返回 None。"""
    unit, _, spec = header.partition("=")
    if unit.strip() != "bytes" or "," in spec:
        return None
    first, _, last = spec.strip().partition("-")
    try:
        if first == "":
            start, end = max(0, size - int(last)), size - 1
        else:
            start = int(first)
            end = int(last) if last else size - 1
    except ValueError:
        return None
    if start >= size or start > end:
        return None
    return start, min(end, size - 1)


def _body(path, start, length):
    """从 start 起吐 length 字节；生成器被关闭时文件随之关闭。"""

    def chunks():
        with open(path, "rb") as f:
            f.seek(start)
            left = length
            while left > 0:
                block = f.read(min(CHUNK, left))
                if not block:
                    break
                left -= len(block)
                yield block

    return chunks()


def video(request):
    """把当前片源原样吐给浏览器。手写 Range，Django 自身不支持。"""
    path = state.read()["file"]
    if not path or not os.path.isfile(path):
        return HttpResponseNotFound("no video")

    size = os.path.getsize(path)
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"

    header = request.headers.get("Range")
    if header is None:
        start, end, code = 0, size - 1, 200
    else:
        parsed = _range(header, size)
        if parsed is None:
            resp = HttpResponse(status=416)
            resp["Content-Range"] = f"bytes */{size}"
            return resp
        # 凡是合法 Range 一律回 206，哪怕覆盖整个文件。浏览器靠这个判断
        # 服务器支不支持 Range，回 200 会导致进度条被禁用。
        start, end = parsed
        code = 206

    length = end - start + 1
    body = () if request.method == "HEAD" else _body(path, start, length)
    resp = StreamingHttpResponse(body, status=code, content_type=ctype)
    resp["Content-Length"] = str(length)
    resp["Accept-Ranges"] = "bytes"
    if code == 206:
        resp["Content-Range"] = f"bytes {start}-{end}/{size}"
    return resp
