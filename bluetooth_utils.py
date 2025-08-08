import threading
import sys
import time
from typing import Callable, List, Optional, Tuple

# Backend selection: PyBluez on desktop, pyjnius on Android

UUID_SPP = "94f39d29-7d6d-437d-973b-fba39e49d4ee"  # random UUID for our service


class BluetoothManager:
    """Cross-platform Bluetooth RFCOMM helper.

    Desktop (Windows/Linux): uses PyBluez.
    Android: uses Java Bluetooth API via pyjnius (paired devices only for simplicity).
    """

    def __init__(self):
        self.on_message: Optional[Callable[[str], None]] = None
        self._recv_thread: Optional[threading.Thread] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._connected = False
        self._client_sock = None
        self._server_sock = None
        self._backend = None
        self._port = None
        self._is_android = False

        # Try Android backend first
        try:
            from jnius import autoclass  # type: ignore

            self._is_android = True
            self._backend = "android"
            # cache classes
            self._BtAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            self._UUID = autoclass("java.util.UUID")
            self._BtDevice = autoclass("android.bluetooth.BluetoothDevice")
            self._BtServerSocket = autoclass("android.bluetooth.BluetoothServerSocket")
            self._BtSocket = autoclass("android.bluetooth.BluetoothSocket")
            self._JavaString = autoclass("java.lang.String")
            self._adapter = self._BtAdapter.getDefaultAdapter()
        except Exception:
            self._is_android = False

        if not self._is_android:
            # Fallback to PyBluez
            try:
                import bluetooth  # type: ignore

                self._bluetooth = bluetooth
                self._backend = "pybluez"
            except Exception:
                self._backend = None

    # -------------- Common API --------------
    def is_available(self) -> bool:
        return self._backend is not None

    def is_android(self) -> bool:
        return self._is_android

    def scan_devices(self, timeout: int = 8) -> List[Tuple[str, str]]:
        """Return list of (name, address). On Android returns bonded devices."""
        if self._backend == "pybluez":
            devs = []
            try:
                devs = self._bluetooth.discover_devices(duration=timeout, lookup_names=True)  # type: ignore
            except Exception:
                devs = []
            return [(name or addr, addr) for addr, name in devs]
        elif self._backend == "android":
            # Paired devices only to avoid BroadcastReceiver complexity
            result = []
            try:
                bonded = self._adapter.getBondedDevices().toArray()
                for d in bonded:
                    name = d.getName()
                    addr = d.getAddress()
                    result.append((name or addr, addr))
            except Exception:
                pass
            return result
        else:
            return []

    def start_server(self) -> bool:
        """Start RFCOMM server socket and accept exactly one client in background."""
        if self._backend == "pybluez":
            return self._start_server_pybluez()
        elif self._backend == "android":
            return self._start_server_android()
        return False

    def connect(self, address: str) -> bool:
        if self._backend == "pybluez":
            return self._connect_pybluez(address)
        elif self._backend == "android":
            return self._connect_android(address)
        return False

    def send_line(self, line: str) -> bool:
        if not self._connected or not self._client_sock:
            return False
        data = (line + "\n").encode("utf-8")
        try:
            if self._backend == "pybluez":
                self._client_sock.sendall(data)
            elif self._backend == "android":
                out = self._client_sock.getOutputStream()
                out.write(data)
                out.flush()
            return True
        except Exception:
            return False

    def close(self):
        self._stop_event.set()
        try:
            if self._recv_thread and self._recv_thread.is_alive():
                self._recv_thread.join(timeout=0.5)
        except Exception:
            pass
        try:
            if self._accept_thread and self._accept_thread.is_alive():
                self._accept_thread.join(timeout=0.5)
        except Exception:
            pass
        try:
            if self._client_sock:
                if self._backend == "pybluez":
                    self._client_sock.close()
                elif self._backend == "android":
                    self._client_sock.close()
        except Exception:
            pass
        try:
            if self._server_sock:
                if self._backend == "pybluez":
                    self._server_sock.close()
                elif self._backend == "android":
                    self._server_sock.close()
        except Exception:
            pass
        self._connected = False
        self._client_sock = None
        self._server_sock = None

    # -------------- PyBluez backend --------------
    def _start_server_pybluez(self) -> bool:
        try:
            self._server_sock = self._bluetooth.BluetoothSocket(self._bluetooth.RFCOMM)
            # Bind to channel 1 so client fallback works cross-platform
            self._server_sock.bind(("", 1))
            self._server_sock.listen(1)
            self._port = 1
            try:
                self._bluetooth.advertise_service(
                    self._server_sock,
                    "BitChatLite",
                    service_id=UUID_SPP,
                    service_classes=[UUID_SPP, self._bluetooth.SERIAL_PORT_CLASS],
                    profiles=[self._bluetooth.SERIAL_PORT_PROFILE],
                )
            except Exception:
                # Not critical; Windows often lacks SDP/advertising
                pass

            self._accept_thread = threading.Thread(target=self._accept_loop_pybluez, daemon=True)
            self._accept_thread.start()
            return True
        except Exception:
            return False

    def _accept_loop_pybluez(self):
        try:
            client_sock, client_info = self._server_sock.accept()
            self._client_sock = client_sock
            self._connected = True
            self._start_recv_thread()
        except Exception:
            pass

    def _connect_pybluez(self, address: str) -> bool:
        try:
            # Try service discovery to find port
            svc = self._bluetooth.find_service(uuid=UUID_SPP, address=address)
            port = None
            if svc:
                port = svc[0]["port"]
            if port is None:
                # Fallback to common RFCOMM channel 1 (matches our server bind)
                port = 1
            sock = self._bluetooth.BluetoothSocket(self._bluetooth.RFCOMM)
            sock.connect((address, port))
            self._client_sock = sock
            self._connected = True
            self._start_recv_thread()
            return True
        except Exception:
            return False

    def _recv_loop_pybluez(self):
        buf = b""
        while not self._stop_event.is_set() and self._connected and self._client_sock:
            try:
                chunk = self._client_sock.recv(1024)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if self.on_message:
                        try:
                            self.on_message(line.decode("utf-8"))
                        except Exception:
                            pass
            except Exception:
                break
        self._connected = False

    # -------------- Android backend --------------
    def _start_server_android(self) -> bool:
        try:
            uuid = self._UUID.fromString(UUID_SPP)
            self._server_sock = self._adapter.listenUsingRfcommWithServiceRecord("BitChatLite", uuid)
            self._accept_thread = threading.Thread(target=self._accept_loop_android, daemon=True)
            self._accept_thread.start()
            return True
        except Exception:
            return False

    def _accept_loop_android(self):
        try:
            sock = self._server_sock.accept()  # blocks until connection
            self._client_sock = sock
            self._connected = True
            self._start_recv_thread()
        except Exception:
            pass

    def _connect_android(self, address: str) -> bool:
        try:
            device = self._adapter.getRemoteDevice(address)
            uuid = self._UUID.fromString(UUID_SPP)
            sock = device.createRfcommSocketToServiceRecord(uuid)
            self._adapter.cancelDiscovery()
            sock.connect()
            self._client_sock = sock
            self._connected = True
            self._start_recv_thread()
            return True
        except Exception:
            return False

    def _recv_loop_android(self):
        try:
            buf = bytearray()
            istream = self._client_sock.getInputStream()
            arr = bytearray(1024)
            mv = memoryview(arr)
            while not self._stop_event.is_set() and self._connected and self._client_sock:
                n = istream.read(mv)
                if n <= 0:
                    break
                buf.extend(mv[:n])
                while b"\n" in buf:
                    idx = buf.index(b"\n")
                    line = bytes(buf[:idx])
                    del buf[: idx + 1]
                    if self.on_message:
                        try:
                            self.on_message(line.decode("utf-8"))
                        except Exception:
                            pass
        except Exception:
            pass
        self._connected = False

    def _start_recv_thread(self):
        self._stop_event.clear()
        target = self._recv_loop_android if self._backend == "android" else self._recv_loop_pybluez
        self._recv_thread = threading.Thread(target=target, daemon=True)
        self._recv_thread.start()