import torch
from PIL import Image
import open_clip
from typing import Union, Tuple


class ImageClassifier:
    def __init__(self, model_name='ViT-SO400M-16-SigLIP2-512', pretrained='webli', text_labels=None):
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
        self.model = self.model.to(self.device)

        # 获取分词器
        self.tokenizer = open_clip.get_tokenizer(model_name)

        if text_labels is None:
            raise ValueError("请提供 text_labels，即你要识别的文本类别列表，例如 ['T-shirt', 'dress']。")
        self.text_labels = text_labels
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


# ======================
# 🔍 使用示例（传入 PIL 图片，而不是路径）
# ======================

if __name__ == "__main__":
    import time
    t = time.time()
    import cv2
    # 定义你想要识别的类别
    MY_TEXT_LABELS = [
        "T-shirt", "black clothing", "winter clothing", "summer clothing",
        "plush toy", "down jacket", "wallet", "sweater", "leggings",
        "underwear", "shoe", "dress"
    ]

    # 创建分类器
    classifier = ImageClassifier(
        model_name='ViT-SO400M-16-SigLIP2-512',
        pretrained='webli',
        text_labels=MY_TEXT_LABELS
    )

    image = cv2.imread(r"C:\Users\14676\Desktop\shoe\2025-09-03-14-46-50.png")

    # 假定是 OpenCV 格式：numpy 数组，BGR，shape (H, W, 3)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"OpenCV 图像应该是 HWC 格式、3通道的 NumPy 数组，但得到的是 {image.shape}")
    # BGR 转 RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # 转为 PIL.Image
    pil_image = Image.fromarray(image_rgb)

    # 直接传入 PIL.Image 对象进行预测
    try:
        label, confidence = classifier.predict(pil_image)
        print(f"🖼️ 预测结果：'{label}'，置信度：{confidence:.2f}%")
    except Exception as e:
        print(f"❌ 预测失败：{e}")
    print(time.time()-t)