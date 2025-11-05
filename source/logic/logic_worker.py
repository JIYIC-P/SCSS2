import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))


from PyQt5.QtCore import QObject, pyqtSlot, QTimer
from logic.logic_handler import Updater          # 你的原来类
from common.data_bus import DataBus

class LogicWorker(QObject):
    def __init__(self, cfg):
        super().__init__()
        self.cfg  = cfg
        self.bus  = DataBus()
        self.comm = None   # 由外部注入 CommManager 实例
        self.up   = Updater(self.comm)   # 你的 updater
        # 定时识别
        self.__cycle = QTimer(self)
        self.__cycle.timeout.connect(self.__cycle_update)
        self.__cycle.start(50)   # 20 Hz

    # 模式切换
    @pyqtSlot(str)
    def set_mode(self, mode):
        self.up.setmode(mode)

    # 主循环
    def __cycle_update(self):
        self.up.update()          # 里面会 emit 推杆命令
        # 把推杆命令再转发给前端显示
        self.bus.push_rods.emit(self.up.last_do)

    # 前端手动推杆
    @pyqtSlot(int)
    def manual_push(self, do):
        self.comm.set_do(do)