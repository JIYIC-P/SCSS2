from PyQt5.QtCore import pyqtSlot, Qt, pyqtSignal
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
        
        ## 两个画面
        self.bus.camera0_img.connect(self.update_mianframe)
        self.bus.camera1_img.connect(self.update_secondframe)

        ## 延时配置
        self.ui.btn_SetDelay.clicked.connect(self.set_delay)
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
            cfg_key = f"{new_mode}_mode"
            self.lables = self.bus.cfg.get(cfg_key, "labels")
            self.show_delay()
            if self.lables is None:
                QMessageBox.warning(self, "警告", 
                    f"无法加载 {mode_text} 模式的标签配置！\n配置键: {cfg_key}")
                return
                
            print(f"【调试】成功加载标签数据: {type(self.lables)}, 数量: {len(self.lables)}")
            
            # 保存原始标签用于重置
            self.original_labels = self.lables.copy()
            # 转换数据格式
            self.left_labels = self._convert_labels_for_display(self.lables)
            # 重置工位分配
            self.worker_labels.clear()
            self.bus.mode_changed.emit(self.current_mode)
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
        for i in range(5):
            self.leds[i].setStyleSheet("background:red" if do & (1 << i) else "background:gray")

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
