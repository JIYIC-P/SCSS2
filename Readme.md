# SCSS2 智能服装分拣系统 V2 技术文档  
**版本**：v2.0  
**作者**：熊雅文  
**更新时间**：2024-05-20  
**仓库地址**：[github.com/your-team/scss2](https://github.com/your-team/scss2)  


## 一、项目概述
### 1.1 背景
原 SCSS1 系统采用「Node.js 后端 + Vue 前端」，但​​桌面端部署复杂​​（需 Node.js 环境），且硬件通信库对 Windows 兼容性差。重构后采用 ​​Python 全栈​​：
后端：Python + FastAPI（提供 RESTful API，适配硬件通信）；
前端：Python + PyQt（桌面端 GUI，直接调用后端 API，无需额外环境）。
### 1.2 重构核心目标
​​全栈 Python 化​​：解决桌面端部署痛点，兼容 Windows/Linux/macOS；
​​硬件适配增强​​：用 Python 库（pyserial、pyvisa）兼容更多工业设备；
​​交互简化​​：PyQt 提供原生桌面体验，用户无需打开浏览器。
## 二、项目结构规范
### 2.1 整体目录结构
SCSS2-Smart-Clothing-Sort-System-V2/  
├── 后端/                  # 后端服务（Python）  
│   ├── 通信层/             # 硬件通信模块  
│   │   ├── tcp/            # TCP通信实现（asyncio + socket）  
│   │   ├── serial_camera/  # 串口相机实现（pyserial）  
│   │   └── pcie_io/        # PCIE IO板卡（pyvisa，保留参考）  
│   │  
│   ├── 逻辑层/             # 核心算法模块  
│   │   ├── interfaces/     # 处理接口定义（abc_model_processor.py）  
│   │   ├── color_mode/     # 颜色模式（OpenCV-Python 处理 HSV 均值）  
│   │   ├── shape_mode/     # 形状模式  
│   │   │   ├── yolo/       # YOLOv8 模型推理（ultralytics 库）  
│   │   │   └── clip/       # CLIP 文本-图像匹配（sentence-transformers）  
│   │   └── hyperspectral/  # 高光谱模式（numpy 统计特征）  
│   │  
│   ├── utils/              # 通用工具  
│   │   ├── image_utils.py  # 图像预处理（缩放、灰度化，OpenCV）  
│   │   └── logger.py       # 日志封装（logging 模块）  
│   │  
│   ├── config/             # 配置文件  
│   │   ├── __init__.py     # 配置初始化  
│   │   ├── settings.py     # 主配置（通信参数、模式开关）  
│   │   └── types.py        # 配置类型定义（Pydantic 模型）   
│  
├── 前端/                  # 桌面端 GUI（Python + PyQt5）  
│   ├── main.py             # 应用入口（启动 PyQt 主窗口）  
│   ├── windows/            # 窗口组件  
│   │   └── main_window.py  # 主窗口（QMainWindow）  
│   ├── widgets/            # 自定义控件  
│   │   ├── mode_selector.py  # 模式选择器（QComboBox + QLabel）  
│   │   ├── image_uploader.py # 图片上传（QPushButton + QPixmap）  
│   │   └── result_panel.py   # 结果展示（QTextEdit + QLabel）  
│   ├── resources/          # 静态资源  
│   │   ├── icons/          # 图标（.ico/.png）  
│   │   └── styles/         # 样式表（.qss）  
│   └── services/           # 后端 API 服务（requests 调用）  
│       └── api_client.py   
│  
├── .gitignore              # Git 忽略配置（Python + PyQt）  
├── requirements.txt        # Python 依赖（后端 + 前端）  
└── README.md               # 项目简介（部署、使用说明）  
## 三、核心模块说明（Python + PyQt 适配）
### 3.1 后端（Python + FastAPI）
#### 3.1.1 通信层
#### 3.1.2 逻辑层
​​接口定义​​：用 abc_model_processor.py定义算法处理接口：  
from abc import ABC, abstractmethod  
from pydantic import BaseModel  

class InputData(BaseModel):  
    image_path: str       # 图片路径  
    numpy_data: Optional[list] = None  # 高光谱 numpy 数组  

class Command(BaseModel):  
    type: str             # 命令类型（SORT/STOP）  
    target: str           # 目标位置（BIN_A/BIN_B）  

class IModelProcessor(ABC):  
    @abstractmethod  
    async def process(self, data: InputData) -> Command: ...  
    @abstractmethod  
    async def init_model(self) -> None: ...  # 模型初始化（如 YOLO 加载权重）  
​​YOLO 实现​​：用 ultralytics库加载 YOLOv8 模型，推理图片中的服装类别；  
​​颜色模式​​：用 OpenCV-Python计算图片 HSV 通道的均值，判断服装颜色。  
#### 3.1.3 入口（app.py）
初始化 FastAPI 应用，挂载路由（如 /api/process处理分拣请求）；  
注入通信层与逻辑层的依赖（如 CommunicationService、ModelProcessor）；  
示例路由：  
from fastapi import FastAPI, UploadFile, File  
from logic_layer.processors import ModelProcessor  

app = FastAPI()  

@app.post("/api/process")  
async def process_image(file: UploadFile = File(...), mode: str = "color"):  
    # 调用逻辑层处理图片
    result = await ModelProcessor().process(  
        InputData(image_path=file.filename)  
    )  
    return result  
### 3.2 前端（Python + PyQt6）
#### 3.2.1 架构设计
​​主窗口​​（main_window.py）：继承 QMainWindow，包含模式选择、图片上传、结果展示区域；  
​​自定义控件​​（widgets/）：  
ModeSelector：模式选择器（QComboBox 绑定模式列表，QLabel 显示当前模式）；  
ImageUploader：图片上传控件（QPushButton 触发文件选择，QPixmap 显示预览）；  
ResultPanel：结果展示（QTextEdit 显示处理日志，QLabel 显示分拣命令）；  
​​API 客户端​​（services/api_client.py）：用 requests库调用后端   FastAPI 接口：  
import requests    

class ApiClient:  
    def __init__(self, base_url: str = "http://localhost:8000"):  
        self.base_url = base_url  

    async def process_image(self, file_path: str, mode: str) -> dict:  
        with open(file_path, "rb") as f:  
            files = {"file": f}  
            response = requests.post(f"{self.base_url}/api/process?  mode={mode}", files=files)  
        return response.json()  
#### 3.2.2 交互逻辑
​​信号槽机制​​：用 PyQt 的信号传递状态（如处理中、结果返回）：  
from PyQt6.QtCore import pyqtSignal, QObject  

class ProcessSignal(QObject):  
    processing = pyqtSignal(bool)  # 处理中状态  
    result_ready = pyqtSignal(dict) # 结果就绪  
​​按钮点击事件​​：点击「开始分拣」时，调用 ApiClient发送请求，更新界面状态：  
from PyQt5.QtWidgets import QPushButton  

class MainWindow(QMainWindow):  
    def __init__(self):  
        super().__init__()  
        self.process_btn = QPushButton("开始分拣")  
        self.process_btn.clicked.connect(self.on_process_click)  

    def on_process_click(self):  
        # 触发处理中信号  
        self.process_signal.processing.emit(True)  
        # 调用 API  
        result = self.api_client.process_image(self.image_path, self.mode)  
        # 更新结果界面  
        self.result_panel.update_result(result)  
        # 关闭处理中状态
        self.process_signal.processing.emit(False)  
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
安装 Python 3.11+；  
安装 PyQt5：pip install pyqt5；  
连接硬件设备（串口相机需配置 COM 口，TCP 设备需确保网络可达）。  
### 5.2 启动服务
后端启动  
cd 后端/  
poetry install  # 安装依赖（或 pip install -r requirements.txt）  
uvicorn app:app --reload --port 8000  # 启动 FastAPI 服务  
前端启动  
cd 前端/  
poetry install  # 安装依赖  
python main.py  # 启动 PyQt 应用  
### 5.3 测试验证
启动后端服务；  
启动 PyQt 前端；  
选择「颜色模式」，上传服装图片；  
点击「开始分拣」，查看结果面板的分拣命令（如 {"type": "SORT", "target": "BIN_A"}）。  
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
### 7.1 配置文件（config/settings.py）
from pydantic_settings import BaseSettings  

class Settings(BaseSettings):  
    communication_type: str = "tcp"  # 通信类型：tcp/serial  
    tcp_host: str = "192.168.1.100"  
    tcp_port: int = 8080  
    serial_baudrate: int = 9600  
    modes: dict = {"color": True, "yolo": True, "clip": False}  

settings = Settings()  
### 7.2 常用命令
命令  
描述  
poetry add fastapi  
添加 FastAPI 依赖  
pytest tests/  
运行所有测试用例  
pyinstaller main.py  
打包 PyQt 应用  
​​文档结束​​ —— 欢迎提交 Issue 或 PR 参与贡献！  
