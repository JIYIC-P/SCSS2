from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QPixmap,QImage

from PyQt5.QtWidgets import QMainWindow,QDialog
from Ui.window_mian import Ui_MainWindow
from common.data_bus import DataBus
from Ui.widget_choose import Ui_Form
from Ui.dialog_mode_change import Ui_modechange as Modechange
import numpy as np



class ChooseColorDialog(QDialog):
    def __init__(self,mode):
        super().__init__()
        self.ui = Modechange()
        self.ui.setupUi(self)
        self.setWindowTitle("模式选择")
        self.ui.label.setText(f"是否选择{mode}模式？")
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)


    # def on_accept(self):
    #     self.accept()


    # def on_reject(self):
    #     self.reject()




class MainWindowLogic(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)   # self 就是 QMainWindow 实例
        self.bus = DataBus()


        # 绑定信号
        self.ui.action_ToColorMode.triggered.connect(self.changemode)
        self.ui.action_ToYoloMode.triggered.connect(self.changemode)
        self.ui.action_ToClipMode.triggered.connect(self.changemode)
        self.ui.action_ToHhitMode.triggered.connect(self.changemode)
        self.bus.camera0_img.connect(self.update_mianframe)
        self.bus.camera1_img.connect(self.update_secondframe)




    def ndarry2pixmap(self,array: np.ndarray):
        height, width, channel = array.shape
        bytes_per_line = width * channel
        import cv2
        rgb_array = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
        qimage = QImage(
            rgb_array.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888  # 3通道 RGB 格式
        )
        pixmap = QPixmap.fromImage(qimage)

        return pixmap
    
    def update_mianframe(self,array: np.ndarray):
        self.ui.lab_ShowFrame0Pic.setPixmap(self.ndarry2pixmap(array))


    def update_secondframe(self,array: np.ndarray):
        self.ui.lab_ShowFrame1Pic.setPixmap(self.ndarry2pixmap(array))

    def changemode(self):
        action = self.sender()
        if not action:
            return
        mode = action.text()
        if mode is not None:
            dialog = ChooseColorDialog(mode)
            if mode == '颜色':
                mode = 'color'
            elif mode == '高光谱':
                mode = 'hhit'
            result = dialog.exec_()
            if result == QDialog.Accepted:
                self.bus.mode_changed.emit(mode)


       


    @pyqtSlot(int)
    def update_do_led(self, do):
        for i in range(5):
            self.leds[i].setStyleSheet("background:red" if do & (1<<i) else "background:gray")