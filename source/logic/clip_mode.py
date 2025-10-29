import clip
import configparser

class CaseSensitiveConfigParser(configparser.ConfigParser):
    """继承ConfigParser，覆盖optionxform方法以保持选项名原样"""
    def optionxform(self, optionstr: str) -> str:
        return optionstr  # 不将选项名转换为小写
    
def load_clip_label_mapping(config_path=r'config\config.ini'):
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