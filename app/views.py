from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render

from . import state

FETCH_TIMEOUT = 5
MAX_SUBS_BYTES = 4 << 20   # 字幕撑死几百 KB，超过这个数就当成不对


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = build_opener(_NoRedirect)


def index(request):
    return render(request, "app/index.html")


def status(request):
    """网页每秒轮询这里：该放哪一段、放还是停。片源地址原样给出去。"""
    s = state.read()
    return JsonResponse({
        "epoch": s["epoch"],          # 换片了没有
        "pos": state.now_pos(s),      # 此刻应该播到哪（不是上次命令的位置）
        "playing": bool(s["playing"]),
        "url": s["file"],             # 空串 = 还没 open 过
    })


def _vtt_url(video):
    p = urlparse(video)
    if p.scheme not in ("http", "https"):
        return ""
    path = p.path
    dot = path.rfind(".")
    if dot > path.rfind("/"):        # 别把目录名里的点当成后缀
        path = path[:dot]
    return p._replace(path=path + ".vtt", query="", fragment="").geturl()


def _allowed(url):
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and any(host.endswith(sfx) for sfx in settings.SUBS_ALLOWED_HOSTS)


def subs(request):
    url = _vtt_url(request.GET.get("u", ""))
    if not _allowed(url):
        return HttpResponseNotFound("")
    try:
        req = Request(url, headers={"User-Agent": "cinema-subs"})
        with _opener.open(req, timeout=FETCH_TIMEOUT) as r:
            body = r.read(MAX_SUBS_BYTES + 1)
    except (HTTPError, URLError, OSError, ValueError):
        return HttpResponseNotFound("")
    if len(body) > MAX_SUBS_BYTES:
        return HttpResponseNotFound("")
    resp = HttpResponse(body, content_type="text/vtt; charset=utf-8")
    resp["Cache-Control"] = "private, max-age=300"
    return resp
