import cv2
from threading import Thread
import time

class ThreadedCamera:
    def __init__(self, source=0):
        # 相机相关变量
        self.cap = None
        self.camera_opened = False
        self.current_frame = None
        self.source = source
        self._running = True  # 控制线程运行的标志

        # 相机参数
        self.fps = 50
        self.exposure = -6
        self.resolution = [1920, 1080]
        self.brightness = 100
        self.contrast = 50

    def init_camera(self):
        """初始化相机"""
        try:
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)  # Windows使用DirectShow
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
        """应用相机设置"""
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
        """更新视频帧"""
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
                    self.current_frame = frame.copy()
            else:
                print("读取帧失败，尝试重新初始化相机...")
                self.camera_opened = False
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                time.sleep(0.1)

    def grab_frame(self):
        """获取当前帧（线程安全）返回图像格式为BGR"""

        if self.current_frame is not None:
            return self.current_frame.copy()
        return None

    def close_cam(self):
        """关闭并释放资源"""
        self._running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0) 
        if self.camera_opened and self.cap is not None:
            self.cap.release()
        self.camera_opened = False
        self.cap = None


    def open_cam(self):
        """打开相机"""
        if self.cap is None:
            print("尝试打开相机...")
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                raise Exception("无法打开相机")
            self.camera_opened = True


    def list_camera_properties(self):
        """列出摄像头支持的属性（调试用）"""
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
            # 你原来代码里重复了，这里去重，但保留一次即可
            # ("CAP_PROP_WHITE_BALANCE_RED_U", cv2.CAP_PROP_WHITE_BALANCE_RED_U),
            # ("CAP_PROP_WHITE_BALANCE_BLUE_V", cv2.CAP_PROP_WHITE_BALANCE_BLUE_V),
        ]

        print("\n--- 开始列出摄像头支持的属性 ---")
        for name, prop_id in props:
            try:
                value = self.cap.get(prop_id)
                print(f"{name:30} (ID:{prop_id}): {value}")
            except Exception as e:
                print(f"{name:30} (ID:{prop_id}): 不支持或无法读取 ({e})")
        print("--- 摄像头属性列表结束 ---\n")

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