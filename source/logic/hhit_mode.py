# hhit_match.py
import os
import configparser
from typing import Dict, List, Tuple, Optional
import numpy as np
import time
from communicator.TCP import ClassifierReceiver 


# ========== 参数区 ==========

INI_PATH = r'source\config\config.ini'          # 含 [HHIT_LABELS] 字段
PASS_SIZE = 640                     # 与主程序保持一致
ZERO_RATIO_THRESHOLD = 0.9        # 90 % 以上为零视为“空帧”

# ========== 工具函数 ==========
class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform( optionstr: str) -> str:
        return optionstr

def statistics_data(float_array: np.ndarray):
    """
    优化后的统计数据函数：解决浮点转整数错误，保持高频率性能
    - 输入：float_array 是 np.ndarray，元素为浮点数（如传感器输出的计数，理论应为整数但含噪声）
    - 功能：统计0-5的值的次数（对应minlength=6）
    """
    try:
        # 1. 范围裁剪：将浮点数限制在[0,5]，避免负数或过大值
        # 注：若原始数据本应在0-5之间，此步过滤噪声/异常值
        clipped_float = np.clip(float_array, a_min=0.0, a_max=7.0)
        
        # 2. 准确转整数：用np.round替代astype(int)，避免截断误差
        # 注：np.uint8是最小的无符号整数类型，节省内存且速度快
        int_array = np.round(clipped_float).astype(np.uint8)
        
        # 3. 快速统计：np.bincount向量化操作，minlength=6确保输出长度为6
        counts = np.bincount(int_array, minlength=6)
        
        # 后续处理（保持原逻辑）
        HHIT_single_frame = counts.tolist()  
        # count += 1
        # if count == 10:
        #     count = 0
        #     print("近10次统计结果：", HHIT_single_frame)
            
    except Exception as e:
        # 异常捕获：避免单次错误导致整个回调崩溃
        print(f"统计数据出错（数组形状：{float_array.shape}）：{str(e)}")
        # 可选：记录日志或返回默认值

receiver = ClassifierReceiver(on_transform_data=statistics_data)

def load_hhit_label(ini_path: str = INI_PATH) -> Dict[str, int]:
    cfg = CaseSensitiveConfigParser()
    cfg.read(ini_path, encoding='utf-8')
    if 'HHIT_LABELS' not in cfg:
        print("[警告] 未找到 [HHIT_LABELS] 配置")
        return 0
    section = cfg['HHIT_LABELS']
    mapping = {}
    for lbl, id_str in section.items():
        try:
            mapping[lbl] = int(id_str.strip())
        except ValueError:
            print(f"[警告] HHIT 标签 '{lbl}' 的 ID 不是有效数字: {id_str}")
    # print("[INFO] 已加载 HHIT 标签与 ID 映射：", mapping)
    return mapping


# --------- 空帧判定 ---------
def _is_empty_frame(frame: List[int]) -> bool:
    """零占比 ≥ 阈值（90%）视为空帧"""
    zero_cnt = sum(1 for v in frame if v == 0)
    return (zero_cnt / len(frame)) >= ZERO_RATIO_THRESHOLD


# --------- 多帧累积状态 ---------
_accum_buffer: List[List[int]] = []
_in_session = False


def _reset():
    global _accum_buffer, _in_session
    _accum_buffer.clear()
    _in_session = False


# ========== 对外接口：逐帧喂数据 ==========
def match_hhit(hhit_single_frame: List[int],
               label_mapping: Optional[Dict[str, int]] = None) -> Tuple[Optional[int], str]:
    """
    逐帧喂数据，内部自动完成“开始-累积-结束-返回”全流程。
    开始/结束条件：零占比 ≥ 20 %
    :param hhit_single_frame: 9 通道计数列表

    :param label_mapping:     外部可复用缓存，传 None 则内部自动加载
    :return: (label_id, label_name)
             仅在“序列结束”时返回有效结果，其余时刻返回 (None, "")
    """
    global _accum_buffer, _in_session

    if label_mapping is None:
        label_mapping = load_hhit_label()


    is_all_zero = np.all(np.array(hhit_single_frame) == 0)

    if len(hhit_single_frame) != 9:
        print(f"[WARN] 输入帧长度不是 9，当前长度：{len(hhit_single_frame)}")
        _reset()
        return None, ""

    empty_flag = _is_empty_frame(hhit_single_frame)


    # 阶段 1：等待开始
    if not _in_session:
        if empty_flag:
            return None, ""
        else:
            _in_session = True
            _accum_buffer.append(hhit_single_frame)
            return None, ""

    # 阶段 2：累积中
    if not empty_flag:
        _accum_buffer.append(hhit_single_frame)
        return None, ""

    # 阶段 3：遇到空帧 → 结束并给出结果
    if not _accum_buffer:
        _reset()
        return None, ""

    summed = np.sum(np.array(_accum_buffer), axis=0).tolist()

    # 背景判断（倒数第二通道）
    if summed[-2] > PASS_SIZE:
        _reset()
        return None, ""

    temp = summed[:7]
    max_val = max(temp)
    if max_val == 0:
        _reset()
        return None, ""

    first_max_index = int(np.argmax(temp))
    label_name = list(label_mapping.keys())[first_max_index]
    label_id = label_mapping[label_name]

    _reset()
    return label_id, label_name


# ====================== 循环多组自测 =======================
if __name__ == "__main__":

    # 测试库：每组是一条完整序列（List[List[int]]）
    test_bank = [
        # 序列 1：class_2 应该赢
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [1, 0, 5, 4, 0, 2, 0, 0, 0],
            [0, 0, 8, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
        # 序列 2：class_0 赢（含少量噪声）
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [4, 1, 2, 0, 0, 0, 0, 0, 0],
            [6, 0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
        # 序列 3：背景通道过大 → 应返回 None
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [1, 0, 0, 0, 5, 0, 0, 0, 0],  # 背景超限
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
        # 序列 4：全零序列 → 应返回 None
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
        # 序列 5：class_6 赢（末类）
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 7, 0, 0],
            [0, 0, 0, 0, 0, 0, 9, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
    ]

    mapping = load_hhit_label()
    print("标签映射:", mapping)
    print("=" * 50)

    rounds = 3                               # 想跑多少轮
    for r in range(rounds):
        print(f"========== 第 {r+1} 轮 ==========")
        for idx, seq in enumerate(test_bank, 1):
            print(f"\n--- 序列 {idx} ---")
            for frm in seq:
                lid, lname = match_hhit(frm, mapping)
               
            print(f"id={lid}  name={lname}")
            print("-" * 30)

