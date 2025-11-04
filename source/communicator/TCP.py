import ctypes
from ctypes import *
import threading
from numpy.ctypeslib import as_array

MAX_ARRY_LENGTH=6#最大数值长度
class ClassifierReceiver:
    """
    现有
    此类用于接受来自其它tcp客户端的数据，数据格式为640*(float),numpy
    要求启动线程，与结束线程的接口，获取数据的方法
    此类接收一个回调函数，当接受到数据后触发
    
    要求
    让其专注于通信，也即每一帧回调后仅作统计，并更新统计后的数据，
    提供一个方法用于获取当前帧的统计结果，数据类型要求为整数列表
    """
    #def __init__(self, on_transform_data: Optional[Callable[[list], None]] = None):
    def __init__(self):
    
        # DLL 路径，需替换为你实际的 DLL 所在路径
        self.dll_path = r'source\Lib\ClassifyResultReceiver.dll'

        # 统计相关
        self.count_frame = 0
        self.count = None # 分别统计值为 1~5 的个数
        self.float_array_np=None#新加变量--qi
        self.PASS_SIZE = 600  # 值为5的个数阈值，超过则重置

        # 加载 DLL
        self.receiver_lib = ctypes.WinDLL(self.dll_path)

        # 定义回调函数类型
        self.HHITClasifyResultCallbackType = CFUNCTYPE(None, c_void_p, c_uint)
        self.HHITClasifyResultErrCallbackType = CFUNCTYPE(None, c_char_p)

        # 回调函数对象
        self.receive_callback = None
        self.error_callback = None

        # 用户自定义回调（可选）
        #self.on_transform_data = on_transform_data  # type: Optional[Callable[[np.ndarray], None]]

        # 绑定 DLL 函数
        self._bind_functions()

        # 运行状态
        self.is_running = False

    def _bind_functions(self):
        # init 函数
        self.init_func = self.receiver_lib.init
        self.init_func.argtypes = [
            c_char_p,            # pServerIp
            c_int,               # nPort
            self.HHITClasifyResultCallbackType,  # clasifyResultCallback
            self.HHITClasifyResultErrCallbackType, # errCallback
            c_int                # nRcvBufSize
        ]
        self.init_func.restype = c_bool

        # uninit 函数
        self.uninit_func = self.receiver_lib.uninit
        self.uninit_func.argtypes = []
        self.uninit_func.restype = c_bool

    def _on_receive_data(self, p_frame, size):
        """
        回调函数，由 DLL 数据到达时触发
        """
        
        if self.count_frame%5==0:
 
            if size % 4 != 0:
                print(f"[警告] 数据大小 {size} 不是 4 的倍数，可能不是 float 数组！")
                return
            float_count = size // 4
            self.count_frame += 1
            if self.count_frame == 640:
                self.count_frame = 0

            FloatPtr = POINTER(c_float)
            float_ptr = cast(p_frame, FloatPtr)
            self.float_array_np = as_array(float_ptr, shape=(float_count,))  # 零拷贝视图
            #values, counts = np.unique(arr.round(decimals), return_counts=True)
            # 构造长度为5的统计结果

            '''以下是原始代码'''
            # int_array = np.round(float_array_np).astype(np.uint8)
            # self.count = list(np.bincount(int_array, MAX_ARRY_LENGTH=6))



            # # --- 调用用户自定义回调（如果提供了）---
            # if self.on_transform_data is not None:
            #     #values, counts = np.unique(float_array_np.round(0), return_counts=True)
            #     #self.on_transform_data(float_array_np)  # 传入 numpy 数组 和 原始数据大小
            #     self.on_transform_data(stat)
    def _on_error(self, err_msg):
        err_str = err_msg.decode('utf-8', errors='ignore')
        print(f"[回调 错误] 接收线程出错: {err_str}")

    def start(self, server_ip, port, rcv_buf_size=1000):
        if self.is_running:
            print("[警告] 接收器已经在运行中！")
            return False

        # 创建回调函数对象
        self.receive_callback = self.HHITClasifyResultCallbackType(self._on_receive_data)
        self.error_callback = self.HHITClasifyResultErrCallbackType(self._on_error)

        # 准备 IP 参数
        server_ip_bytes = server_ip.encode('utf-8') if isinstance(server_ip, str) else server_ip
        if isinstance(server_ip_bytes, str):  # 冗余判断，确保一定是 bytes
            server_ip_bytes = server_ip_bytes.encode('utf-8')

        # 调用 DLL 初始化
        success = self.init_func(
            server_ip_bytes,  # pServerIp
            port,             # nPort
            self.receive_callback,  # clasifyResultCallback
            self.error_callback,    # errCallback
            rcv_buf_size      # nRcvBufSize
        )

        if success:
            self.is_running = True
            print("[Python] ✅ 接收器启动成功，开始接收数据...")
            # 启动一个线程保持程序活跃，以接收回调
            self._keep_alive_thread = threading.Thread(target=self._keep_alive, daemon=True)
            self._keep_alive_thread.start()
            return True
        else:
            print("[Python] ❌ 接收器启动失败！")
            return False

    def stop(self):
        if not self.is_running:
            print("[警告] 接收器未在运行。")
            return False

        success = self.uninit_func()
        if success:
            self.is_running = False
            print("[Python] ✅ 接收器已停止。")
            return True
        else:
            print("[Python] ❌ 接收器停止失败。")
            return False

    def _keep_alive(self):
        """保持主线程存活，以接收回调（否则主线程退出后回调将失效）"""
        try:
            print("[Python] 🟢 接收器运行中，按 Ctrl+C 停止...")
            while self.is_running:
                pass
        except KeyboardInterrupt:
            print("\n[Python] 用户中断，正在停止接收器...")
            self.stop()


# =============================
# ✅ 示例：用户使用代码（可单独运行测试）
# =============================

# if __name__ == "__main__":
#     # --- 示例：用户自定义回调 ---

#     MAX_SIZE = 640
#     RATE = 0.9
#     PASS_SIZE = MAX_SIZE * RATE
#     count = [0,0,0,0]
#     def my_on_transform_data(float_array: np.ndarray):
#         count[4] = int(np.sum(float_array == 5))
#         if count[4] > PASS_SIZE:
#             count = [0, 0, 0, 0, PASS_SIZE]  # 重置，保留 count[4] 为 PASS_SIZE
#             return  # 超过阈值，不继续统计

#         count[0] = int(np.sum(float_array == 1))
#         count[1] = int(np.sum(float_array == 2))
#         count[2] = int(np.sum(float_array == 3))
#         count[3] = int(np.sum(float_array == 4))
#         print(count)

#     # --- 创建接收器实例，并传入自定义回调 ---
#     receiver = ClassifierReceiver(on_transform_data=my_on_transform_data)

#     # --- 启动接收器 ---
#     if receiver.start(server_ip="192.168.1.16", port=5555, rcv_buf_size=1000):
#         try:
#             # 主线程保持运行，或者你可以做其他事情
#             import time
#             while receiver.is_running:
#                 pass  # 或者 time.sleep(1)
#         except KeyboardInterrupt:
#             print("\n[主程序] 用户按下 Ctrl+C，停止中...")
#         finally:
#             receiver.stop()