# hhit_match.py
import os
import configparser
from typing import Dict, List, Tuple, Optional
import numpy as np

# ========== 参数区 ==========
INI_PATH = r"config\config.ini"          # 含 [HHIT_LABELS] 字段
DEFAULT_LABELS = ["class_0", "class_1", "class_2", "class_3", "class_4"]  # 兜底
PASS_SIZE = 640 * 0.9                    # 与主程序保持一致

# ========== 工具函数 ==========
class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr  # 保持大小写


def load_hhit_label(ini_path: str = INI_PATH) -> Dict[str, int]:
    """
    完全复用你提供的 load_HHIT_label 逻辑
    """
    cfg = CaseSensitiveConfigParser()
    cfg.read(ini_path, encoding='utf-8')
    if 'HHIT_LABELS' not in cfg:
        print("[警告] 未找到 [HHIT_LABELS] 配置，无法加载 HHIT 标签与ID映射")
        return {}
    HHIT_section = cfg['HHIT_LABELS']
    HHIT_label_to_id = {}
    for label_text, id_str in HHIT_section.items():
        try:
            HHIT_label_to_id[label_text] = int(id_str.strip())  # 保持原大小写
        except ValueError:
            print(f"[警告] HHIT 标签 '{label_text}' 的 ID 不是有效数字: {id_str}")
    print("[INFO] 已加载 HHIT 标签与 ID 映射：")
    return HHIT_label_to_id


# ========== 对外接口：单帧 HHIT 分类 ==========
def match_hhit(hhit_single_frame: List[int],
               label_mapping: Optional[Dict[str, int]] = None) -> Tuple[Optional[int], str]:
    """
    :param hhit_single_frame: 一帧 8 通道计数列表（末位为背景）
    :param label_mapping:     外部可复用缓存，传 None 则内部自动加载
    :return: (label_id, label_name)  无有效目标返回 (None, "")
    """
    if label_mapping is None:
        label_mapping = load_hhit_label()

    last = len(hhit_single_frame)
    if last == 0:
        return None, ""

    # 1. 背景判断
    if hhit_single_frame[-1] > PASS_SIZE:
        return None, ""

    # 2. 前景找最大
    temp = hhit_single_frame[:-1]
    max_val = max(temp)
    if max_val == 0:
        return None, ""

    first_max_index = int(np.argmax(temp))          # 0-based
    # 按映射表顺序取对应标签
    label_name = list(label_mapping.keys())[first_max_index]
    label_id = label_mapping[label_name]
    return label_id, label_name


# ====================== 单帧测试 =======================
if __name__ == "__main__":
    # 模拟一帧数据（8 通道，末位为背景）
    fake_frame = [10, 3, 0, 0, 0, 0, 0, 700]
    lid, lname = match_hhit(fake_frame)
    print("模拟帧:", fake_frame)
    print("预测结果 -> id:", lid, "name:", lname)