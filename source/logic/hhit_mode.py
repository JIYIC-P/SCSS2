# hhit_match.py
import os
import configparser
from typing import Dict, List, Tuple, Optional
import numpy as np

# ========== 参数区 ==========
INI_PATH = r"config\config.ini"          # 含 [HHIT_LABELS] 字段
DEFAULT_LABELS = [f"class_{i}" for i in range(7)]  # 7 类前景
PASS_SIZE = 640 * 0.9                    # 与主程序保持一致
ZERO_RATIO_THRESHOLD = 0.20              # 20 % 以上为零视为“空帧”

# ========== 工具函数 ==========
class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def load_hhit_label(ini_path: str = INI_PATH) -> Dict[str, int]:
    cfg = CaseSensitiveConfigParser()
    cfg.read(ini_path, encoding='utf-8')
    if 'HHIT_LABELS' not in cfg:
        print("[警告] 未找到 [HHIT_LABELS] 配置，使用默认 7 类映射")
        return {lbl: idx for idx, lbl in enumerate(DEFAULT_LABELS)}
    section = cfg['HHIT_LABELS']
    mapping = {}
    for lbl, id_str in section.items():
        try:
            mapping[lbl] = int(id_str.strip())
        except ValueError:
            print(f"[警告] HHIT 标签 '{lbl}' 的 ID 不是有效数字: {id_str}")
    print("[INFO] 已加载 HHIT 标签与 ID 映射：", mapping)
    return mapping


# --------- 空帧判定 ---------
def _is_empty_frame(frame: List[int]) -> bool:
    """零占比 ≥ 阈值 视为空帧"""
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
            [0, 0, 5, 0, 0, 0, 0, 300, 0],
            [0, 0, 8, 0, 0, 0, 0, 400, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
        # 序列 2：class_0 赢（含少量噪声）
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [4, 1, 2, 0, 0, 0, 0, 200, 0],
            [6, 0, 1, 0, 0, 0, 0, 180, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
        # 序列 3：背景通道过大 → 应返回 None
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [1, 0, 2, 0, 0, 0, 0, 800, 0],  # 背景超限
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
            [0, 0, 0, 0, 0, 0, 7, 100, 0],
            [0, 0, 0, 0, 0, 0, 9, 110, 0],
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
                print("帧:", frm, "→ 结果:", end=" ")
                if lid is None:
                    print("None")
                else:
                    print(f"id={lid}  name={lname}")
            print("-" * 30)