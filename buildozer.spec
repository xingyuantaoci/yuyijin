[app]
title = 妖股竞价选股器
package.name = yaostock
package.domain = com.demo
source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = bin, .buildozer, __pycache__, .venv, bt_cache
version = 1.0.0

# 关键：不含 akshare，仅保留安卓可编译依赖（pandas/numpy 版本与 NDK25 匹配）
requirements = python3,kivy==2.3.0,pillow,openssl,sqlite3,
    requests,urllib3,certifi,charset_normalizer,idna,
    pandas==2.0.3,numpy==1.24.3,setuptools,
    android,pyjnius,et_xmlfile

orientation = portrait
fullscreen = 0

# 图标与启动图（放到项目根目录即可，可先用默认）
# icon.filename = %(source.dir)s/data/icon.png
# presplash.filename = %(source.dir)s/data/presplash.png

# 权限：仅需联网
android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

# 只打 arm64（现代手机全是），体积减半、编译更快
android.archs = arm64-v8a

# 关闭不必要的东西
android.debug = False
p4a.branch = v2024.01.21
release.artifact_formats = apk

[buildozer]
log_level = 2
warn_on_root = 1
