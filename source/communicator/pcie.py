import asyncio
import time
import threading
from ctypes import windll
from typing import Dict, List, Optional

import sys
from pathlib import Path  
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from common.data_bus import DataBus


# 1. 载入DLL（路径保持与用户示例一致）
dll = windll.LoadLibrary(r"Lib\FY5400.dll")


class PcIeIO:
    """
    16位并行IO卡线程安全封装（无锁版）
    提供：
        start()/stop()  —— 后台读线程启停
        get_di()        —— 主线程随时拿到最新DI值
        set_do(value)   —— 主线程立即更新DO输出
        close()         —— 释放设备
    """
    def __init__(self, board_idx: int = 0):
        print("init")
        self.hDev = dll.FY5400_OpenDevice(board_idx)
        if not self.hDev:
            raise RuntimeError("FY5400_OpenDevice 失败")

        # 线程相关
        self._running = True
        self._di_cache = 0
        self._do_cache = 0
        self._thd = None

        # 消抖相关
        self._di_prve = 0
        self._last_tm = [0.] * 16
        self.debounce = 0.02

        # 核心1：为每个ID创建独立的协程锁（非线程锁！）
        self._id_locks: Dict[int, asyncio.Lock] = {i: asyncio.Lock() for i in range(16)}
        
        # 核心2：事件循环引用
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.start_event_loop()
        self.set_do(0)

        # Databus
        self.bus = DataBus()

    def status_judg(self, di: int) -> List[int]:
        """
        返回长度 16 的 list
        -1  下降沿
         0  无变化 / 保持
         1  上升沿
        已消抖
        """
        now = time.time()
        out = [0] * 16
        changed = (di ^ self._di_prve) & 0xFFFF  # 检查全部16位
        
        if not changed:
            return out

        for bit in range(16):
            mask = 1 << bit
            if not (changed & mask):
                continue

            # 正式记录这次变化
            self._last_tm[bit] = now
            if (di & mask) and not (self._di_prve & mask):
                out[bit] = 1  # 上升沿
                self.bus.add_status_up.emit(bit)
                # print(f"DI=0x{di:04X} status={out}")  # 调试时可打开
            elif not (di & mask) and (self._di_prve & mask):
                out[bit] = -1  # 下降沿
                self.bus.add_status_down.emit(bit)
                # print(f"DI=0x{di:04X} status={out}")  # 调试时可打开
        self._di_prve = di

    # ---------------- 对外接口 ----------------
    def start(self, interval: float = 0.1):
        """
        FUNC:启动后台读线程，循环采样DI
        I:param interval: 采样周期，秒
        O:无
        """
        
        if self._thd and self._thd.is_alive():
            return  # 已经运行中
        
        self._running = True
        self._thd = threading.Thread(
            target=self._worker,
            args=(interval,),
            daemon=True
        )
        self._thd.start()


    def stop(self):
        """停止后台读线程"""
        print("stop")
        if self._running:
            self._running = False
            if self._thd:
                self._thd.join()
                self._thd = None

    def get_di(self) -> int:
        """
        FUNC:读取最近一次DI值（无锁，直接返回）
        I:无
        O: 16位DI数据
        """
        return int(self._di_cache)

    async def push(self, ID: Optional[int], delay: float):
        """同一ID串行，不同ID并行"""
        if ID is None:
            return
        
        lock = self._id_locks[ID]
        
        async with lock:  # 协程级锁，不阻塞线程
            await asyncio.sleep(delay)
            dll.FY5400_DO_Bit(self.hDev, 1, ID)
            await asyncio.sleep(1)
            dll.FY5400_DO_Bit(self.hDev, 0, ID)

    def submit_push(self, ID: Optional[int], delay: float):
        """
        从同步代码（主循环）原子化提交push任务
        - 非阻塞，立即返回
        - 同一ID自动排队
        - 可在while循环内任意位置调用
        """
        if self._loop is None:
            raise RuntimeError("事件循环未启动，请先调用start_event_loop()")
        
        # 将协程提交到事件循环，不等待完成
        asyncio.run_coroutine_threadsafe(self.push(ID, delay), self._loop)

    def start_event_loop(self):
        """在后台线程启动永久事件循环（仅调用一次）"""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._event_thread = threading.Thread(target=run_loop, daemon=True)
        self._event_thread.start()
        
        # 等待循环启动完成
        while self._loop is None:
            time.sleep(0.001)


    def set_do(self, value: int):
        """
        FUNC:写入16位DO（无锁，直接操作）
        I:param value: 0~0xFFFF
        O:无
        """
        value &= 0xFFFF
        # 减少无意义写
        if value != self._do_cache:
            dll.FY5400_DO(self.hDev, value)
            self._do_cache = value

    def close(self):
        """关闭设备，释放资源"""
        self.stop()
        dll.FY5400_CloseDevice(self.hDev)

    # ---------------- 内部实现 ----------------
    def _worker(self, interval=0.03):
        """后台采样线程"""
        while self._running:
            # 直接读取并更新缓存（原子操作）
            di = dll.FY5400_DI(self.hDev)
            self._di_cache = di
            self.status_judg(di)  # 计算状态变化
            time.sleep(interval)


# ---------------- 简单测试 ----------------
if __name__ == "__main__":
    io = PcIeIO()          # 打开板卡
    io.set_do(0x0000)
    io.start(0.01)         # 启动后台读取
    
    try:
        time.sleep(0.01)
        while True:
            # 读取DI和状态变化（无锁，直接访问）
            di = io.get_di()
            #print(f"DI=0x{di:04X}  {di:016b} | status={status}")
            
            # 交替输出测试
            io.submit_push(0,2)
            io.submit_push(1,2)
            time.sleep(3)

    finally:
        io.set_do(0)  # 输出清零
        io.close()    # 释放设备