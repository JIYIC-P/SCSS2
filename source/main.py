import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))



from Ui.Ui_manager import core 
import logic.logic_handler as UPDATE
import communicator.manager
from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow


def main():
    """
    此函数为整个程序的启动入口
    启动流程：
    1.应当创建配置管理类，加载配置
    2.根据配置启动前端：（包含交互界面等信息，只记录信息和改变）
    3.待前端准备好后，启动通信管理类，只创建对象，不启动线程
    4.启动逻辑处理类，只创建对象，不启动线程
    5.主循环（获取前端用户操作，如果操作对应更新）
    """
    try:
        app = QApplication(sys.argv)
        window = core()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"发生错误：{str(e)}")

if __name__ == "__main__":
    main()

