import sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent      # 找到工程根
sys.path.insert(0, str(root))  


import cv2
import sys
from communicator.manager import *
import shape_mode
import color_mode
import clip_mode
import hhit_mode
'''
工具函数
'''

def cut_img(self,frame,x,width,y,height):
    '''裁剪图片'''
    # OpenCV 的裁剪操作是通过 NumPy 的数组切片实现的
    return frame[y:y + height, x:x + width]


class updater():
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
        """
        self.com_model = communicator
        self.hhit_signal=None
        self.frame0=None
        self.frame1=None
        self.pcie_signal=None
        # pice signal : 0xFFFF--> 0,1,2,3,4,5：目前有效位，这六位转化为上升下降沿信号： 0 ：上升沿 1 ：下降沿 -1 ：保持


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
        if self.com_model.mode in ('clip', 'yolo'): 
            self.frame0 = self.com_model.camera0.grab_frame() #获取相机一的图片信息
            self.frame1 = self.com_model.camera1.grab_frame() #获取相机二的图片信息
        elif self.com_model.mode=='color':
            self.frame0 = self.com_model.camera0.grab_frame() #获取相机一的图片信息
        elif self.com_model.mode=='hhit':
            self.hhit_signal=self.com_model.hhit.float_array_np.copy() #获取原始hhit信息

    def setmode(self,mode):
        self.mode = mode

    def generate_order(self,ID,worker):
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
        return order
    
    def send_order(self,order):
        """
        调用pcie通信对象，发送指令
        """

    def update(self):
        """
        2 . 获取数据（图片，传感器信息，numpy统计结果）
        3 . 四个模式各自的处理方法。 返回物品ID有范围
        4 . 根据id发出指令（根据传感器信息）

        """
        self.get_data()
        ID = self.Judgment()
        ORDER = self.generate_order(ID)
        self.send_order(ORDER)

    def Judgment(self,mode):
        #TODO： match_j待完善
        '''注意只返回ID，最后记得统一返回值类型和数量'''
        if mode=="shape":
            # frame=self.streamer.grab_frame()
            if self.frame0 is None or self.frame1 is None:
                print("[警告] frame0 或 frame1 未初始化，无法执行后续操作")
                return
            frame_cut0 = self.cut_img(self.frame0, 470, 1136, 0, 1080)
            frame_cut1 = self.cut_img(self.frame1, 470, 1136, 0, 1080)
            _, ID, _ = shape_mode.match_shape(frame_cut0,frame_cut1)#返回的有三个值，目前只用ID
            return ID
        if mode=='color':
            # frame=self.streamer.grab_frame()
            if self.frame0 is None:
                print("[警告] frame0，无法执行后续操作")
                return
            frame_cut0 = self.cut_img(self.frame0, 470, 1136, 0, 1080)
            _,_,ID=color_mode.match_color(frame_cut0)#返回的有三个值，目前只用ID
            return ID
        if mode=='clip':
            # frame=self.streamer.grab_frame()
            if self.frame0 is None or self.frame1 is None:
                print("[警告] frame0 或 frame1 未初始化，无法执行后续操作")
                return
            frame_cut0 = self.cut_img(self.frame0, 470, 1136, 0, 1080)
            frame_cut1 = self.cut_img(self.frame1, 470, 1136, 0, 1080)
            _, _, _,ID =  clip_mode.match_clip(frame_cut0,frame_cut1)#返回的有四个值，目前只用ID
            return ID
        if mode=='HHIT':
            if self.hhit_signal is None:
                print("[警告] 未接收到高光谱信息，无法执行后续操作")
                return
            ID,_=hhit_mode.match_hhit(self.hhit_signal)
            return ID

            


if __name__ == "__main__":

    img_path = r"C:\Users\14676\Desktop\new_env\bag\imgs\2025-10-16-14-05-58.png"
    u1=updater(manager('color'))
    frame = cv2.imread(img_path)
    if frame is None:                       # ---- 关键检查 ----
        print("图片没读进来，请检查路径或文件是否损坏")
        sys.exit()

    print("图片尺寸:", frame.shape[:2])
    vis, cls, conf = u1.Judgment('形状')
    print(f"检测结果 -> class_id={cls}, confidence={conf:.3f}")
    # vis, hsv_avg, color_id =u1.Judgment('颜色')
    # print(f"HSV 均值 -> {hsv_avg}")
    # print(f"匹配结果 -> color_id={color_id}")
    # vis, label, conf, label_id = u1.Judgment('clip')
    # print(f"CLIP 预测 -> label={label}  conf={conf:.3f}  id={label_id}")


    cv2.namedWindow("result", cv2.WINDOW_NORMAL)  # 确保窗口在前台
    cv2.imshow("result", vis)
    print("按任意键关闭窗口...")
    cv2.waitKey(0)                            # 阻塞直到按键
    cv2.destroyAllWindows()
    
