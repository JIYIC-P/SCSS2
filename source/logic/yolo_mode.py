import sys
import cv2
import numpy as np

from ultralytics import YOLO

import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from common.config_manager import ConfigManager

# MODEL = r"source\config\best_epoch400_mAP50-0.8509.pt"
img_path = r"C:\Users\14676\Desktop\happy-1281590_1280.jpg"

# TODO:目前只有了一张图片进行判断，后续补充第二张的处理逻辑和合并判断
class yoloClass:
    def __init__(self,data=None):
        if data is None:
            self.cfg=ConfigManager()
            self.path=str(self.cfg.get("yolo_mode","path","pt"))
        else:
            self.path=data
    def match_shape(self,frame0: np.ndarray,frame1:np.ndarray):
        """
        IN
        OUT
        FUNC
        """
        
        model = YOLO(self.path)
        img_yolo = model(frame0, verbose=False)
        class_id = -2
        confidence = 0.0
        for result in img_yolo:
        # 获取检测到的类别、置信度、边界框
            for box in result.boxes:
                class_id = int(box.cls)  # 类别ID
                class_name = model.names[class_id]  # 类别名称（如 'person', 'car'）
                confidence = float(box.conf)  # 置信度（0~1）
                x1, y1, x2, y2 = box.xyxy[0].tolist()  # 边界框坐标（左上、右下）
                #print(f"检测到: {class_name}, 可信度: {confidence:.2f}, 位置: {x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}")                  
                # 可以在这里做进一步处理，比如筛选高置信度的目标
        frame = img_yolo[0].plot()  
        return  frame,class_id,confidence



# ====================== 新增：单张图片测试 ======================
if __name__ == "__main__":
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    from communicator.camera import ThreadedCamera
    import time
    camera = ThreadedCamera(0)
    camera.init_camera()
    camera1 = ThreadedCamera(1)
    camera1.init_camera()
    t = time.time()
    t1 = time.time()
  
    test1=yoloClass()
    while t1 - t < 10:
        t1 = time.time()

        frame = camera.grab_frame()
        frame1 =camera1.grab_frame()

        if frame is not None and frame1 is not None:
            cv2.imshow("color_result", frame)
            cv2.imshow("color_", frame1)
            frame,class_id,confidence =test1.match_shape(frame,frame1)
            print(f"HSV 均值 -> {confidence}")
            print(f"匹配结果 -> id={class_id}")
            
        if cv2.waitKey(1) & 0xFF == ord('q'):
            camera.close_cam()
            break