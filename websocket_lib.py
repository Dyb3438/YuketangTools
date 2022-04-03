import websocket
import json
import cv2
import requests
import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject, QThread

# websocket.enableTrace(True)
class Websocket(QThread):
    login_qrcode = pyqtSignal(dict)
    login_success = pyqtSignal(dict)
    query_qrcode = pyqtSignal()
    def __init__(self, address):
        super().__init__()
        self.sock = websocket.WebSocketApp(address,
                                           on_open=self.on_open,
                                           on_message=self.on_message,
                                           on_close=self.on_close
                                          )
        self.query_qrcode.connect(self.send_login)
        return
    
    def on_open(self, ws):
        print('Websocket is created!')
        print('Now query the login package.')
        self.send_login()
        return
    
    def on_message(self, ws, msg):
        msg = json.loads(msg)
        if msg['op'] == "requestlogin":
            self.login_qrcode.emit(msg)
        elif msg['op'] == "loginsuccess":
            self.login_success.emit(msg)
        return
    
    def on_close(self, *args):
        print('Websocket is closed')
        return
    
    def send_login(self):
        self.sock.send(json.dumps({"op":"requestlogin","role":"web","version":1.4,"type":"qrcode","from":"web"}))
        return
    
    def run(self):
        self.sock.run_forever()