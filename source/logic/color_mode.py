import cv2
import numpy as np
import json
import sys
import pathlib

from typing import List, Tuple, Optional

import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from common.config_manager import ConfigManager

# ========== 参数区（与主程序保持一致） ==========

class colorClass:

    def __init__(self,data=None):
        #self.data = data
        self.cfg=ConfigManager()
        
        if data is not None:
            self.data = data
        else:
            self.data=self.cfg.get("color_mode","ranges")
    # ========== 工具函数（直接搬自原 Dialog.py） ==========
    def load_color_range(self) -> List[Tuple[List[int], List[int]]]:
        """返回 5 组 ([H_low,S_low,V_low], [H_high,S_high,V_high])"""
        ranges_str = self.data
        print(self.data)
        raw = {int(k): v for k, v in ranges_str.items()}
        print (raw)
        result = []
        for i in range(5):
            base = raw[i][0]
            offset = raw[i][1]
            lower = [max(0, x - offset) for x in base]
            upper = [x + offset for x in base]
            result.append((lower, upper))
        return result


    def hsv_in_range(self,average: List[float],
                    lower: List[int],
                    upper: List[int]) -> bool:
        I = 0
        if len(average) > 0:
            if lower[0] <= average[0] <= upper[0]:
                I += 1
            if lower[1] <= average[1] <= upper[1]:
                I += 1
            if lower[2] <= average[2] <= upper[2]:
                I += 1
            if I > 2:
                return True
        return False


<<<<<<< HEAD


def load_color_range() -> List[Tuple[List[int], List[int]]]:
    """返回 5 组 ([H_low,S_low,V_low], [H_high,S_high,V_high])"""
    with open(get_path(), 'r', encoding='utf-8') as file:
        data = json.load(file)
    ranges_str = data['COLOR_RANGES']['ranges']
    raw = {int(k): v for k, v in ranges_str.items()}
    print (raw)
    result = []
    for i in range(5):
        base = raw[i][0]
        offset = raw[i][1]
        lower = [max(0, x - offset) for x in base]
        upper = [x + offset for x in base]
        result.append((lower, upper))
    return result
=======
    def detect_color_by_hsv(self,hsv_list: List[float],
                            ranges: List[Tuple[List[int], List[int]]]) -> Optional[int]:
        """返回 1~5 表示匹配到的颜色编号，无匹配返回 None"""
        for idx, (lower, upper) in enumerate(ranges):
            if self.hsv_in_range(hsv_list, lower, upper):
                return idx + 1
        return None
>>>>>>> 88bd4e0fe0984b9f080a06d22c29693e02415564


    def segment_one(self,img_in: np.ndarray) -> List[float]:
        """计算整张图 HSV 均值，与原 Dialog.segment_one 逻辑一致"""
        hsv = cv2.cvtColor(img_in, cv2.COLOR_RGB2HSV)
        avg = hsv.reshape(-1, 3).mean(axis=0).tolist()  # [H,S,V]
        return avg


    # ========== 对外接口：单张图颜色检测 ==========
    def match_color(self,frame: np.ndarray,
                    ranges: List[Tuple[List[int], List[int]]] = None) -> Tuple[np.ndarray, List[float], Optional[int]]:
        """
        :param frame: BGR 图
        :param ranges: 外部可复用缓存，传 None 则内部自动加载
        :return:
            vis      : 原图（RGB）
            hsv_avg  : [H,S,V] 均值
            color_id : 1~5 或 None
        """
        if ranges is None:
            ranges = self.load_color_range()

        vis = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hsv_avg = self.segment_one(vis)
        
        color_id =self.detect_color_by_hsv(hsv_avg, ranges)
        return vis, hsv_avg, color_id


# ====================== 单张图片测试 =======================
if __name__ == "__main__":
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    from communicator.camera import ThreadedCamera
    import time
    camera = ThreadedCamera(0)
    camera.init_camera()
    t = time.time()
    t1 = time.time()
    with open(r"C:\Users\14676\Desktop\SCSS2\settings\default_config.json", 'r', encoding='utf-8') as file:
        data = json.load(file)
    test1=colorClass()
    while t1 - t < 10:
        t1 = time.time()

        frame = camera.grab_frame()

        if frame is not None:
            vis, hsv_avg, color_id =test1.match_color(frame)
            print(f"HSV 均值 -> {hsv_avg}")
            print(f"匹配结果 -> color_id={color_id}")
            cv2.imshow("color_result", vis)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            camera.close_cam()
            break