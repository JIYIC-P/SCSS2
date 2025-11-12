import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))



from logic.yolo_mode import yoloClass as yolo_mode
from logic.color_mode import colorClass as color_mode
from logic.clip_mode import clipClass as clip_mode
from logic.hhit_mode import hhitClass as hhit_mode

from common.data_bus import DataBus
from common.config_manager import ConfigManager


import time
from threading import Thread
import asyncio

import cv2
import numpy as np
from PyQt5.QtGui import QImage,QPixmap
'''
工具函数
'''
def ndarray_to_qimage(img_bgr: np.ndarray) -> QImage:
    """OpenCV BGR 图 → RGB888 QImage"""
    h, w, ch = img_bgr.shape
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    bytes_per_line = ch * w
    return QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()


def cut_img(frame,x,width,y,height):
    '''裁剪图片'''
    # OpenCV 的裁剪操作是通过 NumPy 的数组切片实现的
    return frame[y:y + height, x:x + width]



class Updater():
    """
    fix
    此类用于将四个模式的调用封装到一起，提供一个update函数，此函数用于更新

    1 . update（）循环
    2 . 获取数据（图片，传感器信息，numpy统计结果）
    3 . 四个模式各自的处理方法。 返回物品ID有范围
    4 . 根据id发出指令（根据传感器信息）


    缓存图片，识别结果等信息，供前端显示调用
    """
    def __init__(self,communicator):
        """
        初始化传入通信管理对象，其模式与此类模式应统一
        update（）函数执行时只检测对象的数据（可以是信号量）是否准备完毕，不参与对象管理
        # """
        self.com_model = communicator
        self.hhit_signal=None
        self.frame0=None
        self.frame1=None
        self.pcie_signal=None
        self.pcie_status=None
        self.count=0
        self.worker=[[],[],[],[],[]]
        self.obj=[0,0,0,0,0] #物品,暂时命名，具体含义是存放衣服序列的变化
        #每个工位创建一个队列，存放要推的衣服顺序序列
        self.count_worker_queues=[[],[],[],[],[]]
        self.mode=None
        self.bus=DataBus()

        self.clip_mode=None
        self.color_mode=None
        self.yolo_mode=None
        self.hhit_mode=None

        self.push_signal=False
        self.setcolor_signal=False

        self.bus.mode_changed.connect(self.setmode)
        self.bus.manual_cmd.connect(self.send_order)
        self.bus.worker.connect(self.setworker)
        self.bus.do_push.connect(self.doPush)
        self.bus.color_set.connect(self.setColor)
        self.bus.color_range.connect(self.colorRange)
        
        

        self._is_running = True
        self._sleep_time_ms = 10 / 1000.0  # 100ms => 0.1s
        self.init_thread()


        # pice signal : 0xFFFF--> 0,1,2,3,4,5：目前有效位，这六位转化为上升下降沿信号： 0 ：上升沿 1 ：下降沿 -1 ：保持





    def doPush(self):
       self.push_signal=not self.push_signal
    def setColor(self):
        pass
    def colorRange(self):
        pass


    def run(self):
        """线程主循环，在此不断调用 update()"""
        while self._is_running:
            try:
                self.update()
                time.sleep(self._sleep_time_ms)
            except Exception as e:
                print(f"[UpdaterThread] 运行出错: {e}")
                break

    def init_thread(self):
        time.sleep(1) 
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        """安全停止线程的方法"""
        self._is_running = False


    def get_data(self):
        """

        调用传入的对象的数据
        必做：
        
        1.获取传感器信息

        选择：
        2.获取图片（形状模式）
        3.获取hhit统计结果/原始信息
        """
        self.pcie_signal=self.com_model.pcie.get_di() #获取pcie信息
       
        self.bus.pcie_di_update.emit(self.pcie_signal)  #发射相机一数据
       

        self.pcie_status=self.com_model.pcie.status_judg(self.pcie_signal)
        if self.com_model.mode in ('clip', 'yolo'): 
            if self.com_model.camera0 is None or self.com_model.camera1 is None:
                print("[ERROR] 相机未正确初始化！")
                return
            self.frame0 = self.com_model.camera0.grab_frame() #获取相机一的图片信息
            self.frame1 = self.com_model.camera1.grab_frame() #获取相机二的图片信息
        elif self.com_model.mode=='color':
            self.frame0 = self.com_model.camera0.grab_frame() #获取相机一的图片信息
        elif self.com_model.mode=='hhit':
            self.hhit_signal=self.com_model.hhit.float_array_np.copy() #获取原始hhit信息


    def setmode(self,mode):
      
        self.mode = mode
        self.com_model.setmode(mode)

        if ConfigManager().get(f"{self.mode}worker") is not None:
            self.worker=ConfigManager().get(f"{self.mode}worker")
        

    def setworker(self,workerlist):
        self.worker=workerlist
        ConfigManager().set(f"{self.mode}worker",value=self.worker)


    def generate_order(self,result):
        """
        传入ID和工位信息
        根据其内容生成并返回16进制指令


        详细解释：


        1.order ：
                0x0000 默认值 -|推动0号推杆|->             0x0001(0000000000000001)
                0x0000 默认值 -|推动1号推杆|->             0x0002(0000000000000010)        
                0x0000 默认值 -|同时推动五个推杆|->         0x001F(0000000000011111)
        2.worker: list[5]:[1,2,3,4,5] -> 值代表衣服种类 worker-->
        3.ID： int -> 值代表衣服种类
        """

        cloth_id = result["ID"] 
        delay_key=self.bus.cfg.find_key_path(self.bus.cfg.get(f"{self.mode}_mode"),cloth_id) 
        delay=self.bus.cfg.get(f"{self.mode}_mode","delay",delay_key)        # 衣服类别
        #delays
        for idx, worker_id in enumerate(self.worker):   # worker = [1,2,3,4,5]
            if cloth_id in worker_id:                   # 找到目标工位
                # 把衣服编号写进对应队列
                self.count_worker_queues[idx].append(result["count"])
                #把衣服编号写入对应obj
                self.obj[0]=result["count"]
        
        for i in range(len(self.worker)):
            if len(self.count_worker_queues[i]) == 0:
                continue
            if self.pcie_status[i+1]==1:#判断是否触发上升沿
                if self.count_worker_queues[i][0]==self.obj[i]:
                    self.obj[i]=0
                    if self.count_worker_queues[i]:
                        self.count_worker_queues[i].pop(0)
                        return i,delay
                else:
                    self.obj.pop()        # 去掉最右边
                    self.obj.insert(0, 0) # 最左边插 0
        return False
        #分别取每一个对列的首元素和obj[i]比较，例如  self.count_worker2与obj[1]比较                 




    def send_order(self,add,delay):
        """
        调用pcie通信对象，发送指令
        """
        asyncio.run(self.com_model.pcie.Do_bit(add,delay))


    def update(self):
        """
        2 . 获取数据（图片，传感器信息，numpy统计结果）
        3 . 四个模式各自的处理方法。 返回物品ID有范围
        4 . 根据id发出指令（根据传感器信息）

        """
        self.get_data()
        result= self.Judgment()
        if result is not None:
            pusherid, delay = self.generate_order(result)
            self.bus.push_rods.emit(pusherid)#  发送控制指令信息
            self.send_order(pusherid,delay)


    def Judgment(self):
        #TODO： match_j待完善
        '''注意只返回ID，最后记得统一返回值类型和数量'''
        if self.mode=="yolo":
            if self.yolo_mode is None:
                self.yolo_mode=yolo_mode()
            if self.frame0 is not None and self.frame1 is not None:
                frame_cut0 = cut_img(self.frame0, 470, 1136, 0, 1080)
                frame_cut1 = cut_img(self.frame1, 470, 1136, 0, 1080)
                frame, ID, _ = self.yolo_mode.match_shape(frame_cut0,frame_cut1)#返回的有三个值，目前只用ID
                #这里有点小问题，ID是否有效
                self.count+=1

                self.bus.algo_result.emit({"ID": ID, "count": self.count})
                '''这里应该返回，还没有结束'''
                self.bus.camera0_img.emit(frame) #发射相机一裁剪后的图片
                self.bus.camera1_img.emit(frame_cut1)#发射相机二元数据
                
                return {"ID": ID, "count": self.count}
                #return {"ID": random.randint(1,5), "count": self.count}
        if self.mode=='color':

            if self.color_mode is None:
                self.color_mode=color_mode()
            if self.frame0 is not None:
                frame_cut0 = cut_img(self.frame0, 470, 1136, 0, 1080)
                _,_,ID=self.color_mode.match_color(frame_cut0)#返回的有三个值，目前只用ID
                self.count+=1
                self.bus.camera0_img.emit(self.frame0)#发射相机一裁剪后的图片
                self.bus.camera1_img.emit(frame_cut0) #发射相机二元数据
                self.bus.algo_result.emit({"ID": ID, "count": self.count})

                return {"ID": ID, "count": self.count}
        if self.mode=='clip':
            if self.clip_mode is None:
                self.clip_mode=clip_mode()
            if self.frame0 is not None and  self.frame1 is not None:
                
                frame_cut0 = cut_img(self.frame0, 470, 1136, 0, 1080)
                frame_cut1 = cut_img(self.frame1, 470, 1136, 0, 1080)
                vis,_,_,ID =  self.clip_mode.match_clip(frame_cut0,frame_cut1)#返回的有四个值，目前只用ID
                self.count+=1
                '''这里应该返回，还没有结束'''
                self.bus.camera0_img.emit(vis)#发射相机一裁剪后的图片
                self.bus.camera1_img.emit(self.frame1) #发射相机二元数据
                self.bus.algo_result.emit({"ID": ID, "count": self.count})

                return {"ID": ID, "count": self.count}
        if self.mode=='hhit':
            if self.hhit_mode is None:
                self.hhit_mode=hhit_mode()
            if self.hhit_signal is None:
                print("[警告] 未接收到高光谱信息，无法执行后续操作")
                return
            ID,_=self.hhit_mode.match_hhit(self.hhit_signal)
            self.count+=1
            self.bus.hhit_data.emit(self.hhit_signal)  #发送hhit信号
            self.bus.algo_result.emit({"ID": ID, "count": self.count})
            return {"ID": ID, "count": self.count}

            



# def test_changemode_slot():

#     import sys
#     from pathlib import Path  
#     root = Path(__file__).resolve().parent.parent
#     sys.path.insert(0, str(root))


#     from communicator.manager import Manager
#     com_manager = Manager()
#     print("当前模式:", com_manager.mode)
    
#     u1=Updater(com_manager)

#     # ✅ 手动触发信号
#     print("触发 mode_changed 信号，传入 'color'")
#     u1.bus.mode_changed.emit("YOLO")
    
#     u1.bus.worker.emit([[1,3],[2],[],[],[]])




# if __name__ == "__main__":
#     test_changemode_slot()
if __name__ == "__main__":

    from communicator.manager import Manager
    com_manager = Manager()
    #com_manager.setmode("color")

    u1=Updater(com_manager)
    u1.setmode("yolo")
 
 
    
