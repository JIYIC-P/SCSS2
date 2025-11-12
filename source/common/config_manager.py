import json
import threading
import pathlib

class ConfigManager:
    _lock = threading.RLock()

    def __init__(self):
        with self._lock:
            self._user_file = pathlib.Path(__file__).parent.parent.parent / r"settings//user_config.json"  # 用户配置信息
            self._default_file = pathlib.Path(__file__).parent.parent.parent / r"settings//default_config.json"  # 默认配置信息
            try:

                if self._user_file.exists():
                    self._cfg = json.loads(self._user_file.read_text(encoding='utf-8'))
                else:
                    self._cfg = json.loads(self._default_file.read_text(encoding='utf-8'))
            except Exception as e:
                print(e)

    def get(self, *keys, default=None):
        # 逐层获取值
        try:
            value = self._cfg
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            # KeyError: 某个 key 不存在
            # TypeError: value 不是字典，不能继续用 key 索引（比如 value 是字符串，却还想用 ['a'] 访问）
            return default

    def set(self, *keys, value):
        with self._lock:
            if not self._user_file.exists():
                self._user_file.parent.mkdir(parents=True, exist_ok=True)
                self._user_file.write_text(json.dumps(self._cfg, indent=2), encoding='utf-8')

            cfg = self._cfg
            for key in keys[:-1]:
                if key not in cfg:
                    cfg[key] = {}
                cfg = cfg[key]
            cfg[keys[-1]] = value

            self._user_file.write_text(json.dumps(self._cfg, indent=2), encoding='utf-8')
    def find_key_path(self, nested_dict, target_value, path=()):
        for key, value in nested_dict.items():
            if isinstance(value, dict):  # 如果值是字典，递归查找
                result = self.find_key_path(value, target_value, path + (key,))
                if result:
                    return result  # 返回递归结果
            elif value == target_value:  # 找到目标值
                return key  # 返回当前键
        return None  # 如果没有找到，返回 None
if __name__ == '__main__':
    cfg = ConfigManager()
    cfg.set("color_mode","labels","7",value=[[],6])
  
