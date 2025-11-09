import sys, pathlib
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
from Ui.Ui_logic import MainWindowLogic
from communicator.manager import Manager
from logic.logic_handler import Updater                

app = QApplication(sys.argv)
cfg = None
# 2. 主窗口（主线程）
win = MainWindowLogic()
win.show()

# 3. 通信线程
comm_mgr  = Manager()

# 4. 逻辑线程
logic_mgr = Updater(comm_mgr)

# 5. 信号连线（跨线程自动排队）
from common.data_bus import DataBus
bus = DataBus()
bus.mode_changed.connect(comm_mgr.setmode)
bus.mode_changed.connect(logic_mgr.setmode)



#6. 退出时序
def clean():
    comm_mgr.stop()
    logic_mgr.stop()
app.aboutToQuit.connect(clean)

sys.exit(app.exec_())