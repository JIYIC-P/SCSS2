# hhit_match.py
import os
import configparser
from typing import Dict, List, Tuple, Optional
import numpy as np

# ========== 参数区 ==========
INI_PATH = r"config\config.ini"          # 含 [HHIT_LABELS] 字段
DEFAULT_LABELS = [f"class_{i}" for i in range(7)]  # 7 类前景
PASS_SIZE = 640 * 0.9                    # 与主程序保持一致

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


# ========== 多帧累积逻辑 ==========
_accum_buffer: List[List[int]] = []      # 累积队列
_in_session = False                      # 是否处于有效序列中


def _reset():
    """清空缓存与状态"""
    global _accum_buffer, _in_session
    _accum_buffer.clear()
    _in_session = False


def match_hhit(hhit_single_frame: List[int],
               label_mapping: Optional[Dict[str, int]] = None) -> Tuple[Optional[int], str]:
    """
    逐帧喂数据，内部自动完成“开始-累积-结束-返回”全流程。
    :param hhit_single_frame: 9 通道计数列表（前 7 前景，第 8 背景，末位保留）
    :param label_mapping:     外部可复用缓存，传 None 则内部自动加载
    :return: (label_id, label_name)
             仅在“序列结束”时返回有效结果，其余时刻返回 (None, "")
    """
    global _accum_buffer, _in_session

    if label_mapping is None:
        label_mapping = load_hhit_label()

    # 合法性检查
    if len(hhit_single_frame) != 9:
        print(f"[WARN] 输入帧长度不是 9，当前长度：{len(hhit_single_frame)}")
        _reset()
        return None, ""

    is_all_zero = np.all(np.array(hhit_single_frame) == 0)

    # 阶段 1：等待开始
    if not _in_session:
        if is_all_zero:
            return None, ""
        else:
            _in_session = True
            _accum_buffer.append(hhit_single_frame)
            return None, ""

    # 阶段 2：累积中
    if not is_all_zero:
        _accum_buffer.append(hhit_single_frame)
        return None, ""

    # 阶段 3：遇到全零 → 结束并给出结果
    if not _accum_buffer:
        _reset()
        return None, ""

    # 对位相加
    summed = np.sum(np.array(_accum_buffer), axis=0).tolist()

    # 背景判断（倒数第二通道）
    if summed[-2] > PASS_SIZE:
        _reset()
        return None, ""

    # 前景找最大
    temp = summed[:7]
    max_val = max(temp)
    if max_val == 0:
        _reset()
        return None, ""

    first_max_index = int(np.argmax(temp))
    label_name = list(label_mapping.keys())[first_max_index]
    label_id = label_mapping[label_name]

    _reset()          # 清空等待下一次
    return label_id, label_name


# ====================== 简易测试 =======================
if __name__ == "__main__":
    seq = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0],   # 无效
        [3, 0, 15, 0, 0, 0, 0, 720, 0],  # 开始
        [2, 0, 10, 0, 0, 0, 0, 500, 0],  # 累积
        [0, 0, 0, 0, 0, 0, 0, 0, 0],   # 结束
    ]
    for frm in seq:
        lid, lname = match_hhit(frm)
        if lid is not None:
            print("序列结束 -> id:", lid, "name:", lname)