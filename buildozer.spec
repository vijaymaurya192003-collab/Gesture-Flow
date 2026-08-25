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
source.include_exts = py,png,jpg,kv,atlas,json,db,txt,md,xml,java

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# Note: On Android, python3, kivy, pyjnius, requests, urllib3, certifi, pydantic are supported recipes
requirements = python3,kivy,pyjnius,requests,urllib3,certifi,pydantic

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# -----------------------------------------------------------------------------
# Android specific

# (list) Permissions
android.permissions = CAMERA, INTERNET, ACCESS_NETWORK_STATE, VIBRATE, SYSTEM_ALERT_WINDOW, BIND_ACCESSIBILITY_SERVICE

# (int) Target Android API
android.api = 33

# (int) Minimum API supported (API 24 required for AccessibilityService dispatchGesture)
android.minapi = 24

# (list) The Android architectures to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) Accept SDK licenses automatically
android.accept_sdk_license = True

# (str) The entrypoint for your application
android.entrypoint = org.kivy.android.PythonActivity

# (list) Add java files to compile
android.add_src = android/src

# (list) Add android resources (XML configs, strings)
android.add_resources = android/res

# (str) Extra manifest xml to register the AccessibilityService
android.extra_manifest_xml = <service android:name="org.gestureflow.GestureAccessibilityService" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE" android:exported="true"><intent-filter><action android:name="android.accessibilityservice.AccessibilityService" /></intent-filter><meta-data android:name="android.accessibilityservice" android:resource="@xml/accessibility_service_config" /></service>

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug with command output)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
