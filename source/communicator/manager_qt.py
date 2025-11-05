import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from communicator import camera, tcp as hhit
from common.data_bus import DataBus
from communicator import pcie  

class ManagerQt(QObject):
    def __init__(self, cfg):
        super().__init__()
        self.cfg  = cfg
        self.bus  = DataBus()
        self.mode = None
        self.camera0 = None
        self.camera1 = None
        self.pcie    = None
        self.hhit    = None
        # 定时器：每 30 ms 把 DI 发出去
        self.__di_timer = QTimer(self)
        self.__di_timer.timeout.connect(self.__poll_di)
        self.__di_timer.start(30)

    # ---------- 模式切换 ----------
    def set_mode(self, mode):
        self.stop()
        self.mode = mode
        self.start()

    # ---------- 启动/停止 ----------
    def start(self):
        if self.mode is None: return
        self.pcie = pcie.PcIeIO(0)
        self.pcie.start()
        if self.mode in ('clip', 'yolo'):
            self.camera0 = camera.ThreadedCamera(0)
            self.camera1 = camera.ThreadedCamera(1)
            self.camera0.init_camera()
            self.camera1.init_camera()
        elif self.mode == 'color':
            self.camera0 = camera.ThreadedCamera(0)
            self.camera0.init_camera()
        elif self.mode == 'hhit':
            self.hhit = hhit.ClassifierReceiver()
            self.hhit.start(server_ip="192.168.1.16", port=5555)
            # 把高光谱数据转发
            self.hhit.new_data.connect(lambda arr: self.bus.hhit_data.emit(arr))

    def stop(self):
        if self.pcie:
            self.pcie.stop()
        if self.camera0:
            self.camera0.close_cam()
        if self.camera1:
            self.camera1.close_cam()
        if self.hhit:
            self.hhit.stop()

    # ---------- 轮询 DI ----------
    def __poll_di(self):
        if self.pcie:
            di = self.pcie.get_di()
            self.bus.pcie_di_update.emit(di)

    # ---------- 前端下达 DO ----------
    @pyqtSlot(int)
    def set_do(self, do):
        if self.pcie:
            self.pcie.set_do(do)