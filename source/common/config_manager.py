import json
import threading
import pathlib

class ConfigManager:
    _lock = threading.RLock()

    def __init__(self):
        with self._lock:
            self._user_file = pathlib.Path(__file__).parent.parent.parent / r"settings/user_config.json"  # 用户配置信息
            self._default_file = pathlib.Path(__file__).parent.parent.parent / r"settings\default_config.json"  # 默认配置信息
            if self._user_file.exists():
                self._cfg = json.loads(self._user_file.read_text(encoding='utf-8'))
            else:
                self._cfg = json.loads(self._default_file.read_text(encoding='utf-8'))

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

    def set(self, key1, key2,key3, value):
        with self._lock:
            # 如果用户配置文件不存在，先将默认配置完全复制过来
            if not self._user_file.exists():
                self._user_file.parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在
                self._user_file.write_text(json.dumps(self._cfg, indent=2), encoding='utf-8')
            # 加载用户配置文件
            self._cfg = json.loads(self._user_file.read_text(encoding='utf-8'))
            
            # 修改配置
            # if communicator not in self._cfg:
            #     self._cfg[communicator] = {}
            self._cfg[key1][key2][key3] = value
            # 保存修改后的配置
            self._user_file.write_text(json.dumps(self._cfg, indent=2), encoding='utf-8')

if __name__ == '__main__':
    cfg = ConfigManager()
    cfg.set("camera", "config","fps", 50)
    print(cfg.get("hhit_mode"))
