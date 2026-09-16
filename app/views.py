from django.http import JsonResponse
from django.shortcuts import render

from . import state


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
