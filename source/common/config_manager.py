"""
要求创建配置管理类，总管前后端所有的配置，写入config.ini
data.yaml是yolo标准格式，也可以将其并入config.ini中方便统一集中管理
"""
import json, threading, pathlib
class ConfigManager:
    _lock = threading.RLock()
    _file = pathlib.Path(__file__).parent.parent / "config.json"
    def __init__(self):
        with self._lock:
            self._cfg = json.loads(self._file.read_text(encoding='utf-8'))

    def get(self, key=None, default=None):
        with self._lock:
            return self._cfg.copy() if key is None else self._cfg.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._cfg[key] = value
        self._file.write_text(json.dumps(self._cfg, indent=2), encoding='utf-8')