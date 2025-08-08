[app]
title = BitChatLite
package.name = bitchat_lite
package.domain = org.example
source.dir = .
source.include_exts = py,kv
requirements = python3,kivy,pyjnius,cryptography,openssl,libffi,android
orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 24
android.enable_androidx = True
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, BLUETOOTH_ADVERTISE, ACCESS_FINE_LOCATION

# Speed up first build
p4a.local_recipes = 

[buildozer]
log_level = 2
warn_on_root = 1
