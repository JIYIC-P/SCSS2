import cv2
import numpy as np
import configparser
import sys
from PIL import Image
from typing import List, Tuple, Optional,Dict
import torch
import open_clip

import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from common.config_manager import ConfigManager


MY_TEXT_LABELS = [
        "T-shirt", "black clothing", "winter clothing", "summer clothing",
        "plush toy", "down jacket", "wallet", "sweater", "leggings",
        "underwear", "shoe", "dress"
    ]



class CaseSensitiveConfigParser(configparser.ConfigParser):
    """继承ConfigParser，覆盖optionxform方法以保持选项名原样"""
    def optionxform(self, optionstr: str) -> str:
        return optionstr  # 不将选项名转换为小写
    

class clipClass:
    def __init__(self, model_name='ViT-SO400M-16-SigLIP2-512', pretrained='webli',data=None):
        """
        初始化分类器，加载模型、分词器、预处理和文本标签。

        Args:
            model_name (str): 模型名称，如 'ViT-SO400M-16-SigLIP2-512'
            pretrained (str): 预训练权重，如 'webli'
            text_labels (list[str]): 文本标签列表，如 ["T-shirt", "dress", ...]
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 使用设备: {self.device}")

        # 加载模型和预处理
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
        self.model.eval()
        self.cfg=ConfigManager()
        self.model = self.model.to(self.device)
        if data is not None:
            self.label_mapping = data
        else:
            self.label_mapping=self.cfg.get("clip_mode","labels")
       
        # 获取分词器
        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.text_labels= [it for it in self.label_mapping]

        self.text_tokens = self.tokenizer(self.text_labels).to(self.device)  # tokenize 并移至设备

    def predict(self, image: Image.Image) -> Tuple[str, float]:
        """
        对一张 PIL.Image 图片对象进行预测，返回最可能的文本标签及置信度（百分比）。

        Args:
            image (PIL.Image.Image): 输入的图片，必须是 PIL.Image 对象，且最好是 RGB 模式

        Returns:
            Tuple[str, float]: (预测的文本标签, 置信度百分比)，例如 ("T-shirt", 95.67)
        """
        if not isinstance(image, Image.Image):
            raise TypeError(f"输入必须是 PIL.Image 对象，但传入的是 {type(image)}")

        # 确保图片是 RGB（如果是 RGBA 或 L 等格式，可能会报错）
        if image.mode != 'RGB':
            image = image.convert('RGB')

        try:
            # 预处理图片
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)  # [1, 3, H, W]

            # 模型推理
            with torch.no_grad(), torch.autocast(device_type="cuda" if self.device == "cuda" else "cpu"):
                image_features = self.model.encode_image(image_tensor)
                text_features = self.model.encode_text(self.text_tokens)

                # 归一化 -> 余弦相似度 -> softmax 概率
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)

                text_probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)

            probs = text_probs[0].cpu().numpy()
            predicted_idx = probs.argmax()
            predicted_label = self.text_labels[predicted_idx]
            confidence = float(probs[predicted_idx])*100  # 如 95.67

            return predicted_label, confidence

        except Exception as e:
            raise RuntimeError(f"图片推理过程中出错：{e}")

    def match_clip(self,frame0: np.ndarray,frame1:np.ndarray) -> Tuple[np.ndarray, str, float, int]:
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


        vis = cv2.cvtColor(frame0, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(vis)

        label, conf = self.predict(pil_image)   # 返回 (str, float)
        label_id = self.label_mapping.get(label, -1)       # 找不到给 -1
        return vis, label, conf, label_id


if __name__ == "__main__":
    import sys
    data={
            "T-shirt": 0,
            "black clothing": 1,
            "winter clothing": 2,
            "summer clothing": 3,
            "plush toy": 4,
            "down jacket": 5,
            "wallet": 6,
            "sweater": 7,
            "leggings": 8,
            "underwear": 9,
            "shoe": 10,
            "dress": 11
        }
    classifier = clipClass()
    img_path = r"C:\Users\14676\Desktop\new_env\shoe\imgs\2025-10-16-13-43-33.png"
    frame = cv2.imread(img_path)
    frame0 = frame.copy()
    if frame is None:
        print("图片没读进来，请检查路径或文件是否损坏")
        sys.exit()
    
    print("图片尺寸:", frame.shape[:2])

    vis, label, conf, label_id = classifier.match_clip(frame0,frame)
    print(f"CLIP 预测 -> label={label}  conf={conf:.3f}  id={label_id}")

    cv2.namedWindow("clip_result", cv2.WINDOW_NORMAL)
    cv2.imshow("clip_result", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    print("按任意键关闭窗口...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
# if __name__ == "__main__":
#     label = load_clip_label_mapping()
#     print(label)
#     text = []
#     for it in label :

#         text.append(it)
#     print(text)

