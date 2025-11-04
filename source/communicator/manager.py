import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))


import communicator.camera as camera
import communicator.FY5400 as pcie
import communicator.mbs as mbs
import communicator.tcp as hhit


'''
tcp回调函数，复用
'''

# def __float_to_int(arr: np.ndarray) -> np.ndarray:
#     """先 clip 再四舍五入，最后 uint8，保证 0-6"""
#     clipped = np.clip(arr, 0.0, 20.0)
#     return np.round(clipped).astype(np.uint8)

# def statistics_data(float_array: np.ndarray) -> List[int]:
#     try:
#         int_array = __float_to_int(float_array)
#         counts = np.bincount(int_array, minlength=7)
#         return counts.tolist()
#     except Exception as e:
#         print(f"统计数据出错（数组形状：{float_array.shape}）：{e}")
#         return [0] * 7




class manager():

    def __init__(self):
        """
        传入模式，根据模式判断来创建和管理对象
        初始化若传入mode 则启动，否则创建none对象
        """

        self.camera0 = None
        self.camera1 = None
        self.pcie = None
        self.hhit = None
    
    def setmode(self,mode):
        self.mode = mode
        self.start()

    def start(self):
        """
        判断哪个mode，哪个mode需要哪些通信方式
        """
        if self.mode is not None:
            self.pcie=pcie.FY5400IO(0)
            self.pcie.start() #启动板卡读线程
            if self.mode in ('clip', 'yolo'): 
                self.camera0 = camera.ThreadedCamera(0)
                self.camera1=camera.ThreadedCamera(0)
                self.camera0.init_camera()     #打开一号相机 
                self.camera1.init_camera()     #打开二号相机  
                
            elif self.mode=='color':
                self.camera0 = camera.ThreadedCamera(0)
                self.camera0.init_camera()     #打开一号相机  
                
            elif self.mode=='hhit':
                self.hhit= hhit.ClassifierReceiver()
                self.hhit.start(server_ip="192.168.1.16", port=5555, rcv_buf_size=1000) #启动hhit接收640
                
    def stop(self):
        """
        结束线程，但是保留对象
        """
        if self.mode is not None:
            self.pcie.stop() 
            if self.mode in ('clip', 'yolo'): 
                self.camera0.close_cam()     #关闭一号相机 
                self.camera1.close_cam()     #关闭二号相机  
                
            elif self.mode=='color':
                self.camera0.close_cam()     #关闭一号相机   
                
            elif self.mode=='hhit':
                self.hhit.stop()
                

        """
        此处加入对象检测，保证完全关闭
        """      
    # 相机 0
        if self.camera0 is not None:
            try:
                self.camera0.close_cam()
            except Exception as e:
                print(f"[WARN] camera0 close failed: {e}")
            self.camera0 = None

        # 相机 1
        if self.camera1 is not None:
            try:
                self.camera1.close_cam()
            except Exception as e:
                print(f"[WARN] camera1 close failed: {e}")
            self.camera1 = None

        # 板卡
        if self.pcie is not None:
            try:
                self.pcie.stop()
            except Exception as e:
                print(f"[WARN] pcie stop failed: {e}")
            self.pcie = None

        # hhit TCP 接收器
        if self.hhit is not None:
            try:
                self.hhit.stop()
            except Exception as e:
                print(f"[WARN] hhit stop failed: {e}")
            self.hhit = None
            
    def changemode(self,mode):
        """
        根据传入的mode来选择启动和停止哪些对象及其线程
        """
        self.stop()
        self.mode = mode
        self.start()
