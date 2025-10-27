#基于python3.6版本
#北京飞扬助力电子技术有限公司 www.fyying.com
#----------------------

from ctypes import *#引入ctypes库
import time#使用延时函数

#下面两种调用DLL函数的方式都可以
#dll=WinDLL("C:\Windows\System32\FY5400.dll")
dll=windll.LoadLibrary(r"source\Lib\FY5400.dll")

hDev=dll.FY5400_OpenDevice(0)#获得句柄
print("句柄值是" + str(hDev))
print("程序开始运行")


count=0
while(count<1000):#循环1000次
	
	t1 = time.time()
	#dll.FY5400_DO(hDev,0)#输出通道全部置低
	#dll.FY5400_DO(hDev,65535)#输出通道全部置高

	
	didata=dll.FY5400_DI(hDev)#获得所有输入通道的状态
	print("didata is " + str(didata))
	
	#dll.FY5400_EEPROM_WR(hDev,0,3)#地址0写入数据3 这个数据可以任意修改 范围0--255
	#eedata=dll.FY5400_EEPROM_RD(hDev,0)#读取地址0的数据
	#print("eeprom data is " + str(eedata))#显示数据
	print(time.time()-t1)
	count=count+1
#说明：函数的意义以及参数请参考手册，需要技术支持，请联系15911028547




"""
需求：
创建一个类，用于实现板卡的IO操作，
要求创建线程，每一段时间读取或写入办卡
提供接口用于获取读到的数据，接受数据，写入到办卡。
线程启动器和停止器。
"""