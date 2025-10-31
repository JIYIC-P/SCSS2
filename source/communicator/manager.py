import communicator.camera as camera
import communicator.FY5400 as pcie
import communicator.mbs as mbs
import communicator.tcp as hhit
from typing import Dict, List, Tuple, Optional
import numpy as np


def __float_to_int(arr: np.ndarray) -> np.ndarray:
    """先 clip 再四舍五入，最后 uint8，保证 0-6"""
    clipped = np.clip(arr, 0.0, 20.0)
    return np.round(clipped).astype(np.uint8)

def statistics_data(float_array: np.ndarray) -> List[int]:
    try:
        int_array = __float_to_int(float_array)
        counts = np.bincount(int_array, minlength=7)
        return counts.tolist()
    except Exception as e:
        print(f"统计数据出错（数组形状：{float_array.shape}）：{e}")
        return [0] * 7

class manager():

    def __init__(self,mode = None):
        """
        传入模式，根据模式判断来创建和管理对象
        初始化若传入mode 则启动，否则创建none对象
        """
        self.pcie=pcie.FY5400IO(0)
        self.camera0 = camera.ThreadedCamera(0)
        self.camera1=camera.ThreadedCamera(0)
        
        if mode is not None:
            self.pcie=pcie.FY5400IO(0)
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
            if self.mode in ('clip', 'yolo'): 
                # self.pcie=pcie.FY5400IO(0)
                self.camera0 = camera.ThreadedCamera(0)
                self.camera1=camera.ThreadedCamera(0)
                self.camera0.init_camera()     #打开一号相机 
                self.camera1.init_camera()     #打开二号相机  
                self.pcie.start() #启动板卡读线程
            elif self.mode=='color':
                self.camera0 = camera.ThreadedCamera(0)

                self.camera0.init_camera()     #打开一号相机  
                self.pcie.start() #启动板卡读线程
            elif self.mode=='hhit':
                self.hhit= hhit.ClassifierReceiver(on_transform_data=statistics_data)
                self.hhit.start(server_ip="192.168.1.16", port=5555, rcv_buf_size=1000) #启动hhit接收640
                self.pcie.start() #启动板卡读线程
    def stop(self):
        """
        结束线程，但是保留对象
        """
        if self.mode is not None:
            if self.mode in ('clip', 'yolo'): 
                self.camera0.close_cam()     #关闭一号相机 
                self.camera1.close_cam()     #关闭二号相机  
                self.pcie.stop() #关闭板卡读线程
            elif self.mode=='color':
                self.camera0.close_cam()     #关闭一号相机   
                self.pcie.stop() #启动板卡读线程
            elif self.mode=='hhit':
                self.hhit.stop()
                self.pcie.stop() #启动板卡读线程
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
