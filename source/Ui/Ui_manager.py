#!/usr/bin/python3

"""
ZetCode PyQt5 tutorial 
This program shows a confirmation message box when closing.
Author: Jan Bodnar (Modified)
"""

import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))


from Ui.main_window import Ui_MainWindow  
from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow

class app(QMainWindow):  
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)  

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, '确认退出', 
            "确定要退出程序吗？", 
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        window = app()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"发生错误：{str(e)}")


        