"""Django 配置。

就一个页面加一个只读状态接口，没有数据库、没有登录、没有静态文件，
用不上的东西一律不装。
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-r2l00mr(sw2obp$@&awdm%6pe+k18*)8d9tn#k_(7wf2hu9j=+"

DEBUG = True

ALLOWED_HOSTS = ["*"]

# /subs 代理只许去这些域名取字幕（后缀匹配）。不设限它就是个 SSRF 跳板，
# 别人能拿它去打 ECS 的元数据接口 100.100.100.200 偷 AK。
SUBS_ALLOWED_HOSTS = [".aliyuncs.com"]

INSTALLED_APPS = ["app"]

MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]

ROOT_URLCONF = "cinema_online.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "cinema_online.wsgi.application"
