from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
import socket
import json
import logging
import os

class WorkerSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

import struct

class Worker(QRunnable):
    def __init__(self, request):
        super().__init__()
        self.request = request
        self.signals = WorkerSignals()

    def run(self):
        ip_file = "server_ip.txt"
        HOST = self.get_server_ip(ip_file)
        PORT = 9999
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((HOST, PORT))
                sock.sendall(json.dumps(self.request).encode('utf-8'))

                length_prefix = sock.recv(4)
                if not length_prefix:
                    self.signals.error.emit("No length prefix received from server.")
                    return
                message_length = struct.unpack('!I', length_prefix)[0]

                chunks = []
                bytes_recd = 0
                while bytes_recd < message_length:
                    chunk = sock.recv(min(message_length - bytes_recd, 2048))
                    if not chunk:
                        self.signals.error.emit("Connection closed while receiving data.")
                        return
                    chunks.append(chunk)
                    bytes_recd += len(chunk)

                response = b''.join(chunks)
                try:
                    data = json.loads(response.decode('utf-8'))
                    self.signals.finished.emit(data)
                except json.JSONDecodeError as e:
                    self.signals.error.emit(f"Decoding error: {e}")
        except ConnectionRefusedError:
            self.signals.error.emit("Could not connect to server.")
        except Exception as e:
            self.signals.error.emit(f"Error: {e}")

    def get_server_ip(self, ip_file):
        try:
            if os.path.exists(ip_file):
                with open(ip_file, "r") as f:
                    custom_ip = f.read().strip()
                    if custom_ip:
                        return custom_ip
            return "localhost"
        except Exception as e:
            logging.error(f"Ошибка чтения IP из файла {ip_file}: {e}")
            return "localhost"
