
import time
import sys
#from Ui_main_form import Ui_Dialog 
import cv2
import numpy as np
import configparser
import json
import os
from datetime import datetime
import yaml
from ultralytics import YOLO

MODEL = "config/best_epoch400_mAP50-0.8509.pt"
img_path = r"C:\Users\14676\Desktop\happy-1281590_1280.jpg"

class shape_mode:
    def __init__(self):
        """初始化：加载模型"""
        self.model = YOLO(MODEL)       # 原来缺失的 model 属性
    #     self.yolo_classes = {}   
    # def read_yolo_classes(self,yaml_path = r"config/data.yaml"):
    #     """
    #     从YOLO的YAML配置文件中读取类别名称和对应编号
    #     参数:
    #         yaml_path (str): YOLO配置文件的路径
            
    #     返回:
    #         dict: 包含类别编号和名称的字典，格式为 {编号: 类别名称}
    #     """
    #     with open(yaml_path, 'r') as file:
    #         data = yaml.safe_load(file)
        
    #     if 'names' in data:
    #         #print(data)
    #         if isinstance(data['names'], list):
    #             self.yolo_classes = {}  # 显式创建一个空字典
    #             for idx, name in enumerate(data['names']):
    #                 self.yolo_classes[idx] = name  # 逐个添加键值对
    #         try :
    #             allboxes = self._get_all_comboboxes()
    #             for combox in allboxes:

    #                 for i,cls in enumerate(self.yolo_classes.values()):
    #                     #print(i,cls)
    #                     if i>=5:
    #                         self.add_combox_Item(i+1)
    #                     combox.setItemText(i+1,cls)
    #         except Exception as e:
    #             print(e)

    def match_shape(self,frame):
        img_yolo = self.model(frame, verbose=False)
        class_id = -2
        confidence = 0.0
        for result in img_yolo:
        # 获取检测到的类别、置信度、边界框
            for box in result.boxes:
                class_id = int(box.cls)  # 类别ID
                class_name = self.model.names[class_id]  # 类别名称（如 'person', 'car'）
                confidence = float(box.conf)  # 置信度（0~1）
                x1, y1, x2, y2 = box.xyxy[0].tolist()  # 边界框坐标（左上、右下）
                #print(f"检测到: {class_name}, 可信度: {confidence:.2f}, 位置: {x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}")                  
                # 可以在这里做进一步处理，比如筛选高置信度的目标
        frame = img_yolo[0].plot()  
        return  frame,[class_id,confidence]
    

# ====================== 新增：单张图片测试 ======================
if __name__ == "__main__":

    detector = shape_mode()
    frame = cv2.imread(img_path)
    if frame is None:                       # ---- 关键检查 ----
        print("图片没读进来，请检查路径或文件是否损坏")
        sys.exit()

    print("图片尺寸:", frame.shape[:2])
    vis, (cls, conf) = detector.match_shape(frame)
    print(f"检测结果 -> class_id={cls}, confidence={conf:.3f}")

    cv2.namedWindow("result", cv2.WINDOW_NORMAL)  # 确保窗口在前台
    cv2.imshow("result", vis)
    print("按任意键关闭窗口...")
    cv2.waitKey(0)                            # 阻塞直到按键
    cv2.destroyAllWindows()