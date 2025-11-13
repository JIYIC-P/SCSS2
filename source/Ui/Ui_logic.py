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
        self.bus.do_push.connect(self.update_do_led)

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
        if not hsv_list or len(hsv_list) != 3:
            return QColor(128, 128, 128)
        h, s, v = hsv_list
        h = max(0, min(360, float(h)))
        s = max(0, min(255, float(s)))
        v = max(0, min(255, float(v)))
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
        existing_ids = []
        row_count = self.ui.tab_Color.rowCount()
        for row in range(row_count):
            item = self.ui.tab_Color.item(row, 0)
            if item:
                existing_ids.append(item.text())
        max_id = -1
        for id_str in existing_ids:
            try:
                max_id = max(max_id, int(id_str))
            except ValueError:
                pass
        return str(max_id + 1)

    def on_color_row_selected(self):
        selected_items = self.ui.tab_Color.selectedItems()
        if not selected_items:
            self.selected_color_id = None
            return
        row = selected_items[0].row()
        id_item = self.ui.tab_Color.item(row, 0)
        if id_item:
            self.selected_color_id = id_item.text()

    # ==================== 核心功能函数 ====================
    def show_colorange(self):
        self.ui.tab_Color.clearContents()
        color_labels = self.bus.cfg.get("color_mode", "labels", default={})
        if not color_labels:
            self.ui.tab_Color.setRowCount(0)
            return
        self.ui.tab_Color.setRowCount(len(color_labels))
        self.ui.tab_Color.setHorizontalHeaderLabels(["ID", "颜色预览", "Range"])
        self.ui.tab_Color.setColumnWidth(0, 50)
        self.ui.tab_Color.setColumnWidth(1, 80)
        self.ui.tab_Color.setColumnWidth(2, 100)
        for row, (label_id, data) in enumerate(color_labels.items()):
            hsv_values = data[0] if len(data) > 0 else [0, 0, 0]
            range_value = data[1] if len(data) > 1 else 5
            id_item = QTableWidgetItem(str(label_id))
            id_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.ui.tab_Color.setItem(row, 0, id_item)
            color = self.hsv_to_qcolor(hsv_values)
            color_item = QTableWidgetItem("")
            color_item.setBackground(color)
            color_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.ui.tab_Color.setItem(row, 1, color_item)
            range_item = QTableWidgetItem(str(range_value))
            range_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
            self.ui.tab_Color.setItem(row, 2, range_item)
        self.ui.tab_Color.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    def add_column(self):
        new_id = self.get_next_color_id()
        row = self.ui.tab_Color.rowCount()
        self.ui.tab_Color.insertRow(row)
        id_item = QTableWidgetItem(new_id)
        id_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.ui.tab_Color.setItem(row, 0, id_item)
        color_item = QTableWidgetItem("")
        color_item.setBackground(QColor(128, 128, 128))
        color_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.ui.tab_Color.setItem(row, 1, color_item)
        range_item = QTableWidgetItem("5")
        range_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
        self.ui.tab_Color.setItem(row, 2, range_item)
        self.ui.tab_Color.selectRow(row)

    def set_color(self):
        row_count = self.ui.tab_Color.rowCount()
        if row_count == 0:
            return
        color_labels = {}
        for row in range(row_count):
            id_item = self.ui.tab_Color.item(row, 0)
            if not id_item:
                continue
            label_id = id_item.text()
            range_item = self.ui.tab_Color.item(row, 2)
            if not range_item:
                continue
            try:
                range_value = int(range_item.text())
                range_value = max(0, min(25, range_value))
            except ValueError:
                range_value = 5
            hsv_values = [0, 0, 0]
            existing_data = self.bus.cfg.get("color_mode", "labels", label_id, default=None)
            if existing_data and isinstance(existing_data, list) and len(existing_data) > 0:
                hsv_values = existing_data[0]
            color_labels[label_id] = [hsv_values, range_value]
        self.bus.cfg.set("color_mode", "labels", value=color_labels)
        QMessageBox.information(self, "保存成功", "颜色标签配置已保存！")

    # ==================== 其它方法保持原样，未改动 ====================
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

            if self.current_mode == "color":
                self.colormode_init()
            
            self.worker_labels.clear()
            self.bus.mode_changed.emit(self.current_mode)
            self.bus.result.connect(self.update_result)
            self._update_worker_buttons()
            self._load_and_apply_worker_config(new_mode)
            self._emit_worker_labels()
            QMessageBox.information(
                self, 
                "模式切换成功", 
                f"已切换到 {mode_text} 模式\n剩余 {len(self.left_labels)} 个标签待分配"
            )

    def update_result(self, result: list):
        if self.current_mode == "color":
            self.ui.lab_ShowFrame0Txt.setText(f"\t\t主视角  ID:{result[0]}")
        elif self.current_mode in ("clip", "yolo"):
            self.ui.lab_ShowFrame0Txt.setText(f"\t\t主视角  ID:{result[0]}\tLabel:{result[1]}")

    def _convert_labels_for_display(self, raw_labels):
        display_data = []
        if not raw_labels:
            print("【调试】raw_labels为空")
            return display_data
        print(f"【调试】转换模式: {self.current_mode}, 原始数据类型: {type(raw_labels)}")
        if self.current_mode == "color":
            for key, value in raw_labels.items():
                try:
                    if isinstance(value, list) and len(value) >= 1:
                        hsv_array = value[0]
                        if isinstance(hsv_array, (list, np.ndarray)) and len(hsv_array) >= 3:
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
            for label_name, label_id in raw_labels.items():
                display_data.append({
                    "id": label_id,
                    "text": str(label_name)
                })
        print(f"【调试】转换后数据: {display_data}")
        return display_data

    def _load_and_apply_worker_config(self, mode):
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
        label_id_map = {str(label["id"]): label for label in self.left_labels}
        for i, label_ids in enumerate(worker_config):
            if not label_ids:
                continue
            worker_name = f"工位{i}"
            valid_labels = []
            missing_ids = []
            for label_id in label_ids:
                label_id_str = str(label_id)
                if label_id_str in label_id_map:
                    valid_labels.append(label_id_map[label_id_str])
                else:
                    missing_ids.append(label_id)
            if missing_ids:
                print(f"【警告】工位 {worker_name} 的标签ID不存在: {missing_ids}")
                QMessageBox.warning(
                    self, 
                    "标签缺失", 
                    f"工位 {worker_name} 的部分标签ID不存在: {missing_ids}\n请检查配置或标签数据！"
                )
            if valid_labels:
                self.worker_labels[worker_name] = valid_labels
                for label in valid_labels:
                    if label in self.left_labels:
                        self.left_labels.remove(label)
                print(f"【调试】工位 {worker_name} 自动分配 {len(valid_labels)} 个标签")
        self._update_worker_buttons()
        total_assigned = sum(len(labels) for labels in self.worker_labels.values())
        QMessageBox.information(
            self,
            "工位配置加载完成",
            f"已从配置加载并自动分配 {total_assigned} 个标签到各工位\n剩余可用标签: {len(self.left_labels)}"
        )

    def _create_choice_dialog(self, display_data, title="请选择对应的选项"):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        main_layout = QVBoxLayout()
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['ID', '预览/标签'])
        table.setSelectionMode(QAbstractItemView.MultiSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setRowCount(len(display_data))
        for row_idx, item in enumerate(display_data):
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
        btn_Box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_Box.accepted.connect(dialog.accept)
        btn_Box.rejected.connect(dialog.reject)
        def update_count():
            count = len(table.selectionModel().selectedRows())
            count_label.setText(f"已选中: {count}")
        table.itemSelectionChanged.connect(update_count)
        btn_Layout.addWidget(btn_Box)
        main_layout.addLayout(btn_Layout)
        main_layout.addWidget(table)
        main_layout.addWidget(btn_Box)
        dialog.setLayout(main_layout)
        dialog.setMinimumSize(400, 300)
        dialog.table_widget = table
        return dialog

    def _get_selected_ids(self, dialog):
        selected_ids = []
        table = getattr(dialog, 'table_widget', None)
        if table:
            for index in table.selectionModel().selectedRows():
                id_item = table.item(index.row(), 0)
                if id_item:
                    selected_ids.append(id_item.text())
        return selected_ids

    def _emit_worker_labels(self):
        worker_array = [[] for _ in range(5)]
        for i in range(5):
            worker_name = f"工位{i}"
            if worker_name in self.worker_labels:
                ids = [int(label["id"]) for label in self.worker_labels[worker_name]]
                worker_array[i] = ids
        self.bus.worker.emit(worker_array)
        print(f"【调试】发射工位标签信号: {worker_array}")

    def _update_worker_buttons(self):
        for worker_name, button in self.worker_buttons.items():
            assigned = self.worker_labels.get(worker_name, [])
            if assigned:
                button.setText(f"{worker_name} ({len(assigned)})")
            else:
                button.setText(worker_name)

    def _show_assigned_labels(self, worker_name):
        assigned = self.worker_labels.get(worker_name, [])
        if not assigned:
            return False
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{worker_name} - 已分配标签")
        layout = QVBoxLayout()
        label = QLabel(f"{worker_name} 已分配 {len(assigned)} 个标签：")
        layout.addWidget(label)
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
        btn_Box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_Box.button(QDialogButtonBox.Ok).setText("确定")
        btn_Box.button(QDialogButtonBox.Cancel).setText("取消选中并重新分配")
        btn_Box.accepted.connect(dialog.accept)
        btn_Box.rejected.connect(dialog.reject)
        layout.addWidget(table)
        layout.addWidget(btn_Box)
        dialog.setLayout(layout)
        dialog.setMinimumSize(400, 300)
        result = dialog.exec_()
        if result == QDialog.Rejected:
            selected_rows = table.selectionModel().selectedRows()
            if selected_rows:
                rows_to_remove = [index.row() for index in selected_rows]
                removed_labels = [assigned[i] for i in sorted(rows_to_remove, reverse=True)]
                for label in removed_labels:
                    assigned.remove(label)
                    self.left_labels.append(label)
                self._update_worker_buttons()
                self._emit_worker_labels()
                QMessageBox.information(
                    self, 
                    "取消成功", 
                    f"已从 {worker_name} 移除 {len(removed_labels)} 个标签\n剩余可用标签: {len(self.left_labels)}"
                )
                return True
        return False

    def setwoker(self):
        btn = self.sender()
        if not btn:
            return
        worker_name = btn.text().split(" ")[0]
        if not self.left_labels and worker_name not in self.worker_labels:
            QMessageBox.warning(self, "警告", "请先选择模式并加载标签数据！\n或所有标签已分配完毕！")
            return
        if worker_name in self.worker_labels:
            canceled = self._show_assigned_labels(worker_name)
            if canceled:
                pass
        if not self.left_labels:
            QMessageBox.information(self, "提示", "没有更多标签可供分配！")
            return
        dialog = self._create_choice_dialog(self.left_labels, f"为 {worker_name} 选择标签")
        result = dialog.exec_()
        if result == QDialog.Accepted:
            selected_ids = self._get_selected_ids(dialog)
            if selected_ids:
                selected_labels = []
                for label_id in selected_ids:
                    for label in self.left_labels:
                        if str(label["id"]) == label_id:
                            selected_labels.append(label)
                            break
                for label in selected_labels:
                    self.left_labels.remove(label)
                self.worker_labels[worker_name] = selected_labels
                self._update_worker_buttons()
                self._emit_worker_labels()
                QMessageBox.information(
                    self, 
                    "分配成功", 
                    f"工位 {worker_name} 已分配 {len(selected_labels)} 个标签\n剩余标签数: {len(self.left_labels)}"
                )
                if not self.left_labels:
                    QMessageBox.information(self, "提示", "所有标签已分配完毕！")
            else:
                QMessageBox.information(self, "提示", "未选择任何标签！")

    @pyqtSlot(int)
    def update_do_led(self, do):
        if do is None or not (0 <= do <= 4):
            self.current_pusher_do = None
            do = None

        self.ui.btn_PusherStatus0.setStyleSheet("background:green" if do == 0 else "background:red")
        self.ui.btn_PusherStatus1.setStyleSheet("background:green" if do == 1 else "background:red")
        self.ui.btn_PusherStatus2.setStyleSheet("background:green" if do == 2 else "background:red")
        self.ui.btn_PusherStatus3.setStyleSheet("background:green" if do == 3 else "background:red")
        self.ui.btn_PusherStatus4.setStyleSheet("background:green" if do == 4 else "background:red")

        if do is not None and 0 <= do <= 4:
            self.current_pusher_do = do
            self.pusher_timer.start(1500)
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

    def show_delay(self):
        if not self.current_mode:
            QMessageBox.warning(self, "警告", "请先选择模式！")
            return
        labels_cfg = self.bus.cfg.get(f"{self.current_mode}_mode", "labels", default={})
        delay_cfg = self.bus.cfg.get(f"{self.current_mode}_mode", "delay", default={})
        if not labels_cfg:
            QMessageBox.information(self, "提示", "当前模式没有标签配置")
            return
        table = self.ui.tab_Delay
        table.clearContents()
        table.setRowCount(len(labels_cfg))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['名称', '延时'])
        for row, (key, value) in enumerate(labels_cfg.items()):
            name_item = QTableWidgetItem(str(key))
            name_item.setFlags(Qt.ItemIsEnabled)
            table.setItem(row, 0, name_item)
            delay_item = QTableWidgetItem(f"{float(delay_cfg.get(key, 0.0)):.3f}")
            delay_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
            table.setItem(row, 1, delay_item)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumWidth(400)
        table.setColumnWidth(0, max(table.columnWidth(0), 150))
        table.setColumnWidth(1, max(table.columnWidth(1), 100))

    def set_delay(self):
        if not self.current_mode:
            QMessageBox.warning(self, "警告", "请先选择模式！")
            return
        table = self.ui.tableWidget_2
        delay_dict = {}
        for row in range(table.rowCount()):
            try:
                name_item = table.item(row, 0)
                if not name_item:
                    continue
                key = name_item.text()
                delay_item = table.item(row, 1)
                if not delay_item:
                    delay_dict[key] = 0.0
                    continue
                delay_str = delay_item.text().strip()
                if not delay_str:
                    delay_dict[key] = 0.0
                else:
                    delay_value = float(delay_str)
                    delay_dict[key] = round(delay_value, 3)
            except ValueError:
                QMessageBox.warning(self, "格式错误", f"第 {row+1} 行的延时值不是有效的数字！")
                return
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取数据失败: {e}")
                return
        try:
            self.bus.cfg.set(f"{self.current_mode}_mode", "delay", value=delay_dict)
            QMessageBox.information(self, "成功", f"延时配置已保存！\n共保存 {len(delay_dict)} 条记录")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入配置文件时出错: {e}")