[app]
title = Viciously Mediator
package.name = viciously
package.domain = com.viciously.mediator
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,bin
version = 1.0.0

# Android Permissions
android.permissions = RECORD_AUDIO, MODIFY_AUDIO_SETTINGS, INTERNET, WAKE_LOCK, FOREGROUND_SERVICE, POST_NOTIFICATIONS, REQUEST_IGNORE_BATTERY_OPTIMIZATIONS

# Python dependencies
requirements = python3, kivy==2.2.1, requests, pycryptodome

# Display Settings
orientation = portrait
fullscreen = 0

# SDK/NDK Pins
android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 33.0.2
android.archs = arm64-v8a
android.accept_sdk_license = True

# Foreground Service
services = viciously_service:service.py:foreground

[buildozer]
log_level = 2
warn_on_root = 1
