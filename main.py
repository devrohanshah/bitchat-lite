from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout

from bluetooth_utils import BluetoothManager
from encryption import encrypt_text, decrypt_text


class ChatRoot(BoxLayout):
    passphrase = StringProperty("")
    chat_log = StringProperty("")
    connected = BooleanProperty(False)
    server_running = BooleanProperty(False)
    devices = ListProperty([])  # list of display strings "Name (AA:BB:...)"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bt = BluetoothManager()
        self.addr_map = {}
        self.bt.on_message = self._on_bt_message
        # Request Android runtime permissions if needed
        if self.bt.is_android():
            try:
                from android.permissions import request_permissions, Permission  # type: ignore

                request_permissions(
                    [
                        Permission.BLUETOOTH,
                        Permission.BLUETOOTH_ADMIN,
                        Permission.BLUETOOTH_CONNECT,
                        Permission.BLUETOOTH_SCAN,
                        Permission.ACCESS_FINE_LOCATION,
                    ]
                )
            except Exception:
                pass

    def append_chat(self, line: str):
        self.chat_log = (self.chat_log + ("\n" if self.chat_log else "") + line)[-10_000:]

    def do_scan(self):
        if not self.bt.is_available():
            self.append_chat("[!] Bluetooth backend not available on this platform.")
            return
        devs = self.bt.scan_devices(timeout=8)
        self.addr_map = {}
        disp = []
        for name, addr in devs:
            tag = f"{name} ({addr})"
            disp.append(tag)
            self.addr_map[tag] = addr
        self.devices = disp
        if not disp:
            self.append_chat("[i] No devices found. On Android, pair in system settings first.")

    def start_server(self):
        if not self.bt.is_available():
            self.append_chat("[!] Bluetooth backend not available.")
            return
        ok = self.bt.start_server()
        self.server_running = ok
        if ok:
            self.append_chat("[i] Server started. Waiting for a peer to connect...")
        else:
            self.append_chat("[!] Failed to start server.")

    def connect_selected(self, selection_text: str):
        if not selection_text:
            self.append_chat("[!] Select a device first.")
            return
        addr = self.addr_map.get(selection_text)
        if not addr:
            self.append_chat("[!] Could not resolve device address.")
            return
        ok = self.bt.connect(addr)
        self.connected = ok
        if ok:
            self.append_chat(f"[i] Connected to {selection_text}.")
        else:
            self.append_chat("[!] Connection failed.")

    def _on_bt_message(self, line: str):
        # Called from background thread; switch to UI thread
        def _ui(_dt):
            text = line
            if self.passphrase:
                try:
                    text = decrypt_text(line, self.passphrase)
                except Exception:
                    # show raw if decrypt fails
                    pass
            self.append_chat(f"Peer: {text}")
        Clock.schedule_once(_ui)

    def send_msg(self, text: str):
        if not text.strip():
            return
        if not self.bt or not self.bt.is_available():
            self.append_chat("[!] Bluetooth not available.")
            return
        if not self.passphrase:
            self.append_chat("[!] Set a shared passphrase first.")
            return
        try:
            token = encrypt_text(text, self.passphrase)
        except Exception as e:
            self.append_chat(f"[!] Encrypt failed: {e}")
            return
        ok = self.bt.send_line(token)
        if ok:
            self.append_chat(f"Me: {text}")
            self.ids.msg_input.text = ""
        else:
            self.append_chat("[!] Send failed (not connected?).")

    def on_stop(self):
        try:
            self.bt.close()
        except Exception:
            pass


class BitChatLiteApp(App):
    def build(self):
        Builder.load_file("chat.kv")
        return ChatRoot()

    def on_stop(self):
        if isinstance(self.root, ChatRoot):
            self.root.on_stop()


if __name__ == "__main__":
    BitChatLiteApp().run()
