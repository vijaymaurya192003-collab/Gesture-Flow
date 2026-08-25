[app]

# (str) Title of your application
title = Gesture Flow

# (str) Package name
package.name = gestureflow

# (str) Package domain (needed for android/ios packaging)
package.domain = org.gestureflow

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,db,txt,md

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,kivymd,opencv,numpy,requests,urllib3,certifi,pydantic

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# -----------------------------------------------------------------------------
# Android specific

# (list) Permissions
android.permissions = CAMERA, INTERNET, ACCESS_NETWORK_STATE, VIBRATE, SYSTEM_ALERT_WINDOW

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support (API 24 required for AccessibilityService dispatchGesture).
android.minapi = 24

# (list) The Android architectures to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess downloads or save time
android.skip_update = False

# (bool) If True, then accept all SDK licenses
android.accept_sdk_license = True

# (str) The entrypoint for your application
android.entrypoint = org.kivy.android.PythonActivity

# (list) Pattern to whitelist for the whole project
android.whitelist = []

# (list) Add java files to compile
# android.add_src = java_src

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug with command output)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

