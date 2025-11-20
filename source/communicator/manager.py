import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))


import communicator.camera as camera
import communicator.pcie as pcie
import communicator.mbs as mbs
import communicator.tcp as hhit
from common.data_bus import DataBus

class Manager():

    def __init__(self):
        """
        传入模式，根据模式判断来创建和管理对象
        初始化若传入mode 则启动，否则创建none对象
        """
        self.bus= DataBus()
        self.camera0 = None
        self.camera1 = None
        self.pcie = None
        self.hhit = None
        #self.bus.mode_changed.connect(self.changemode)
        self.mode = self.bus.cfg.get("qt","config","mode")
        self.start()
    
    # def setmode(self):

        

    def start(self):
        """
        判断哪个mode，哪个mode需要哪些通信方式
        """
        self.pcie=pcie.PcIeIO(0)
        self.pcie.start(0.01) #启动板卡读线程
        print("manager start")
        if self.mode is not None:
            if self.mode in ('clip', 'yolo'): 
                self.camera0 = camera.ThreadedCamera(0)
           #打开一号相机 
                self.camera1=camera.ThreadedCamera(1)     
                self.camera1.init_camera()     
                self.camera0.init_camera()  #打开二号相机  
                
            elif self.mode=='color':
                self.camera0 = camera.ThreadedCamera(0)
                self.camera0.init_camera()     #打开一号相机  
            elif self.mode=='hhit':
                self.hhit= hhit.ClassifierReceiver()
                self.hhit.start(server_ip=self.bus.cfg.get('tcp','address','ip'), port=self.bus.cfg.get('tcp','address','port'), rcv_buf_size=1000) #启动hhit接收640
                
    def stop(self):
        """
        结束线程，但保留对象状态
        """
        print("manager stop")
        if self.mode is not None:
            if self.pcie is not None:
                self.pcie.stop()
            if self.camera0 is not None:
                self.camera0.stop()  # 停止线程，但不释放对象
            if self.camera1 is not None:
                self.camera1.stop()  # 停止线程，但不释放对象
            if self.hhit is not None:
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
            
    def setmode(self, mode):
        print("manager setmode")
        if not self.pcie._running:
        #self.pcie=pcie.PcIeIO(0)
            self.pcie.start(0.01) #启动板卡读线程
        """
        根据传入的mode来选择启动和停止哪些对象及其线程。
        保留原有对象，仅根据模式差异调整线程状态。
        """
        if self.mode == mode:
            print("模式未改变，无需切换")
            return

        print(f"切换模式：从 {self.mode} 到 {mode}")

        # 保存当前模式的线程状态
        old_mode = self.mode

        # 根据目标模式调整对象线程状态
        if mode in ('clip', 'yolo'):
            # 新模式需要两个相机
            if self.camera0 is None:
                self.camera0 = camera.ThreadedCamera(0)
            if self.camera1 is None:
                self.camera1 = camera.ThreadedCamera(1)
            
            # 启动或重新启动相机线程
            if not self.camera0.camera_opened:
                self.camera0.init_camera()
            if not self.camera1.camera_opened:
                self.camera1.init_camera()

            # 如果之前是其他模式，停止不需要的对象
            if old_mode != 'clip' and old_mode != 'yolo':
  
                if self.hhit is not None:
                    self.hhit.stop()

        elif mode == 'color':
            # 新模式只需要一个相机
            if self.camera0 is None:
                self.camera0 = camera.ThreadedCamera(0)
            
            # 启动或重新启动相机线程
            if not self.camera0.camera_opened:
                self.camera0.init_camera()

            # 如果之前是其他模式，停止不需要的对象
            if old_mode != 'color':
                if self.camera1 is not None:
                    self.camera1.stop()

                if self.hhit is not None:
                    self.hhit.stop()

        elif mode == 'hhit':
            # 新模式需要 TCP 接收器
            if self.hhit is None:
                self.hhit = hhit.ClassifierReceiver()
            
            # 启动或重新启动 TCP 接收器
            if not self.hhit.is_running():
                self.hhit.start(server_ip=self.bus.cfg.get('tcp', 'address', 'ip'),
                                port=self.bus.cfg.get('tcp', 'address', 'port'),
                                rcv_buf_size=1000)

            # 如果之前是其他模式，停止不需要的对象
            if old_mode != 'hhit':
                if self.camera0 is not None:
                    self.camera0.stop()
                if self.camera1 is not None:
                    self.camera1.stop()


        # 更新当前模式
        self.mode = mode
        print(f"模式切换完成，当前模式：{self.mode}")


