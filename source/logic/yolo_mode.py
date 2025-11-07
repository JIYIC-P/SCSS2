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
            self.path=self.cfg.get("yolo_mode","path","pt")
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

    frame = cv2.imread(img_path)
    frame1=frame
    if frame is None:                       # ---- 关键检查 ----
        print("图片没读进来，请检查路径或文件是否损坏")
        sys.exit()

    print("图片尺寸:", frame.shape[:2])
    test1=yoloClass()
    vis, cls, conf = test1.match_shape(frame,frame1)
    print(f"检测结果 -> class_id={cls}, confidence={conf:.3f}")

    cv2.namedWindow("result", cv2.WINDOW_NORMAL)  # 确保窗口在前台
    cv2.imshow("result", vis)
    print("按任意键关闭窗口...")
    cv2.waitKey(0)                            # 阻塞直到按键
    cv2.destroyAllWindows()