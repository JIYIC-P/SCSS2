#基于python3.6版本
#北京飞扬助力电子技术有限公司 www.fyying.com
#----------------------

# from ctypes import *#引入ctypes库
# import time#使用延时函数
# def test():
#     #下面两种调用DLL函数的方式都可以
#     #dll=WinDLL("C:\Windows\System32\FY5400.dll")
#     dll=windll.LoadLibrary(r"source\Lib\FY5400.dll")

#     hDev=dll.FY5400_OpenDevice(0)#获得句柄
#     print("句柄值是" + str(hDev))
#     print("程序开始运行")

#     t = 0.01
#     count=0
#     while(count<1000):#循环1000次

#         dll.FY5400_DO(hDev,0xffff)#输出通道全部置高
#         time.sleep(t)
#         print(t)
#         dll.FY5400_DO(hDev,0x0000)#输出通道全部置低
#         time.sleep(t)



import time
import threading
from ctypes import windll

# 1. 载入DLL（路径保持与用户示例一致）
dll = windll.LoadLibrary(r"source\Lib\FY5400.dll")


class FY5400IO:
    """
    16位并行IO卡线程安全封装
    提供：
        start()/stop()  —— 后台读线程启停
        get_di()        —— 主线程随时拿到最新DI值
        set_do(value)   —— 主线程立即更新DO输出
        close()         —— 释放设备
    """

    def __init__(self, board_idx: int = 0):
        """
        FUNC: 打开设备，初始化缓存
        I:param board_idx: 板卡编号，默认0
        O:无
        """
        self.hDev = dll.FY5400_OpenDevice(board_idx)
        if not self.hDev:
            raise RuntimeError("FY5400_OpenDevice 失败，请检查驱动/硬件连接")

        # 线程相关
        self._running = threading.Event()   # 用作退出标志
        self._lock = threading.Lock()       # 保护共享缓存
        self._di_cache = 0                  # 最新DI采样值
        self._do_cache = 0                  # 当前DO输出值
        self._thd = None                    # 后台线程对象

        # 初始化DO为全0
        self.set_do(0)

        self.send_sig = False
        self.order = 0xffff

    # ---------------- 对外接口 ----------------
    def start(self, interval: float = 0.01):
        """
        FUNC:启动后台读线程，循环采样DI
        I:param interval: 采样周期，秒
        O:无
        """
        if self._running.is_set():
            return
        self._running.set()
        self._thd = threading.Thread(
            target=self._worker,
            args=(interval,),
            daemon=True
        )
        self._thd.start()

    def stop(self):
        """停止后台读线程"""
        if self._running.is_set():
            self._running.clear()
            self._thd.join()
            self._thd = None

    def get_di(self) -> int:
        """
        FUNC:线程安全读取最近一次DI值
        I:无
        O: 16位DI数据
        """
        with self._lock:
            return hex(self._di_cache)#返回16进制数

    def set_do(self, value: int):
        """
        FUNC:线程安全写入16位DO
        I:param value: 0~0xFFFF,十六进制数
        O:无
        """
        value &= 0xFFFF
        with self._lock:
            if value != self._do_cache:          # 减少无意义写
                dll.FY5400_DO(self.hDev, value) 
                print(value) # 真正写硬件,写入十进制int
                self._do_cache = value           # 更新缓存

    def close(self):
        """关闭设备，释放资源"""
        self.stop()                       # 先停线程
        dll.FY5400_CloseDevice(self.hDev)

    # ---------------- 内部实现 ----------------
    def _worker(self, interval: float):
        """
        FUNC:后台线程函数：循环读DI
        I:param interval: 采样周期，秒
        O:无
        """
        while self._running.is_set():
            with self._lock:
                di = dll.FY5400_DI(self.hDev)      # 读硬件
                self._di_cache = di              # 更新缓存
                if self.send_sig :
                    pass#发self.order
            time.sleep(interval)


# ---------------- 简单测试 ----------------
if __name__ == "__main__":
    io = FY5400IO()          # 打开板卡
    io.set_do(0x0000)
    try:
        # for i in range(1):  # 跑1秒
        #     di = io.get_di()
        #     print(f"DI=0x{di:04X}  {di:016b}")
        #     time.sleep(0.1)

        time.sleep(3)
        while True:
            io.set_do(0x0001)
            time.sleep(0.5)
            io.set_do(0x8000)
            time.sleep(0.5)

    finally:
        io.set_do(0)  # 输出清零
        io.close()    # 释放设备