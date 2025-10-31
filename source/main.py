import pathlib,sys
root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))


import Ui #PYQT界面
import logic.logic_handler as UPDATE
#import communicator.

import communicator.manager

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

if __name__ == "__main__":
    main()
