import sys, pathlib
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
from Ui.main_window_logic import MainWindowLogic
from communicator.manager_qt import CommManager
from logic.logic_worker import LogicWorker
from common.config_manager import ConfigManager

app = QApplication(sys.argv)

# 1. 配置
cfg = ConfigManager()

# 2. 主窗口（主线程）
win = MainWindowLogic()
win.show()

# 3. 通信线程
comm_thread = QThread()
comm_mgr  = CommManager(cfg)
comm_mgr.moveToThread(comm_thread)
comm_thread.start()

# 4. 逻辑线程
logic_thread = QThread()
logic_mgr = LogicWorker(cfg)
logic_mgr.comm = comm_mgr   # 注入通信实例
logic_mgr.moveToThread(logic_thread)
logic_thread.start()

# 5. 信号连线（跨线程自动排队）
from common.data_bus import DataBus
bus = DataBus()
bus.mode_changed.connect(comm_mgr.set_mode)
bus.mode_changed.connect(logic_mgr.set_mode)
bus.manual_cmd.connect(comm_mgr.set_do)

# 6. 退出时序
def clean():
    comm_mgr.stop()
    logic_mgr.__cycle.stop()
    comm_thread.quit(),  logic_thread.quit()
    comm_thread.wait(), logic_thread.wait()
app.aboutToQuit.connect(clean)

sys.exit(app.exec_())