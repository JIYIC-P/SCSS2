# hhit_match.py
import sys, pathlib, configparser, numpy as np
from typing import Dict, List, Tuple, Optional

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from common.config_manager import ConfigManager

from communicator.tcp import ClassifierReceiver          # 若无需 TCP 可注释

INI_PATH = r'Lib\config.ini'
VALID_RATIO = 0.20          # 80 % 通道有标签才算有效帧


class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr

class hhitClass:
    def __init__(self,data=None):
        self.accum_buf: List[List[int]] = []
        self.in_sess = False
        self.cfg=ConfigManager()
        if data is not None:
            self.label_map = data
        else:
            self.label_map=self.cfg.get("hhit_mode","labels")
# ---------- 统一的小数→整数 ----------
    def float_to_int(self,arr: np.ndarray) -> np.ndarray:
        """先 clip 再四舍五入，最后 uint8，保证 0-6"""
        clipped = np.clip(arr, 0.0, 20.0)
        return np.round(clipped).astype(np.uint8)

    # ---------- 640→7 维统计 ----------
    def statistics_data(self,float_array: np.ndarray) -> List[int]:
        try:
            int_array = self.float_to_int(float_array)
            counts = np.bincount(int_array, minlength=7)
            return counts.tolist()
        except Exception as e:
            print(f"统计数据出错（数组形状：{float_array.shape}）：{e}")
            return [0] * 7

    # ---------- 空/有效帧判定 ----------
    def is_valid_frame(self,arr640: np.ndarray, label_map: Dict[str, int]) -> bool:
        int_arr = self.float_to_int(arr640)
        valid_mask = (int_arr >= 0) & (int_arr <= 6)
        valid_vals = int_arr[valid_mask]
        # print(valid_vals.size)
        # 只要值在 0~6 就视为合法，无需再查表
        ratio = valid_vals.size / 640.0
        # print(ratio)
        return ratio >= VALID_RATIO

      # 全局复用

    def reset(self) -> None:
        
        self.accum_buf.clear()
        self.in_sess = False

    # ---------- 对外接口 ----------
    def match_hhit(self,arr640: np.ndarray) -> Tuple[Optional[int], str]:
        """
        主流程：640→有效判断→统计→累加→给标签
        """
    

        valid = self.is_valid_frame(arr640, self.label_map)
        # print(valid)
        cnt7 = self.statistics_data(arr640) if valid else None
        # print(cnt7)

        if not self.in_sess:                      # 阶段1：等待开始
            if not valid:
                return None, ""
            self.in_sess = True
            self.accum_buf.append(cnt7)
            return None, ""

        if valid:                             # 阶段2：累积中
            self.accum_buf.append(cnt7)
            return None, ""

        # 阶段3：遇到无效帧 → 结算
        if not self.accum_buf:
            self.reset()
            return None, ""

        summed = np.sum(self.accum_buf, axis=0, dtype=int)
        max_idx = int(np.argmax(summed))
        reverse_map = {v: k for k, v in self.label_map.items()}
        label_name = reverse_map.get(max_idx, '其它')
        self.reset()
        return max_idx, label_name

# ====================== 自测 =======================
if __name__ == "__main__":
    import random
    test1=hhitClass()

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
            lid, lname = test1.match_hhit(arr640)
            print(lid, lname)

        # ✅ 强制用无效帧收尾，触发结算
        lid, lname = test1.match_hhit(fake_640(empty=True))
        if lid is not None:
            print(f"[序列结束] id={lid}  name={lname}")
    print("标签映射:", {v: k for k, v in test1.label_map.items()})
    print("-" * 50)
    for g in range(3):
        print(f"\n========== 第 {g+1} 组 ==========")
        run_fake()