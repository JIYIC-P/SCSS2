import serial 
import modbus_tk.defines as fnc
from modbus_tk import modbus_rtu as rtu
import time
import threading


class ModBus():
    """
    此类用于基于串口的modbus通信，该通信方法暂时弃用：
    后续修改请只保留通信部分，只保留读取寄存器和写入线圈两个部分，
    其余指令保留一个通信接口，可以自定义发的数据包内容。
    
    
    要求：
    1.创建线程接口：
    传入串口号，波特率等信息
    该线程每隔一段时间与从机通信
    平时通信要求为：读取寄存器信息并更新变量
    必要时：写入线圈信息。
    2.关闭线程接口：
    释放占用的资源

    """
    def __init__(self, PORT='COM1', BOARD_RATE=38400, TOUT=1):
        """
        Modbus RTU 通信类初始化
        """
        self.PORT = PORT
        self.BOARD_RATE = BOARD_RATE
        self.TOUT = TOUT
        # 通信参数


        self.isopend = False
        self.master = None
        self.end = False
        # 传递信号量

        self.func = 0  
        self.config = []
        self.distance = []
        self.values = [0,0,0,0,0]    
        self.t1 = [time.time() for _ in range(5)]
        #电机运动参数


        self.ADR_IN = 0
        self.NUM_IN = 6
        self.ADR_COIL = 0
        self.NUM_COIL = 5
        # 受控设备


        self.pre_reg = [0]*6
        self.cur_reg = [0]*6
        self.trig_status = [0]*6
        self.count_trig_u = [0]*6
        self.coils = [0]*5
        # input寄存器状态和线圈状态
        

        self.sender = threading.Thread(target=self.beating)
        self.beating_interval = 0.07
        # 发指令线程
        # 默认心跳间隔

        self.lock = threading.Lock()


    # def send_to_2(self,i,ADR):
    #     try:       
    #         int_value = int(i) #原精度为三位小数，受控端会将整数转化为小数
    #         # 2. 拆分高低16位
    #         high_word1 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
    #         low_word1 = int_value & 0xFFFF
    #         print(f"i {i},ADR {ADR},high_word1 {high_word1},low_word1 {low_word1}")
    #         

    #             self.master.execute(
    #                 2,
    #                 fnc.WRITE_MULTIPLE_REGISTERS,
    #                 starting_address= ADR,
    #                 quantity_of_x = 2,
    #                 output_value=[low_word1,high_word1]
    #             )
    #     except Exception as e:
    #         print(f": {e}")



    def open(self):
        """打开Modbus RTU串口连接"""
        if self.isopend:
            raise Exception(f'端口已经打开: {self.PORT}')
        # 创建Modbus RTU主站
        self.master = rtu.RtuMaster(
            serial.Serial(
                port=self.PORT,
                baudrate=self.BOARD_RATE,
                parity='N',
                stopbits=1,
                timeout=0.5
            )
        )
        self.master.set_timeout(self.TOUT)
        self.master.set_verbose(False)  # 启/停用详细日志
        self.isopend = True
        print(f"打开端口: {self.isopend}, {self.PORT}, {self.BOARD_RATE}, {self.TOUT}")



    def set_speed(self):    
        """
        此函数修改电机控制板正反转速度
        """
        for s in self.config:
            int_value = int(s[1]) #原精度为三位小数，受控端会将整数转化为小数
            # 2. 拆分高低16位
            high_word1 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
            low_word1 = int_value & 0xFFFF

            int_value = int(s[2])  
            high_word2 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
            low_word2 = int_value & 0xFFFF
            print(s[0],s[1],s[2],"\n")
            print(f"id\t{s[0]-1},\nhigh_word1\t{high_word1},\nlow_word1\t{low_word1},\nhigh_word2\t{high_word2},\nlow_word2\t{low_word2}")
            try:
                self.master.execute(
                    slave= s[0],
                    function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                    starting_address = 404,
                    quantity_of_x = 2,
                    output_value=[low_word1,high_word1]
                )
                time.sleep(0.1)
                self.master.execute(
                    slave= s[0],
                    function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                    starting_address = 408,
                    quantity_of_x = 2,
                    output_value=[low_word2,high_word2]
                )
                time.sleep(0.1)
            except Exception as e:
                print(f"设置速度错误: sid{s[0]}{e}")



    def set_distance(self):    
        """
        此函数修改电机控制板正反转速度
        """
        for s in self.config:

            int_value = int(s[3]*1000)  # 100.000 → 100000
            # 2. 拆分高低16位
            high_word1 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
            low_word1 = int_value & 0xFFFF
            print(f"id\t{s[0]-1},\nhigh_word1\t{high_word1},\nlow_word1\t{low_word1}")
            try:
                

                    self.master.execute(
                        slave= s[0],
                        function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                        starting_address = 402,
                        quantity_of_x = 2,
                        output_value=[low_word1,high_word1]
                    )
            except Exception as e:
                print(f"设置距离错误: sid{s[0]}{e}")



    def close(self):
        """关闭Modbus RTU串口连接"""
        if not self.isopend:
            raise Exception(f'端口未打开: {self.PORT}')
        
        self.master.close()
        time.sleep(0.11)
        del self.master
        self.isopend = False



    def in_once(self):
        """
        读取输入寄存器
        
        参数:
            ADR: 起始地址 (默认:0)
            NUM: 读取数量 (默认:8)
        
        返回:
            读取的值存储在self.registers中
        """
        try:
            
            self.cur_reg = self.master.execute(
                1,
                fnc.READ_INPUT_REGISTERS,
                self.ADR_IN,
                self.NUM_IN 
            )
            for i in range(6):#
                if self.cur_reg[i] - self.pre_reg[i] > 0 :
                    self.trig_status[i] = 1

                elif self.cur_reg[i] - self.pre_reg[i] < 0:
                    self.trig_status[i] = 2
                    #self.count_trig_u[i] += 1 #up计数

                else : 
                    self.trig_status[i] = 0
            #print("trig_status:",self.trig_status)


            self.pre_reg = self.cur_reg
            #print("cur reg   : ",self.cur_reg)
            #print("trigstatus: ",self.trig_status)

        except Exception as e:
            print(f"输入寄存器错误: {e}")



    def beating(self):
        """
        心跳发送指令：默认读取输入，如果传参则写/设置
        使用self.in_beating_interval作为间隔时间
        """

        while True:
            if self.end:
                break
            if not self.isopend:
                time.sleep(0.5)
                continue
            time.sleep(self.beating_interval)

            func = self.func

            if func == 0:
                self.in_once()

            elif func == 1:
                self.coil_once()
                self.func = 0

            elif func == 2:
                self.set_speed()
                self.set_distance()
                self.func = 0






    def coil_once(self):
        """
        控制多个线圈
        
        参数:
            ADR: 起始地址 (默认:0)
            NUM: 线圈数量 (默认:8)
            values: 控制值列表 (默认:全部断开)
                   [62580]表示闭合, [0]表示断开
        """
        if self.values is None:
            VALUES = [0] * self.NUM_COIL         
        else :
            VALUES = self.values
        try:
            #print("VALUES:",VALUES)
            for i in range(5):
                if self.values[i] == 62580:
                    self.t1[i] = time.time()
                    self.coils[i] = 1
                else :
                    self.coils[i] = 0
            
                self.master.execute(
                    1,
                    fnc.WRITE_MULTIPLE_COILS,
                    starting_address=self.ADR_COIL,
                    quantity_of_x=self.NUM_COIL,
                    output_value=VALUES
                )
        except Exception as e:
            print(f"控制失败: {e}")



    def set_salarate(self,id,value):
        

            int_value = int(value) 
            # 2. 拆分高低16位
            high_word1 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
            low_word1 = int_value & 0xFFFF
            print(f"id\t{id-1},\nhigh_word1\t{high_word1},\nlow_word1\t{low_word1}")
            try:
                self.master.execute(
                    slave= id,
                    function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                    starting_address = 436,
                    quantity_of_x = 2,
                    output_value=[low_word1,high_word1]
                )
                self.master.execute(
                    slave= id,
                    function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                    starting_address = 438,
                    quantity_of_x = 2,
                    output_value=[low_word1,high_word1]
                )
            except Exception as e:
                print(f"设置距离错误: sid{id}{e}")



def main(): 
    print("end")



if __name__ == "__main__":
    main()