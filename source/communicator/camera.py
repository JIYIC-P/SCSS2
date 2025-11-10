import cv2
from threading import Thread
import time


import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from common.config_manager import ConfigManager
class ThreadedCamera:
    """
    相机类，提供相机线程用于抓取图片和设置相机参数
    提供线程启停接口和拷贝图片的函数。
    拷贝图片格式为BGR
    """
    def __init__(self, source=0):
        """
        I: source - 相机设备索引/视频路径（默认0表示默认摄像头）
        O: 无
        FUNC: 初始化相机实例，设置基础参数和状态变量
        """
        # 相机相关变量
        self.cap = None
        self.camera_opened = False
        self.current_frame = None
        self.source = source
        self._running = True  # 控制线程运行的标志


      
        data = ConfigManager()
        # 相机参数
        self.fps = data.get("camera","config","fps")
        self.exposure = data.get("camera","config","exposure")
        self.resolution = data.get("camera","config","resolution")
        self.brightness = data.get("camera","config","brightness")
        self.contrast = data.get("camera","config","contrast")

        

    def init_camera(self):
        """
        I: 无显式输入（依赖类实例已初始化的source等参数）
        O: 无显式输出（通过camera_opened状态标识初始化结果）
        FUNC: 执行相机核心初始化流程：
              1. 创建VideoCapture对象并验证是否成功打开
              2. 标记相机已打开状态
              3. 应用预设相机参数
              4. 启动独立线程持续更新视频帧
        """
        try:
            
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_MSMF)  # Windows使用DirectShow
            if not self.cap.isOpened():
                raise Exception("无法打开相机")
            
            self.camera_opened = True
            self.set_camera()
            # 启动帧更新线程
            self.thread = Thread(target=self.update, daemon=True)
            self.thread.start()

        except Exception as e:
            print(f"相机初始化失败: {e}")
            self.camera_opened = False
            self._running = False

    def set_camera(self):
        """
        I: 无显式输入（依赖类实例已设置的参数属性）
        O: 无显式输出（通过cap.set()返回值隐式反馈设置结果）
        FUNC: 将类内预设的相机参数应用到实际相机设备：
              包括分辨率、帧率、曝光、亮度、对比度等基础参数，
              额外关闭自动白平衡、自动对焦和增益以获得稳定画面
        """
        if not self.camera_opened:
            return

        print("应用相机设置")
        
        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        # 设置帧率
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        # 设置曝光
        self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure)
        # 设置其他参数
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
        self.cap.set(cv2.CAP_PROP_CONTRAST, self.contrast)
        # 关闭自动白平衡
        self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)          # 0 = OFF
        # 关闭自动增益（部分相机把增益和曝光耦合在一起，也一起关掉）
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)        # 顺带关自动对焦，防止跑焦
        self.cap.set(cv2.CAP_PROP_GAIN, 0)             # 手动增益设为固定值

        print(f"分辨率: {self.resolution}, FPS: {self.fps}, 曝光: {self.exposure}, "
              f"亮度: {self.brightness}, 对比度: {self.contrast}")

    def update(self):
        """
        I: 无显式输入（依赖_running标志和camera_opened状态）
        O: 无显式输出（通过修改current_frame更新最新帧）
        FUNC: 线程主循环函数，持续执行以下操作：
              1. 检查相机连接状态，异常时尝试重新初始化
              2. 读取最新视频帧并缓存到current_frame
              3. 处理读取失败情况（释放资源并尝试重连）
              
        """
       
        while self._running:
            if self.cap is None or not self.camera_opened:
                try:
                    self.open_cam()
                    self.set_camera()
                    self.camera_opened = True
                except Exception as e:
                    print(f"打开相机失败: {e}")
                    time.sleep(0.1)
                    continue
            
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
            else:
                print("读取帧失败，尝试重新初始化相机...")
                self.camera_opened = False
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                time.sleep(0.1)

    def grab_frame(self):
        """
        I: 无显式输入
        O: current_frame的深拷贝（BGR格式）或None（无有效帧时）
        FUNC: 线程安全地获取当前最新视频帧：
              通过返回拷贝避免多线程下的数据竞争问题，
              保证外部使用帧数据时不影响内部帧更新
        """
        if self.current_frame is not None:
            return self.current_frame
        return None

    def close_cam(self):
        """
        I: 无显式输入
        O: 无显式输出（通过释放资源和修改状态标记完成关闭）
        FUNC: 安全关闭相机并释放所有相关资源：
              1. 设置_running标志终止更新线程
              2. 等待线程安全退出（join）
              3. 释放VideoCapture对象
              4. 重置相机状态标记
        """
        self._running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0) 
        if self.camera_opened and self.cap is not None:
            self.cap.release()
        self.camera_opened = False
        self.cap = None


    def open_cam(self):
        """
        I: 无显式输入
        O: 无显式输出（通过修改camera_opened状态标记反馈结果）
        FUNC: 尝试重新打开相机设备：
              仅在cap对象未初始化或已释放时调用，
              成功打开后标记camera_opened为True
        """
        if self.cap is None:
            print("尝试打开相机...")
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                raise Exception("无法打开相机")
            self.camera_opened = True


    def list_camera_properties(self):
        """
        I: 无显式输入（依赖已打开的cap对象）
        O: 无显式输出（直接打印相机支持的属性列表）
        FUNC: 调试辅助函数，遍历常见相机属性并打印其当前值：
              帮助开发者了解相机支持的可配置参数及其当前状态，
              包含分辨率、帧率、曝光、白平衡等关键参数
        """
        props = [
            ("CAP_PROP_POS_MSEC", cv2.CAP_PROP_POS_MSEC),
            ("CAP_PROP_POS_FRAMES", cv2.CAP_PROP_POS_FRAMES),
            ("CAP_PROP_POS_AVI_RATIO", cv2.CAP_PROP_POS_AVI_RATIO),
            ("CAP_PROP_FRAME_WIDTH", cv2.CAP_PROP_FRAME_WIDTH),
            ("CAP_PROP_FRAME_HEIGHT", cv2.CAP_PROP_FRAME_HEIGHT),
            ("CAP_PROP_FPS", cv2.CAP_PROP_FPS),
            ("CAP_PROP_FOURCC", cv2.CAP_PROP_FOURCC),
            ("CAP_PROP_FRAME_COUNT", cv2.CAP_PROP_FRAME_COUNT),
            ("CAP_PROP_FORMAT", cv2.CAP_PROP_FORMAT),
            ("CAP_PROP_MODE", cv2.CAP_PROP_MODE),
            ("CAP_PROP_BRIGHTNESS", cv2.CAP_PROP_BRIGHTNESS),
            ("CAP_PROP_CONTRAST", cv2.CAP_PROP_CONTRAST),
            ("CAP_PROP_SATURATION", cv2.CAP_PROP_SATURATION),
            ("CAP_PROP_HUE", cv2.CAP_PROP_HUE),
            ("CAP_PROP_GAIN", cv2.CAP_PROP_GAIN),
            ("CAP_PROP_EXPOSURE", cv2.CAP_PROP_EXPOSURE),
            ("CAP_PROP_CONVERT_RGB", cv2.CAP_PROP_CONVERT_RGB),
            ("CAP_PROP_WHITE_BALANCE_BLUE_U", cv2.CAP_PROP_WHITE_BALANCE_BLUE_U),
            ("CAP_PROP_WHITE_BALANCE_RED_V", cv2.CAP_PROP_WHITE_BALANCE_RED_V),
            ("CAP_PROP_AUTO_WB", cv2.CAP_PROP_AUTO_WB),
            ("CAP_PROP_GAMMA", cv2.CAP_PROP_GAMMA),
            ("CAP_PROP_TEMPERATURE", cv2.CAP_PROP_TEMPERATURE),  # 某些工业相机支持
            ("CAP_PROP_TRIGGER", cv2.CAP_PROP_TRIGGER),
            ("CAP_PROP_TRIGGER_DELAY", cv2.CAP_PROP_TRIGGER_DELAY),
        ]

        print("--- 开始列出摄像头支持的属性 ---")
        for name, prop_id in props:
            try:
                value = self.cap.get(prop_id)
                print(f"{name:30} (ID:{prop_id}): {value}")
            except Exception as e:
                print(f"{name:30} (ID:{prop_id}): 不支持或无法读取 ({e})")
        print("--- 摄像头属性列表结束 ---")


# 使用示例
if __name__ == '__main__':
    camera = ThreadedCamera(0)
    camera.init_camera()
    camera.list_camera_properties()
    try:
        while True:
            frame = camera.grab_frame()
            if frame is not None:
                cv2.imshow("Camera Feed", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.close_cam()
        cv2.destroyAllWindows()