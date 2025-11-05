import json
import threading
import pathlib

class ConfigManager:
    _lock = threading.RLock()

    def __init__(self):
        with self._lock:
            self._user_file = pathlib.Path(__file__).parent.parent.parent / r"settings/user_config.json"  # 用户配置信息
            self._default_file = pathlib.Path(__file__).parent.parent.parent / r"settings\default_config.json"  # 默认配置信息
            self._cfg = json.loads(self._default_file.read_text(encoding='utf-8'))

    def get(self, key1=None,key2=None, default=None):
        with self._lock:
            if  self._user_file.exists():
                self._cfg=json.loads(self._user_file.read_text(encoding='utf-8'))
                return self._cfg[key1][key2]
            else:
                self._cfg=json.loads(self._default_file.read_text(encoding='utf-8'))
                return self._cfg[key1]

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
    print(cfg.get("hhit_mode","labels"))
