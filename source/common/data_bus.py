from PyQt5.QtCore import QObject, pyqtSignal
from common.config_manager import ConfigManager

class DataBus(QObject):
    # ========= 前端 → 后台 =========
    mode_changed     = pyqtSignal(str)          # 用户切换模式
    manual_cmd       = pyqtSignal(int)          # 手动推杆

    # ========= 通信 → 前端 =========
    pcie_di_update   = pyqtSignal(int)          # 16 位 DI
    camera0_img      = pyqtSignal('QImage')     # 图片
    camera1_img      = pyqtSignal('QImage')
    hhit_data        = pyqtSignal('PyQt_PyObject')  # np.ndarray

    # ========= 逻辑 → 前端 =========
    algo_result      = pyqtSignal(dict)         # 识别结果
    push_rods        = pyqtSignal(int)          # 实际下发的 DO
    
    cfg = ConfigManager()

    # 单例
    _instance = None
    def __new__(cls, *a, **k):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance