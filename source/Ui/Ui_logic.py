from PyQt5.QtCore import pyqtSlot, Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QDialog, QTableWidgetItem, QMessageBox, 
    QAbstractItemView, QPushButton, QHBoxLayout, QLabel, 
    QVBoxLayout, QDialogButtonBox, QTableWidget
)
from Ui.window_mian import Ui_MainWindow
from common.data_bus import DataBus
from Ui.dialog_mode_change import Ui_modechange as Modechange
import numpy as np
import cv2


class ChooseColorDialog(QDialog):
    def __init__(self, mode):
        super().__init__()
        self.ui = Modechange()
        self.ui.setupUi(self)
        self.setWindowTitle("模式选择")
        self.ui.label.setText(f"是否选择{mode}模式？")
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)


class MainWindowLogic(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.bus = DataBus()

        # 绑定信号
        ## 四种模式
        self.ui.action_ToColorMode.triggered.connect(self.changemode)
        self.ui.action_ToYoloMode.triggered.connect(self.changemode)
        self.ui.action_ToClipMode.triggered.connect(self.changemode)
        self.ui.action_ToHhitMode.triggered.connect(self.changemode)
        
        ## 五个工位
        self.ui.btn_SetWorker0.clicked.connect(self.setwoker)
        self.ui.btn_SetWorker1.clicked.connect(self.setwoker)
        self.ui.btn_SetWorker2.clicked.connect(self.setwoker)
        self.ui.btn_SetWorker3.clicked.connect(self.setwoker)
        self.ui.btn_SetWorker4.clicked.connect(self.setwoker)
        
        ## 五个推杆
        self.bus.pcie_do.connect(self.update_do_led)

        ## 六个传感器
        self.bus.pcie_di.connect(self.update_in_led)

        ## 两个画面
        self.bus.camera0_img.connect(self.update_mianframe)
        self.bus.camera1_img.connect(self.update_secondframe)

        ## 延时配置
        self.ui.btn_SetDelay.clicked.connect(self.set_delay)

        ## 推杆控制
        self.ui.btn_ShiftPusher.clicked.connect(self.bus.do_push.emit)


        # 工位标签存储
        self.worker_labels = {}  # {工位名称: [{"id": ..., "text": ..., "color": QColor}, ...]}
        self.original_labels = None  # 保存原始完整标签，用于重置
        
        self.lables = None
        self.left_labels = None
        self.current_mode = None

        # 保存工位按钮引用
        self.worker_buttons = {
            "工位0": self.ui.btn_SetWorker0,
            "工位1": self.ui.btn_SetWorker1,
            "工位2": self.ui.btn_SetWorker2,
            "工位3": self.ui.btn_SetWorker3,
            "工位4": self.ui.btn_SetWorker4
        }
        
        # 存储当前选中的行ID
        self.selected_color_id = None

        # ✅ 新增：用于自动收回逻辑
        self.current_pusher_do = None  # 当前处于推出状态的推杆编号，None表示无
        self.pusher_timer = QTimer()
        self.pusher_timer.setSingleShot(True)
        self.pusher_timer.timeout.connect(self._on_pusher_timeout)

    def _on_pusher_timeout(self):
        # ✅ 定时器超时后，清除当前推出状态，UI自动恢复为红色
        self.current_pusher_do = None
        self.update_do_led(self.current_pusher_do)

    def colormode_init(self):
        self.ui.btn_Add.clicked.connect(self.add_column)
        self.ui.btn_Delete.clicked.connect(self.delete_selected_color_row)
        self.ui.btn_LoadColor.clicked.connect(self.LoadColor)
        self.ui.tab_Color.itemSelectionChanged.connect(self.on_color_row_selected)
        self.ui.btn_SetColor.clicked.connect(self.set_color)
        self.bus.color_hsv.connect(self.update_color_hsv)

    # ==================== 辅助函数 ====================
    
    def LoadColor(self):
        self.show_colorange()
        self.bus.color_set.emit()

    def hsv_to_qcolor(self, hsv_list):
        """将HSV列表 [h, s, v] 转换为 QColor"""
        if not hsv_list or len(hsv_list) != 3:
            return QColor(128, 128, 128)  # 默认灰色
        
        h, s, v = hsv_list
        
        # 规范化：h:0-360, s:0-255, v:0-255
        h = max(0, min(360, float(h)))
        s = max(0, min(255, float(s)))
        v = max(0, min(255, float(v)))
        
        # 转换为RGB
        s_norm = s / 255.0
        v_norm = v / 255.0
        
        c = v_norm * s_norm
        x = c * (1 - abs(((h / 60.0) % 2) - 1))
        m = v_norm - c
        
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        r = int((r + m) * 255)
        g = int((g + m) * 255)
        b = int((b + m) * 255)
        
        return QColor(r, g, b)
    
    def get_next_color_id(self):
        """获取下一个可用的ID"""
        existing_ids = []
        row_count = self.ui.tab_Color.rowCount()
        
        for row in range(row_count):
            item = self.ui.tab_Color.item(row, 0)
            if item:
                existing_ids.append(item.text())
        
        # 找到最大的数字ID
        max_id = -1
        for id_str in existing_ids:
            try:
                max_id = max(max_id, int(id_str))
            except ValueError:
                pass
        
        return str(max_id + 1)
    
    def on_color_row_selected(self):
        """表格行选中回调"""
        selected_items = self.ui.tab_Color.selectedItems()
        if not selected_items:
            self.selected_color_id = None
            return
        
        # 获取选中的行
        row = selected_items[0].row()
        id_item = self.ui.tab_Color.item(row, 0)
        
        if id_item:
            self.selected_color_id = id_item.text()
            # 预留：触发HSV设置对话框
            # self.open_hsv_picker(self.selected_color_id)
    
    # ==================== 核心功能函数 ====================
    
    def show_colorange(self):
        """
        从bus.cfg中获取color label信息，然后通过表格显示出来
        表格对象是ui.tab_Color
        """
        # 清空表格
        self.ui.tab_Color.clearContents()
        
        # 获取color_mode配置
        color_labels = self.bus.cfg.get("color_mode", "labels", default={})
        
        if not color_labels:
            self.ui.tab_Color.setRowCount(0)
            return
        
        # 设置表格行数
        self.ui.tab_Color.setRowCount(len(color_labels))
        
        # 设置列宽（可选）
        self.ui.tab_Color.setHorizontalHeaderLabels(["ID", "颜色预览", "Range"])
        self.ui.tab_Color.setColumnWidth(0, 50)   # ID列较窄
        self.ui.tab_Color.setColumnWidth(1, 80)   # 颜色预览列
        self.ui.tab_Color.setColumnWidth(2, 100)  # Range编辑列
        
        # 填充数据
        for row, (label_id, data) in enumerate(color_labels.items()):
            # 解析数据: [[h,s,v], range]
            hsv_values = data[0] if len(data) > 0 else [0, 0, 0]
            range_value = data[1] if len(data) > 1 else 5
            
            # 第0列：ID
            id_item = QTableWidgetItem(str(label_id))
            id_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.ui.tab_Color.setItem(row, 0, id_item)
            
            # 第1列：颜色预览
            color = self.hsv_to_qcolor(hsv_values)
            color_item = QTableWidgetItem("")
            color_item.setBackground(color)
            color_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.ui.tab_Color.setItem(row, 1, color_item)
            
            # 第2列：Range（可编辑）
            range_item = QTableWidgetItem(str(range_value))
            range_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable | 
                Qt.ItemFlag.ItemIsEnabled | 
                Qt.ItemFlag.ItemIsEditable
            )
            self.ui.tab_Color.setItem(row, 2, range_item)
        
        # 启用整行选择
        self.ui.tab_Color.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    
    def add_column(self):
        """
        添加一行额外的colorlabel
        新的id递增生成，range默认为5
        """
        # 获取新ID
        new_id = self.get_next_color_id()
        
        # 添加新行
        row = self.ui.tab_Color.rowCount()
        self.ui.tab_Color.insertRow(row)
        
        # 第0列：ID（不可编辑）
        id_item = QTableWidgetItem(new_id)
        id_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.ui.tab_Color.setItem(row, 0, id_item)
        
        # 第1列：颜色预览（初始灰色）
        color_item = QTableWidgetItem("")
        color_item.setBackground(QColor(128, 128, 128))
        color_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.ui.tab_Color.setItem(row, 1, color_item)
        
        # 第2列：Range（默认可编辑）
        range_item = QTableWidgetItem("5")
        range_item.setFlags(
            Qt.ItemFlag.ItemIsSelectable | 
            Qt.ItemFlag.ItemIsEnabled | 
            Qt.ItemFlag.ItemIsEditable
        )
        self.ui.tab_Color.setItem(row, 2, range_item)
        # 自动选中新行
        self.ui.tab_Color.selectRow(row)
    
    def set_color(self):
        """
        调用cfg.set()写入colorlabel
        从表格读取数据并保存到JSON
        """
        row_count = self.ui.tab_Color.rowCount()
        if row_count == 0:
            return
        
        # 构建要保存的数据结构
        color_labels = {}
        
        for row in range(row_count):
            # 读取ID
            id_item = self.ui.tab_Color.item(row, 0)
            if not id_item:
                continue
            label_id = id_item.text()
            
            # 读取Range（并验证范围）
            range_item = self.ui.tab_Color.item(row, 2)
            if not range_item:
                continue
            
            try:
                range_value = int(range_item.text())
                # 限制range范围在0-25
                range_value = max(0, min(25, range_value))
            except ValueError:
                range_value = 5  # 默认值
            
            # 获取颜色预览的HSV值（这里需要您后续实现）
            # 暂时从单元格数据中获取，如果存在的话
            # 新添加的行可能还没有HSV值
            hsv_values = [0, 0, 0]  # 默认值
            
            # 检查是否已有HSV数据（从原始配置中保留）
            existing_data = self.bus.cfg.get("color_mode", "labels", label_id, default=None)
            if existing_data and isinstance(existing_data, list) and len(existing_data) > 0:
                hsv_values = existing_data[0]
            
            # 构建数据项
            color_labels[label_id] = [hsv_values, range_value]
        
        # 使用cfg.set()写入
        self.bus.cfg.set("color_mode", "labels", value=color_labels)
        
        # 可选：显示保存成功提示
        QMessageBox.information(self, "保存成功", "颜色标签配置已保存！")
    
    # ==================== 预留槽函数（供您后续实现） ====================
    
    def delete_selected_color_row(self):
        """删除选中的颜色标签行"""
        selected_items = self.ui.tab_Color.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        self.ui.tab_Color.removeRow(row)
        
        # 注意：这里不会立即保存到JSON，需要用户点击保存按钮
    
    def update_color_hsv(self, hsv_values):
        """
        通过回调更新当前选中行的颜色HSV值
        调用此函数后更新表格预览
        """
        # 如果没有选中任何行，直接返回不执行
        if self.selected_color_id is None:
            return
        
        # 查找对应选中的行
        for row in range(self.ui.tab_Color.rowCount()):
            id_item = self.ui.tab_Color.item(row, 0)
            if id_item and id_item.text() == str(self.selected_color_id):
                # 更新颜色预览
                color = self.hsv_to_qcolor(hsv_values)
                color_item = self.ui.tab_Color.item(row, 1)
                if color_item:
                    color_item.setBackground(color)
                
                # 注意：HSV值的持久化存储需要在调用set_color()时处理
                # 这里仅更新UI显示
                break

    def ndarry2pixmap(self, array: np.ndarray):
        height, width, channel = array.shape
        bytes_per_line = width * channel
        rgb_array = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
        qimage = QImage(
            rgb_array.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(qimage)
        return pixmap
    
    def update_mianframe(self, array: np.ndarray):
        self.ui.lab_ShowFrame0Pic.setPixmap(self.ndarry2pixmap(array))

    def update_secondframe(self, array: np.ndarray):
        self.ui.lab_ShowFrame1Pic.setPixmap(self.ndarry2pixmap(array))

    def changemode(self):
        """模式切换，加载并转换标签数据"""
        action = self.sender()
        if not action:
            return
            
        mode_text = action.text()
        print(f"【调试】收到模式文本: '{mode_text}'")
        
        mode_map = {
            '颜色': 'color',
            '高光谱': 'hhit',
            'yolo': 'yolo',
            'clip': 'clip'
        }
        
        new_mode = mode_map.get(mode_text)
        if not new_mode:
            QMessageBox.warning(self, "错误", f"未知的模式: '{mode_text}'")
            return
            
        dialog = ChooseColorDialog(mode_text)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            self.current_mode = new_mode
            try:
                self.bus.result.disconnect(self.update_result)  # 断开所有旧连接
            except:
                pass  # 如果之前未连接，会抛异常，忽略即可
        
            self.bus.result.connect(self.update_result)  # 重新连接
            cfg_key = f"{new_mode}_mode"
            self.lables = self.bus.cfg.get(cfg_key, "labels")
            self.show_delay()
            if self.lables is None:
                QMessageBox.warning(self, "警告", 
                    f"无法加载 {mode_text} 模式的标签配置！\n配置键: {cfg_key}")
                return
                
            print(f"【调试】成功加载标签数据: {type(self.lables)}, 数量: {len(self.lables)}")

            if self.current_mode == "color":
                self.colormode_init()
            
            # 保存原始标签用于重置
            self.original_labels = self.lables.copy()
            # 转换数据格式
            self.left_labels = self._convert_labels_for_display(self.lables)
            # 重置工位分配
            self.worker_labels.clear()
            self.bus.mode_changed.emit(self.current_mode)
            self.bus.result.connect(self.update_result)
            self._update_worker_buttons()
            # ==== 新增：加载工位配置并自动映射 ====
            self._load_and_apply_worker_config(new_mode)
            
            # 发射信号
            self._emit_worker_labels()
            
            QMessageBox.information(
                self, 
                "模式切换成功", 
                f"已切换到 {mode_text} 模式\n剩余 {len(self.left_labels)} 个标签待分配"
            )

    def update_result(self,result:list):
        if self.current_mode == "color":
            self.ui.lab_ShowFrame0Txt.setText(f"\t\t主视角  ID:{result[0]}")
        elif self.current_mode in ("clip","yolo"):
            self.ui.lab_ShowFrame0Txt.setText(f"\t\t主视角  ID:{result[0]}\tLabel:{result[1]}")

    def _convert_labels_for_display(self, raw_labels):
        """
        将原始标签数据转换为显示格式
        返回: [{"id": ..., "text": ..., "color": QColor}, ...]
        """
        display_data = []
        
        if not raw_labels:
            print("【调试】raw_labels为空")
            return display_data
        
        print(f"【调试】转换模式: {self.current_mode}, 原始数据类型: {type(raw_labels)}")
        
        if self.current_mode == "color":
            # color_mode: {"0": [[hsv], 5], "1": [[hsv], 5], ...}
            for key, value in raw_labels.items():
                try:
                    if isinstance(value, list) and len(value) >= 1:
                        hsv_array = value[0]
                        if isinstance(hsv_array, (list, np.ndarray)) and len(hsv_array) >= 3:
                            # HSV转RGB
                            hsv_pixel = np.uint8([[[hsv_array[0], hsv_array[1], hsv_array[2]]]])
                            rgb_pixel = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2RGB)
                            color = QColor(int(rgb_pixel[0][0][0]), int(rgb_pixel[0][0][1]), int(rgb_pixel[0][0][2]))
                            display_data.append({
                                "id": key,
                                "text": "", 
                                "color": color
                            })
                        else:
                            print(f"【警告】无效的HSV数据: key={key}, value={value}")
                    else:
                        print(f"【警告】无效的color数据格式: key={key}, value={value}")
                except Exception as e:
                    print(f"【错误】转换color标签失败: key={key}, error={e}")
        else:
            # clip_mode & hhit_mode: {"标签名": id, ...}
            for label_name, label_id in raw_labels.items():
                display_data.append({
                    "id": label_id,
                    "text": str(label_name)
                })
        
        print(f"【调试】转换后数据: {display_data}")
        return display_data

    def _load_and_apply_worker_config(self, mode):
        """
        加载工位配置并自动映射标签
        配置格式: "colorworker": [[0,1], [], [], [], []]
        """
        worker_cfg_key = f"{mode}worker"
        worker_config = self.bus.cfg.get(worker_cfg_key)
        
        if worker_config is None:
            print(f"【调试】未找到工位配置: {worker_cfg_key}")
            return
        
        if not isinstance(worker_config, list) or len(worker_config) != 5:
            print(f"【警告】工位配置格式错误: {worker_cfg_key} = {worker_config}")
            QMessageBox.warning(self, "警告", f"工位配置格式错误，请检查配置文件！\n键: {worker_cfg_key}")
            return
        
        print(f"【调试】加载工位配置: {worker_cfg_key} = {worker_config}")
        
        # 创建标签ID到标签数据的映射，方便快速查找
        label_id_map = {str(label["id"]): label for label in self.left_labels}
        
        # 遍历5个工位
        for i, label_ids in enumerate(worker_config):
            if not label_ids:
                continue  # 跳过空配置
            
            worker_name = f"工位{i}"
            
            # 验证并收集标签
            valid_labels = []
            missing_ids = []
            
            for label_id in label_ids:
                label_id_str = str(label_id)
                if label_id_str in label_id_map:
                    valid_labels.append(label_id_map[label_id_str])
                else:
                    missing_ids.append(label_id)
            
            # 报告缺失的标签
            if missing_ids:
                print(f"【警告】工位 {worker_name} 的标签ID不存在: {missing_ids}")
                QMessageBox.warning(
                    self, 
                    "标签缺失", 
                    f"工位 {worker_name} 的部分标签ID不存在: {missing_ids}\n"
                    f"请检查配置或标签数据！"
                )
            
            # 分配有效标签到工位
            if valid_labels:
                self.worker_labels[worker_name] = valid_labels
                
                # 从可用池中移除已分配的标签
                for label in valid_labels:
                    if label in self.left_labels:
                        self.left_labels.remove(label)
                
                print(f"【调试】工位 {worker_name} 自动分配 {len(valid_labels)} 个标签")
        
        # 更新按钮显示
        self._update_worker_buttons()
        
        # 显示自动分配结果
        total_assigned = sum(len(labels) for labels in self.worker_labels.values())
        QMessageBox.information(
            self,
            "工位配置加载完成",
            f"已从配置加载并自动分配 {total_assigned} 个标签到各工位\n"
            f"剩余可用标签: {len(self.left_labels)}"
        )

    def _create_choice_dialog(self, display_data, title="请选择对应的选项"):
        """
        动态创建选择对话框
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['ID', '预览/标签'])
        table.setSelectionMode(QAbstractItemView.MultiSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 填充表格数据
        table.setRowCount(len(display_data))
        for row_idx, item in enumerate(display_data):
            # ID列
            table.setItem(row_idx, 0, QTableWidgetItem(str(item["id"])))
            
            # 预览/标签列
            if "color" in item and item["color"] is not None:
                color_item = QTableWidgetItem()
                color_item.setBackground(item["color"])
                color_item.setText("  ")
                table.setItem(row_idx, 1, color_item)
            else:
                table.setItem(row_idx, 1, QTableWidgetItem(str(item["text"])))
        
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        
        # 创建控制按钮布局
        btn_Layout = QHBoxLayout()
        
        btn_SelectAll = QPushButton("全选")
        btn_SelectAll.clicked.connect(table.selectAll)
        
        btn_Clear = QPushButton("清空")
        btn_Clear.clicked.connect(table.clearSelection)
        
        count_label = QLabel("已选中: 0")
        
        btn_Layout.addWidget(btn_SelectAll)
        btn_Layout.addWidget(btn_Clear)
        btn_Layout.addStretch()
        btn_Layout.addWidget(count_label)
        
        # 创建按钮框
        btn_Box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_Box.accepted.connect(dialog.accept)
        btn_Box.rejected.connect(dialog.reject)
        
        # 更新选中计数
        def update_count():
            count = len(table.selectionModel().selectedRows())
            count_label.setText(f"已选中: {count}")
        
        table.itemSelectionChanged.connect(update_count)
        
        # 组装布局
        main_layout.addLayout(btn_Layout)
        main_layout.addWidget(table)
        main_layout.addWidget(btn_Box)
        
        dialog.setLayout(main_layout)
        dialog.setMinimumSize(400, 300)
        
        # 将表格存储在dialog中以便后续访问
        dialog.table_widget = table
        
        return dialog

    def _get_selected_ids(self, dialog):
        """从对话框获取选中的ID列表"""
        selected_ids = []
        table = getattr(dialog, 'table_widget', None)
        if table:
            for index in table.selectionModel().selectedRows():
                id_item = table.item(index.row(), 0)
                if id_item:
                    selected_ids.append(id_item.text())
        return selected_ids

    def _emit_worker_labels(self):
        """
        构建并发射工位标签二维列表信号
        格式: [[0,2], [1], [3], [], []]
        第一维: 5个工位
        第二维: 每个工位的标签ID列表（整数列表）
        """
        # 初始化5个空列表
        worker_array = [[] for _ in range(5)]
        
        # 按工位顺序填充标签ID
        for i in range(5):
            worker_name = f"工位{i}"
            if worker_name in self.worker_labels:
                # 提取该工位的所有标签ID（转换为整数）
                ids = [int(label["id"]) for label in self.worker_labels[worker_name]]
                worker_array[i] = ids
        
        # 发射信号
        self.bus.worker.emit(worker_array)
        print(f"【调试】发射工位标签信号: {worker_array}")

    def _update_worker_buttons(self):
        """更新工位按钮文本，显示已分配标签数量"""
        for worker_name, button in self.worker_buttons.items():
            assigned = self.worker_labels.get(worker_name, [])
            if assigned:
                button.setText(f"{worker_name} ({len(assigned)})")
            else:
                button.setText(worker_name)

    def _show_assigned_labels(self, worker_name):
        """显示已分配标签的对话框，支持取消"""
        assigned = self.worker_labels.get(worker_name, [])
        if not assigned:
            return False
            
        # 创建对话框显示已分配标签
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{worker_name} - 已分配标签")
        layout = QVBoxLayout()
        
        # 提示文字
        label = QLabel(f"{worker_name} 已分配 {len(assigned)} 个标签：")
        layout.addWidget(label)
        
        # 创建表格显示已分配标签
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['ID', '预览/标签'])
        table.setSelectionMode(QAbstractItemView.MultiSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setRowCount(len(assigned))
        
        for row_idx, item in enumerate(assigned):
            table.setItem(row_idx, 0, QTableWidgetItem(str(item["id"])))
            if "color" in item and item["color"] is not None:
                color_item = QTableWidgetItem()
                color_item.setBackground(item["color"])
                color_item.setText("  ")
                table.setItem(row_idx, 1, color_item)
            else:
                table.setItem(row_idx, 1, QTableWidgetItem(str(item["text"])))
        
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        # 按钮框
        btn_Box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_Box.button(QDialogButtonBox.Ok).setText("确定")
        btn_Box.button(QDialogButtonBox.Cancel).setText("取消选中并重新分配")
        btn_Box.accepted.connect(dialog.accept)
        btn_Box.rejected.connect(dialog.reject)
        
        layout.addWidget(btn_Box)
        dialog.setLayout(layout)
        dialog.setMinimumSize(400, 300)
        
        result = dialog.exec_()
        
        if result == QDialog.Rejected:
            # 获取选中的要取消的标签
            selected_rows = table.selectionModel().selectedRows()
            if selected_rows:
                # 从已分配中移除
                rows_to_remove = [index.row() for index in selected_rows]
                removed_labels = [assigned[i] for i in sorted(rows_to_remove, reverse=True)]
                
                for label in removed_labels:
                    assigned.remove(label)
                    # 将标签加回可用池
                    self.left_labels.append(label)
                
                # 更新按钮文本
                self._update_worker_buttons()
                
                # 重新排序可用标签，保持ID顺序
                self.left_labels.sort(key=lambda x: int(x["id"]) if str(x["id"]).isdigit() else str(x["id"]))
                
                # 发射更新后的标签信号
                self._emit_worker_labels()
                
                QMessageBox.information(
                    self, 
                    "取消成功", 
                    f"已从 {worker_name} 移除 {len(removed_labels)} 个标签\n剩余可用标签: {len(self.left_labels)}"
                )
                return True
        
        return False

    def setwoker(self):
        """工位标签分配（支持取消和重新分配）"""
        btn = self.sender()
        if not btn:
            return
            
        worker_name = btn.text().split(" ")[0]  # 获取工位名称（去掉数量显示）
        
        # 检查是否有可用标签，并且不是全部已分配
        if not self.left_labels and worker_name not in self.worker_labels:
            QMessageBox.warning(self, "警告", "请先选择模式并加载标签数据！\n或所有标签已分配完毕！")
            return
        
        # 如果该工位已有分配，先显示已分配标签，支持取消
        if worker_name in self.worker_labels:
            canceled = self._show_assigned_labels(worker_name)
            if canceled:
                # 已取消部分标签，重新进入分配流程
                pass
            # 如果没有取消或取消后还有标签，继续显示选择对话框
        
        # 如果没有可用标签了，退出
        if not self.left_labels:
            QMessageBox.information(self, "提示", "没有更多标签可供分配！")
            return
        
        # 显示选择对话框
        dialog = self._create_choice_dialog(self.left_labels, f"为 {worker_name} 选择标签")
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            selected_ids = self._get_selected_ids(dialog)
            if selected_ids:
                # 从剩余标签中取出选中的标签
                selected_labels = []
                for label_id in selected_ids:
                    for label in self.left_labels:
                        if str(label["id"]) == label_id:
                            selected_labels.append(label)
                            break
                
                # 从剩余池中移除
                for label in selected_labels:
                    self.left_labels.remove(label)
                
                # 添加到工位（如果是重新分配，覆盖原有）
                self.worker_labels[worker_name] = selected_labels
                
                # 更新按钮文本
                self._update_worker_buttons()
                
                # 发射更新后的标签信号
                self._emit_worker_labels()
                
                QMessageBox.information(
                    self, 
                    "分配成功", 
                    f"工位 {worker_name} 已分配 {len(selected_labels)} 个标签\n剩余标签数: {len(self.left_labels)}"
                )
                
                print(f"工位 {worker_name} 已分配标签: {[l['id'] for l in selected_labels]}")
                
                if not self.left_labels:
                    QMessageBox.information(self, "提示", "所有标签已分配完毕！")
            else:
                QMessageBox.information(self, "提示", "未选择任何标签！")

    @pyqtSlot(int)
    def update_do_led(self, do):
        # ✅ 增强功能：如果 do 是 None 或不在 0~4，则所有按钮为红色，清除状态
        if do is None or not (0 <= do <= 4):
            self.current_pusher_do = None
            do = None

        # ✅ 设置每个推杆按钮的背景色
        self.ui.btn_PusherStatus0.setStyleSheet("background:green" if do == 0 else "background:red")
        self.ui.btn_PusherStatus1.setStyleSheet("background:green" if do == 1 else "background:red")
        self.ui.btn_PusherStatus2.setStyleSheet("background:green" if do == 2 else "background:red")
        self.ui.btn_PusherStatus3.setStyleSheet("background:green" if do == 3 else "background:red")
        self.ui.btn_PusherStatus4.setStyleSheet("background:green" if do == 4 else "background:red")

        # ✅ 如果 do 是有效值（0~4），则启动 1.5 秒定时器，超时后自动清除状态（模拟收回）
        if do is not None and 0 <= do <= 4:
            self.current_pusher_do = do
            self.pusher_timer.start(1500)  # 1.5 秒后自动恢复为红色
        else:
            self.current_pusher_do = None

    def _on_pusher_timeout(self):
        self.current_pusher_do = None
        self.update_do_led(self.current_pusher_do)

    def update_in_led(self, di):
        self.ui.btn_InStatus0.setStyleSheet("background:green" if (di & (1 << 0)) == 1 else "background:red")
        self.ui.btn_InStatus1.setStyleSheet("background:green" if (di & (1 << 1)) == 1 else "background:red")
        self.ui.btn_InStatus2.setStyleSheet("background:green" if (di & (1 << 2)) == 1 else "background:red")
        self.ui.btn_InStatus3.setStyleSheet("background:green" if (di & (1 << 3)) == 1 else "background:red")
        self.ui.btn_InStatus4.setStyleSheet("background:green" if (di & (1 << 4)) == 1 else "background:red")
        self.ui.btn_InStatus5.setStyleSheet("background:green" if (di & (1 << 5)) == 1 else "background:red")



    def show_delay(self):
        """
        从self.bus.cfg读取当前模式的延时配置并显示到tableWidget_2
        只有"延时"列可编辑，格式为浮点数，保留3位小数
        """
        if not self.current_mode:
            QMessageBox.warning(self, "警告", "请先选择模式！")
            return
        
        # 获取标签和延时配置
        labels_cfg = self.bus.cfg.get(f"{self.current_mode}_mode", "labels", default={})
        delay_cfg = self.bus.cfg.get(f"{self.current_mode}_mode", "delay", default={})
        
        if not labels_cfg:
            QMessageBox.information(self, "提示", "当前模式没有标签配置")
            return
        
        # 设置表格
        table = self.ui.tab_Delay
        table.clearContents()
        table.setRowCount(len(labels_cfg))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['名称', '延时'])
        
        # 填充数据
        for row, (key, value) in enumerate(labels_cfg.items()):
            # 名称列（只读）
            name_item = QTableWidgetItem(str(key))
            name_item.setFlags(Qt.ItemIsEnabled)
            table.setItem(row, 0, name_item)
            
            # 延时列（可编辑）
            delay_value = delay_cfg.get(key, 0.0)
            delay_item = QTableWidgetItem(f"{float(delay_value):.3f}")
            delay_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
            table.setItem(row, 1, delay_item)
        
        # 优化表格宽度（新增部分）
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)  # 最后一列拉伸填充
        table.setMinimumWidth(400)  # 设置表格最小宽度
        # 设置列最小宽度保证显示效果
        table.setColumnWidth(0, max(table.columnWidth(0), 150))  # 名称列至少150px
        table.setColumnWidth(1, max(table.columnWidth(1), 100))  # 延时列至少100px

    def set_delay(self):
        """
        从tableWidget_2读取用户编辑的延时数据并写入self.bus.cfg
        只读取"延时"列的浮点数值
        """
        if not self.current_mode:
            QMessageBox.warning(self, "警告", "请先选择模式！")
            return
        
        table = self.ui.tableWidget_2
        delay_dict = {}
        
        # 遍历所有行读取数据
        for row in range(table.rowCount()):
            try:
                # 获取名称（作为配置键）
                name_item = table.item(row, 0)
                if not name_item:
                    continue
                key = name_item.text()
                
                # 获取延时值
                delay_item = table.item(row, 1)
                if not delay_item:
                    delay_dict[key] = 0.0
                    continue
                
                # 解析并验证延时值
                delay_str = delay_item.text().strip()
                if not delay_str:
                    delay_dict[key] = 0.0
                else:
                    delay_value = float(delay_str)
                    delay_dict[key] = round(delay_value, 3)  # 保留3位小数
                    
            except ValueError:
                QMessageBox.warning(self, "格式错误", 
                    f"第 {row+1} 行的延时值不是有效的数字！")
                return
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取数据失败: {e}")
                return
        
        # 写入配置
        try:
            self.bus.cfg.set(f"{self.current_mode}_mode", "delay", value=delay_dict)
            QMessageBox.information(self, "成功", f"延时配置已保存！\n共保存 {len(delay_dict)} 条记录")
            print(f"【调试】保存延时配置: {delay_dict}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入配置文件时出错: {e}")