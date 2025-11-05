# SCSS2 智能服装分拣系统 V2 技术文档  
**版本**：v2.0  
**作者**：疾轶辰  
**更新时间**：2024-05-20  
**仓库地址**：https://github.com/JIYIC-P/SCSS2


## 一、项目概述
### 1.1 背景
后端：Python
前端：Python + PyQt（桌面端 GUI，无需额外环境）。
### 1.2 重构核心目标
​​全栈 Python 化​​：解决桌面端部署痛点，兼容 Windows/Linux/macOS；
​​通信增强​​：用 Python 调用C DLL库提升通信性能；
​​交互简化​​：PyQt 提供原生桌面体验，用户无需打开浏览器。
## 二、项目结构规范
### 2.1 整体目录结构
SCSS2-Smart-Clothing-Sort-System-V2/  
├── Lib/                        # 外部库/文件  
│   ├── .pt                     # yolo权重文件  
│   ├── .pth                    # clip权重文件  
│   ├── .DLL                    # C函数  
│   ├── .ini                    # 配置文件  
│   └── .yaml                   # Yolo标准格式文件  
│                  
├── source/                     # 代码部分  
│   ├── common/                   
│   │   ├── config_manager.py   # 通信管理类  
│   │   └── data_bus.py         # 数据总线，多个线程间通信用（单例）  
│   │    
│   ├── communicator.py         # 硬件通信模块    
│   │   ├── manager.py          # 通信管理类  
│   │   ├── manager_qt.py       # qt重构通信管理类  
│   │   ├── tcp.py              # TCP通信实现（DLL库调用）  
│   │   ├── camera.py           # 串口相机实现（pyserial）  
│   │   ├── modbus.py           # 串口通信（弃用）  
│   │   └── pcie.py             # PCIE IO板卡(DLL库调用)  
│   │  
│   └── logic/                  # 核心算法模块  
│       ├── logic_handler.py    # 处理接口定义（update()） 
│       ├── color_mode.py       # 颜色模式（OpenCV-Python 处理 HSV 均值）  
│       ├── clip_mode.py        # 形状模式  --clip  
│       ├── yolo_mode.py        # 形状模式  --yolo  
│       ├── hhit_mode.py        # 高光谱模式（numpy 统计特征）  
│       └── cfgmanager.py       # 配置管理类    
│                  
├── Ui/                         # 桌面端 GUI（Python + PyQt5）  
│   ├── windows/                # 窗口组件  
│   │   └── main_window.py      # 主窗口（QMainWindow）  
│   └── resources/              # 静态资源  
│       ├── icons/              # 图标（.ico/.png）  
│       └── styles/             # 样式表（.qss）  
│                  
├── main.py                     # 应用入口（启动 PyQt 主窗口）  
├── .gitignore                  # Git 忽略配置（Python + PyQt）  
├── requirements.txt            # Python 依赖（后端 + 前端）  
└── README.md                   # 项目简介（部署、使用说明）  
## 三、核心模块说明（Python + PyQt 适配）
### 3.1 后端（Python）
#### 3.1.1 通信层

#### 3.1.2 逻辑层
​
#### 3.1.3 入口（app.py）

### 3.2 前端（Python + PyQt6）
#### 3.2.1 架构设计
​​主窗口​​（main_window.py）：继承 QMainWindow，包含模式选择、图片上传、结果展示区域；  
​​自定义控件​​（widgets/）：  
ModeSelector：模式选择器（QComboBox 绑定模式列表，QLabel 显示当前模式）；  
ImageUploader：图片上传控件（QPushButton 触发文件选择，QPixmap 显示预览）；  
ResultPanel：结果展示（QTextEdit 显示处理日志，QLabel 显示分拣命令）；  
#### 3.2.2 交互逻辑
​
## 四、技术栈清单
模块  
技术/工具  
说明  
后端  
Python 3.9+、FastAPI  
轻量级 RESTful API 框架  
通信  
pyserial、asyncio.socket  
串口/TCP 通信库  
视觉算法  
OpenCV-Python、ultralytics  
图像处理/YOLOv8 推理  
前端  
PyQt5  
桌面端 GUI 框架  
工具  
Poetry、pytest  
依赖管理/测试框架  
## 五、部署指南
### 5.1 环境准备
连接硬件设备（串口相机需配置 COM 口，TCP 设备需确保网络可达）。  
安装 Python 3.11+；  
python -m pip install --upgrade pip #更新pip 
pip install -r requirements.txt  #安装项目依赖

如果有电脑有显卡则 使用cmd 输入   
nvidia-smi   
正确输出则显卡驱动已安装  
否则前往官网安装对应自身版本的显卡驱动  

打开nvidia 控制面板 点击 帮助 -> 系统信息 -> 组件 
找到 NVCUDA64.DLL 对应版本 
若无则使用cpu版本 
https://developer.nvidia.com/cuda-toolkit-archive
访问 pytorch 官网以下载对应cuda版本的torch https://pytorch.org/get-started/locally/
最后 输入 终端

### 5.2 启动服务

python main.py  # 启动 PyQt 应用  
 
## 六、维护与扩展
### 6.1 新增通信方式（如 USB）
在 通信层/interfaces定义 IUSBCommunication接口；  
实现 usb_communication.py，适配 USB 设备驱动；  
在 app.py中注入 USBCommunication服务。  
### 6.2 新增逻辑模式（如纹理识别）
在 逻辑层/interfaces定义 ITextureProcessor接口；  
实现 texture_processor.py，用 OpenCV 提取纹理特征；  
在 ModelProcessor中注册纹理模式。  
### 6.3 打包发布 
用 PyInstaller将前端 PyQt 应用打包为可执行文件：  
pip install pyinstaller  
pyinstaller --onefile --windowed main.py  # 生成 Windows 可执行文件  
## 七、附录
### 7.1 配置文件


### 7.2 常用命令

