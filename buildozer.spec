[app]
title = 妖股竞价选股器
package.name = yaostock
package.domain = com.demo
source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = bin, .buildozer, __pycache__, .venv, bt_cache
version = 1.0.0

# 关键：不含 akshare，数据层已改为纯 Python（list[dict]），无 pandas/numpy 重型 C 库
requirements = python3,kivy,pillow,openssl,sqlite3,
    requests,urllib3,certifi,charset_normalizer,idna,
    setuptools,et_xmlfile,
    android,pyjnius

orientation = portrait
fullscreen = 0

# 图标与启动图（放到项目根目录即可，可先用默认）
# icon.filename = %(source.dir)s/data/icon.png
# presplash.filename = %(source.dir)s/data/presplash.png

# 权限：仅需联网
android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 24
android.ndk = 26b
android.accept_sdk_license = True

# 只打 arm64（现代手机全是），体积减半、编译更快
android.archs = arm64-v8a

# 关闭不必要的东西
android.debug = False
p4a.branch = v2026.05.09
release.artifact_formats = apk

[buildozer]
log_level = 2
warn_on_root = 1
