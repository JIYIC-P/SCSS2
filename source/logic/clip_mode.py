import cv2
import numpy as np
import configparser
import json
import sys
import clip
from PIL import Image
from typing import List, Tuple, Optional,Dict

MY_TEXT_LABELS = [
        "T-shirt", "black clothing", "winter clothing", "summer clothing",
        "plush toy", "down jacket", "wallet", "sweater", "leggings",
        "underwear", "shoe", "dress"
    ]

class CaseSensitiveConfigParser(configparser.ConfigParser):
    """继承ConfigParser，覆盖optionxform方法以保持选项名原样"""
    def optionxform(self, optionstr: str) -> str:
        return optionstr  # 不将选项名转换为小写
    
def load_clip_label_mapping(config_path=r'Lib\config.ini'):
    cfg = CaseSensitiveConfigParser()
    cfg.read(config_path, encoding='utf-8')
    if 'CLIP_LABELS' not in cfg:
        print("[警告] 未找到 [CLIP_LABELS] 配置，无法加载 CLIP 标签与ID映射")
        return {}
    clip_section = cfg['CLIP_LABELS']
    clip_label_to_id = {}
    for label_text, id_str in clip_section.items():
        try:
            clip_label_to_id[label_text] = int(id_str.strip())  # 保持label_text原大小写
        except ValueError:
            print(f"[警告] CLIP 标签 '{label_text}' 的 ID 不是有效数字: {id_str}")
    print("[INFO] 已加载 CLIP 标签与 ID 映射：")
    return clip_label_to_id

classifier = clip.ImageClassifier(
    model_name='ViT-SO400M-16-SigLIP2-512',
    pretrained='webli',
    text_labels=MY_TEXT_LABELS)

def match_clip(frame0: np.ndarray,frame1:np.ndarray,
               classifier,
               label_mapping: Optional[Dict[str, int]] = None) -> Tuple[np.ndarray, str, float, int]:
    """
    单张 BGR 图 -> CLIP 分类结果
    :param frame:        BGR 图
    :param classifier:   你自己的 ClipClassifier 实例
    :param label_mapping:外部可复用缓存，传 None 则内部自动加载
    :return:
        vis      : RGB 图
        label    : 最佳标签
        conf     : 置信度
        label_id : 对应 ID
    """
    #TODO :补充两张图片的逻辑
    if label_mapping is None:
        label_mapping = load_clip_label_mapping()

    vis = cv2.cvtColor(frame0, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(vis)

    label, conf = classifier.predict(pil_image)   # 返回 (str, float)
    label_id = label_mapping.get(label, -1)       # 找不到给 -1
    return vis, label, conf, label_id


if __name__ == "__main__":
    import sys

    img_path = r"C:\Users\14676\Desktop\new_env\shoe\imgs\2025-10-16-13-43-33.png"
    frame = cv2.imread(img_path)
    if frame is None:
        print("图片没读进来，请检查路径或文件是否损坏")
        sys.exit()

    print("图片尺寸:", frame.shape[:2])

    vis, label, conf, label_id = match_clip(frame, classifier)
    print(f"CLIP 预测 -> label={label}  conf={conf:.3f}  id={label_id}")

    cv2.namedWindow("clip_result", cv2.WINDOW_NORMAL)
    cv2.imshow("clip_result", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    print("按任意键关闭窗口...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
