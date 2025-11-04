# color_match.py
import cv2
import numpy as np
import configparser
import json
import sys
from typing import List, Tuple, Optional

# ========== 参数区（与主程序保持一致） ==========
INI_PATH = r"Lib\config.ini"      # 含 [COLOR_RANGES] 字段
MAX_SIZE = 640
RATE = 0.9
PASS_SIZE = MAX_SIZE * RATE                 # 如需阈值可复用

"""
color_mode中颜色范围的保存不是我写的，是小辈写得


"""
# ========== 工具函数（直接搬自原 Dialog.py） ==========
def load_color_range(ini_path: str = INI_PATH) -> List[Tuple[List[int], List[int]]]:
    """返回 5 组 ([H_low,S_low,V_low], [H_high,S_high,V_high])"""
    cfg = configparser.ConfigParser()
    cfg.read(ini_path, encoding='utf-8')
    ranges_str = cfg['COLOR_RANGES']['ranges']
    raw = json.loads(ranges_str)            # dict[str,list]
    raw = {int(k): v for k, v in raw.items()}
    return [raw[i] for i in range(5)]       # 顺序 0~4


def hsv_in_range(average: List[float],
                 lower: List[int],
                 upper: List[int]) -> bool:
    """原封不动摘自原代码"""
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


def detect_color_by_hsv(hsv_list: List[float],
                        ranges: List[Tuple[List[int], List[int]]]) -> Optional[int]:
    """返回 1~5 表示匹配到的颜色编号，无匹配返回 None"""
    for idx, (lower, upper) in enumerate(ranges):
        if hsv_in_range(hsv_list, lower, upper):
            return idx + 1
    return None


def segment_one(img_in: np.ndarray) -> List[float]:
    """计算整张图 HSV 均值，与原 Dialog.segment_one 逻辑一致"""
    hsv = cv2.cvtColor(img_in, cv2.COLOR_RGB2HSV)
    avg = hsv.reshape(-1, 3).mean(axis=0).tolist()  # [H,S,V]
    return avg


# ========== 对外接口：单张图颜色检测 ==========
def match_color(frame: np.ndarray,
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
        ranges = load_color_range()

    vis = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hsv_avg = segment_one(vis)
    color_id = detect_color_by_hsv(hsv_avg, ranges)
    return vis, hsv_avg, color_id


# ====================== 单张图片测试 =======================
if __name__ == "__main__":
    img_path = r"C:\Users\14676\Desktop\new_env\bag\imgs\2025-10-16-14-09-54.png"
    frame = cv2.imread(img_path)
    if frame is None:
        print("图片没读进来，请检查路径或文件是否损坏")
        sys.exit()

    print("图片尺寸:", frame.shape[:2])
    vis, hsv_avg, color_id = match_color(frame)
    print(f"HSV 均值 -> {hsv_avg}")
    print(f"匹配结果 -> color_id={color_id}")

    cv2.namedWindow("color_result", cv2.WINDOW_NORMAL)
    cv2.imshow("color_result", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    print("按任意键关闭窗口...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()