# hhit_match.py
import sys, pathlib, configparser, numpy as np
from typing import Dict, List, Tuple, Optional

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from communicator.tcp import ClassifierReceiver          # 若无需 TCP 可注释

INI_PATH = r'Lib\config.ini'
VALID_RATIO = 0.20          # 80 % 通道有标签才算有效帧

# ---------- 读取标签 ----------
class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr

def load_HHIT_label(config_path: str = INI_PATH) -> Dict[str, int]:
    cfg = CaseSensitiveConfigParser()
    cfg.read(config_path, encoding='utf-8')
    if 'HHIT_LABELS' not in cfg:
        print("[警告] 未找到 [HHIT_LABELS] 配置，无法加载 HHIT 标签与ID映射")
        return {}
    section = cfg['HHIT_LABELS']
    return {label: int(v.strip()) for label, v in section.items()}

# ---------- 统一的小数→整数 ----------
def __float_to_int(arr: np.ndarray) -> np.ndarray:
    """先 clip 再四舍五入，最后 uint8，保证 0-6"""
    clipped = np.clip(arr, 0.0, 20.0)
    return np.round(clipped).astype(np.uint8)

# ---------- 640→7 维统计 ----------
def statistics_data(float_array: np.ndarray) -> List[int]:
    try:
        int_array = __float_to_int(float_array)
        counts = np.bincount(int_array, minlength=7)
        return counts.tolist()
    except Exception as e:
        print(f"统计数据出错（数组形状：{float_array.shape}）：{e}")
        return [0] * 7

# ---------- 空/有效帧判定 ----------
def _is_valid_frame(arr640: np.ndarray, label_map: Dict[str, int]) -> bool:
    int_arr = __float_to_int(arr640)
    valid_mask = (int_arr >= 0) & (int_arr <= 6)
    valid_vals = int_arr[valid_mask]
    # print(valid_vals.size)
    # 只要值在 0~6 就视为合法，无需再查表
    ratio = valid_vals.size / 640.0
    # print(ratio)
    return ratio >= VALID_RATIO

# ---------- 累积状态 ----------
_accum_buf: List[List[int]] = []
_in_sess = False
_label_map = load_HHIT_label()          # 全局复用

def _reset() -> None:
    global _accum_buf, _in_sess
    _accum_buf.clear()
    _in_sess = False

# ---------- 对外接口 ----------
def match_hhit(arr640: np.ndarray) -> Tuple[Optional[int], str]:
    """
    主流程：640→有效判断→统计→累加→给标签
    """
    global _accum_buf, _in_sess

    valid = _is_valid_frame(arr640, _label_map)
    # print(valid)
    cnt7 = statistics_data(arr640) if valid else None
    # print(cnt7)

    if not _in_sess:                      # 阶段1：等待开始
        if not valid:
            return None, ""
        _in_sess = True
        _accum_buf.append(cnt7)
        return None, ""

    if valid:                             # 阶段2：累积中
        _accum_buf.append(cnt7)
        return None, ""

    # 阶段3：遇到无效帧 → 结算
    if not _accum_buf:
        _reset()
        return None, ""

    summed = np.sum(_accum_buf, axis=0, dtype=int)
    max_idx = int(np.argmax(summed))
    reverse_map = {v: k for k, v in _label_map.items()}
    label_name = reverse_map.get(max_idx, '其它')
    _reset()
    return max_idx, label_name

# ====================== 自测 =======================
if __name__ == "__main__":
    import random

    def fake_640(empty: bool = False) -> np.ndarray:
        if empty:
            return np.full(640, 9.0, np.float32)
        mask = np.random.rand(640) < 0.2
        arr = np.where(mask, 3,
                       np.random.randint(1, 20, size=640)) \
              + np.random.rand(640) * 0.3
        return arr.astype(np.float32)

    def run_fake(seq_len: int = 30) -> None:
        for _ in range(seq_len):
            arr640 = fake_640(empty=(random.random() < 0.3))
            # print(arr640)
            lid, lname = match_hhit(arr640)
            print(lid, lname)

        # ✅ 强制用无效帧收尾，触发结算
        lid, lname = match_hhit(fake_640(empty=True))
        if lid is not None:
            print(f"[序列结束] id={lid}  name={lname}")
    print("标签映射:", {v: k for k, v in _label_map.items()})
    print("-" * 50)
    for g in range(3):
        print(f"\n========== 第 {g+1} 组 ==========")
        run_fake()