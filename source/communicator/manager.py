import communicator.camera as camera
import communicator.FY5400 as pcie
import communicator.mbs as mbs
import communicator.tcp as hhit

class manager():
    
    def __init__(self,mode = None):
        """
        传入模式，根据模式判断来创建和管理对象
        初始化若传入mode 则启动，否则创建none对象
        """
        if mode is not None:
            self.mode = mode
            self.start()
        else:
            self.camera0 = None
            self.camera1 = None
            self.pcie = None
            self.hhit = None
        

    def start(self):
        """
        判断哪个mode，哪个mode需要哪些通信方式
        """
        if self.mode is not None:
            pass
    def stop(self):
        """
        结束线程，但是保留对象
        """
        if self.mode is not None:
            pass
        else :
            """
            此处加入对象检测，保证完全关闭
            """
    def changemode(self,mode):
        """
        根据传入的mode来选择启动和停止哪些对象及其线程
        """
        self.stop()
        self.mode = mode
        self.start()
