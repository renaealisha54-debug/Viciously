[app]
title = Viciously Mediator
package.name = viciously
package.domain = com.viciously.mediator
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,bin
version = 1.0.0

# Mandatory Android Permissions
android.permissions = RECORD_AUDIO, MODIFY_AUDIO_SETTINGS, INTERNET, WAKE_LOCK, FOREGROUND_SERVICE, POST_NOTIFICATIONS

# Python dependencies to bundle in the APK
requirements = python3, kivy, requests, pycryptodome

# Orientation and Display settings
orientation = portrait
fullscreen = 0

# Android Target Specifications
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

# Enable foreground service execution
android.service = mediator_service:service.py

[buildozer]
log_level = 2
warn_on_root = 1
