# BitChatLite – Offline Bluetooth Chat (Kivy + Python)

BitChatLite is a minimal, peer‑to‑peer Bluetooth chat app with end‑to‑end encryption. It works without Internet or servers and can run on desktop (Windows/Linux) and on Android (built with Buildozer, no Android Studio required).

- Transport: Bluetooth RFCOMM (classic)
- UI: Kivy
- Crypto: AES‑256‑GCM (passphrase‑derived key)
- Android build: Buildozer/python‑for‑android


## Features
- Peer‑to‑peer Bluetooth chat (no server)
- Device discovery (desktop) / bonded devices (Android)
- AES‑GCM encryption using a shared passphrase
- Simple chat UI (input + history)


## Project Structure
```
bitchat-lite/
  main.py               # Kivy app entry
  chat.kv               # Kivy UI
  bluetooth_utils.py    # Bluetooth scan/connect/send/recv (PyBluez + Android via pyjnius)
  encryption.py         # AES-GCM encrypt/decrypt
  requirements.txt      # Desktop/dev dependencies
  buildozer.spec        # Android APK configuration
```


## Prerequisites
- Python 3.10+ (64‑bit recommended)
- Bluetooth hardware enabled

Platform notes:
- Windows: uses PyBluez (classic Bluetooth). Pair devices via Windows Settings if needed.
- Linux: uses PyBluez. May require `bluez`/`bluetooth` packages and user in `bluetooth`/`lp` groups.
- macOS: PyBluez classic RFCOMM is not supported. macOS is not targeted.
- Android: build with Buildozer on Linux/WSL2. Pair devices in system settings first.


## Desktop (Windows/Linux) – Run from source
1) Install dependencies
   - Ensure you are inside the `bitchat-lite` folder.
   - Windows (PowerShell/CMD):
     - `pip install -r requirements.txt`
   - Linux (shell):
     - Install system packages (example on Debian/Ubuntu): `sudo apt update && sudo apt install -y python3-dev libbluetooth-dev bluez` then `pip install -r requirements.txt`

2) Run the app
   - `python main.py`

3) Use the app
   - On both devices, open the app and enter the exact same shared passphrase.
   - On device A: click “Start Server”.
   - On device B: click “Scan”, select device A, then “Connect”.
   - Type messages and press “Send”. Messages are encrypted with your passphrase.

Troubleshooting (desktop)
- “Bluetooth backend not available”: install PyBluez and ensure the Bluetooth service is running.
- No devices found: make device discoverable, or pair in OS settings, then retry Scan.
- Connect fails: try pairing in OS first, then connect from the app; ensure only one client connects to the server.


## Android – Build APK with Buildozer (no Android Studio)
You need Linux (native) or Windows with WSL2 Ubuntu. Examples below use Ubuntu.

1) Install prerequisites (Ubuntu)
- `sudo apt update && sudo apt install -y build-essential git zip unzip openjdk-17-jdk python3 python3-pip python3-venv libffi-dev libssl-dev` 
- `pip install --upgrade pip cython buildozer`

2) Prepare the project
- Place this folder `bitchat-lite/` inside your Linux home (or open it from WSL2).
- Verify `buildozer.spec` exists (already provided).

3) Build the APK
- From inside `bitchat-lite`: `buildozer android debug`
- First build downloads SDK/NDK and can take a while.
- On success, APK is at `bin/BitChatLite-*-armeabi-v7a-debug.apk` (and/or arm64).

4) Install on device
- Copy the APK to your phone and install (enable “Install unknown apps”), or use `adb install` from a PC.

5) Use the app
- Grant Bluetooth and Location permissions when prompted (Android 6+ requires Location for Bluetooth discovery).
- Pair the two phones in Android system settings first (the app lists bonded devices).
- In the app on both phones: enter the same passphrase.
- On phone A: “Start Server”.
- On phone B: “Scan”, select phone A, “Connect”.
- Chat.

Troubleshooting (Android)
- Nothing in Scan: pair devices in system settings first, then reopen the app and Scan.
- Cannot connect: ensure one side started Server, Bluetooth is ON, and devices are paired.
- Permissions: make sure Bluetooth and Location are granted and Location is ON.


## Security Notes
- Encryption uses AES‑256‑GCM with a key derived from your passphrase (PBKDF2‑HMAC‑SHA256, 200k iterations, random salt).
- Anyone with the passphrase can read messages on that session. Use a strong passphrase and share it securely.
- This sample is for educational use; review and harden before using for sensitive data.


## Limitations
- One‑to‑one chat (first incoming connection is accepted).
- Android lists bonded devices only (to avoid background discovery code complexity).
- macOS not supported (classic RFCOMM not available via PyBluez).


## FAQ
- Q: Do I need Internet?  A: No. It’s Bluetooth P2P only.
- Q: Do I need Android Studio?  A: No. Use Buildozer (CLI) on Linux/WSL2.
- Q: Do both sides need the same passphrase?  A: Yes, or decryption will fail and raw text will show.


## License

MIT
