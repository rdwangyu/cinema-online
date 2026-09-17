"""Django 配置。

就一个页面加一个只读状态接口，没有数据库、没有登录、没有静态文件，
用不上的东西一律不装。
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-r2l00mr(sw2obp$@&awdm%6pe+k18*)8d9tn#k_(7wf2hu9j=+"

DEBUG = True

ALLOWED_HOSTS = ["*"]

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
