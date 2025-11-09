from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow
from Ui.window_mian import Ui_MainWindow
from common.data_bus import DataBus
from Ui.widget_choose import Ui_Form




class MainWindowLogic(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)   # self 就是 QMainWindow 实例
        self.bus = DataBus()


        # 绑定信号
        self.ui.action_ToColorMode.connectNotify(self.changemode)
        #connect(self.changemode)
        # self.ui.action_ToYoloMode.connect(self.changemode)
        # self.ui.action_ToClipMode.connect(self.changemode)
        # self.ui.action_ToHhitMode.connect(self.changemode)

        # self.bus.pcie_di_update.connect(self.update_di_lcd)
        # self.bus.camera0_img.connect(self.set_cam0_label)
        # self.bus.algo_result.connect(self.update_result_table)
        # self.bus.push_rods.connect(self.update_do_led)


    def changemode(self):
        action = self.sender()
        if not action:
            return
        mode = action.text()
        
        if mode :
            print(mode)
    
    @pyqtSlot(int)
    def update_do_led(self, do):
        for i in range(5):
            self.leds[i].setStyleSheet("background:red" if do & (1<<i) else "background:gray")