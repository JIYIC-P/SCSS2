import communicator.camera
import communicator.FY5400
import communicator.mbs
import communicator.tcp

class manager():
    def __init__(self,mode):
        self.mode = mode
        """
        传入模式，根据模式判断来创建和管理对象
        """
    def start(self):
        """
        判断哪个mode，哪个mode需要哪些通信方式
        """
    def stop(self):
        """
        结束线程，但是保留对象
        """
    def changemode(self,mode):
        """
        根据传入的mode来选择启动和停止哪些对象及其线程
        """