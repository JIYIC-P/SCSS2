from PyQt5.QtCore import QObject, pyqtSignal
from common.config_manager import ConfigManager
import numpy as np



class DataBus(QObject):

    # ========= 前端 → 后台 =========
    mode_changed     = pyqtSignal(str)          # 用户切换模式
    manual_cmd       = pyqtSignal(int)          # 手动推杆
    worker           = pyqtSignal(list)   #手动设置工位讯息
    do_push          = pyqtSignal()  #控制推杆模式
    color_set        =pyqtSignal()    #颜色控制
    color_range      =pyqtSignal(int, int)    #颜色id和范围

    # ========= 通信 → 前端 =========
    pcie_di_update   = pyqtSignal(int)          # 16 位 DI

    camera0_img      = pyqtSignal(np.ndarray)     # 图片
    camera1_img      = pyqtSignal(np.ndarray)
    hhit_data        = pyqtSignal(np.ndarray)  # np.ndarray

    # ========= 逻辑 → 前端 =========
    algo_result      = pyqtSignal(dict)         # 识别结果
    push_rods        = pyqtSignal(int)          # 实际下发的 DO
    
    cfg = ConfigManager()
    # 单例实现
    _instance = None
    _initialized = False  # 类级别的标志

    def __new__(cls, *a, **k):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 使用类标志防止重复初始化
        if DataBus._initialized:
            return
        
        super().__init__()  # 必须先调用
        DataBus._initialized = True  # 标记已初始化