import sys
import json
import os
import subprocess
import random
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QMenu, QVBoxLayout, QLabel,
    QFileDialog, QMessageBox, QDialog, QPushButton,
    QHBoxLayout, QFrame, QInputDialog, QCheckBox, QGroupBox,
    QRadioButton, QButtonGroup, QComboBox
)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QPixmap, QAction

# ====================== 配置管理（扩展） ======================
class ConfigManager:
    CONFIG_FILE = Path(os.environ.get('APPDATA', '.')) / 'ClassSun' / 'config.json'
    
    @classmethod
    def ensure_dir(cls):
        cls.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load(cls):
        cls.ensure_dir()
        default = {
            'classsoon_path': 'Soon.exe',
            'use_icc': False,
            'desktop_annotation_path': 'DesktopAnnotation.exe',
            'desktop_timer_path': 'DesktopTimer.exe',
            'auto_start': True,
            'disable_xiwo': False,
            'icc_or_zhihui': 'ICC-CE',
            'zhihui_path': 'ZhiHuiJiao.exe'
        }
        if cls.CONFIG_FILE.exists():
            try:
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    if 'use_icc' in saved and 'disable_xiwo' not in saved:
                        saved['disable_xiwo'] = saved['use_icc']
                        saved['icc_or_zhihui'] = 'ICC-CE' if saved['use_icc'] else '智绘教'
                    default.update(saved)
            except:
                pass
        return default
    
    @classmethod
    def save(cls, config):
        cls.ensure_dir()
        with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)


# ====================== 设置窗口（增强版） ======================
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager.load()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setFixedSize(500, 420)
        self.setWindowTitle("ClassSun 设置")
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        self.auto_start_cb = QCheckBox("开机自启动")
        self.auto_start_cb.setChecked(self.config.get('auto_start', True))
        layout.addWidget(self.auto_start_cb)
        
        group = QGroupBox("屏幕批注方案")
        group_layout = QVBoxLayout()
        
        self.disable_xiwo_cb = QCheckBox("不使用希沃批注")
        self.disable_xiwo_cb.setChecked(self.config.get('disable_xiwo', False))
        self.disable_xiwo_cb.toggled.connect(self.on_disable_xiwo_toggled)
        group_layout.addWidget(self.disable_xiwo_cb)
        
        self.sub_widget = QWidget()
        sub_layout = QVBoxLayout(self.sub_widget)
        sub_layout.setContentsMargins(20, 0, 0, 0)
        
        self.icc_radio = QRadioButton("使用 InkCanvasForClassCe (ICC-CE)")
        self.zhihui_radio = QRadioButton("使用智绘教")
        
        self.software_group = QButtonGroup(self)
        self.software_group.addButton(self.icc_radio)
        self.software_group.addButton(self.zhihui_radio)
        
        zhihui_path_layout = QHBoxLayout()
        self.zhihui_path_edit = QComboBox()
        self.zhihui_path_edit.setEditable(True)
        self.zhihui_path_edit.setMinimumWidth(250)
        zhihui_path_layout.addWidget(QLabel("智绘教路径:"))
        zhihui_path_layout.addWidget(self.zhihui_path_edit)
        browse_zhihui_btn = QPushButton("浏览")
        browse_zhihui_btn.clicked.connect(self.browse_zhihui)
        zhihui_path_layout.addWidget(browse_zhihui_btn)
        
        sub_layout.addWidget(self.icc_radio)
        sub_layout.addWidget(self.zhihui_radio)
        sub_layout.addLayout(zhihui_path_layout)
        
        group_layout.addWidget(self.sub_widget)
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        tip = QLabel("提示：\n• ICC-CE 需要从官网安装协议支持\n• 智绘教请指定正确的 exe 路径\n• 若取消“不使用希沃批注”，则使用同目录下的 DesktopAnnotation.exe")
        tip.setStyleSheet("color: #95a5a6; font-size: 11px;")
        layout.addWidget(tip)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        saved_software = self.config.get('icc_or_zhihui', 'ICC-CE')
        if saved_software == 'ICC-CE':
            self.icc_radio.setChecked(True)
        else:
            self.zhihui_radio.setChecked(True)
        self.zhihui_path_edit.addItem(self.config.get('zhihui_path', 'ZhiHuiJiao.exe'))
        self.zhihui_path_edit.setCurrentText(self.config.get('zhihui_path', 'ZhiHuiJiao.exe'))
        
        self.on_disable_xiwo_toggled(self.disable_xiwo_cb.isChecked())
    
    def browse_zhihui(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择智绘教程序", "", "可执行文件 (*.exe)")
        if path:
            self.zhihui_path_edit.addItem(path)
            self.zhihui_path_edit.setCurrentText(path)
    
    def on_disable_xiwo_toggled(self, checked):
        self.sub_widget.setVisible(checked)
        self.sub_widget.updateGeometry()
        QApplication.processEvents()
    
    def save_settings(self):
        self.config['auto_start'] = self.auto_start_cb.isChecked()
        self.config['disable_xiwo'] = self.disable_xiwo_cb.isChecked()
        if self.icc_radio.isChecked():
            self.config['icc_or_zhihui'] = 'ICC-CE'
        else:
            self.config['icc_or_zhihui'] = '智绘教'
        self.config['zhihui_path'] = self.zhihui_path_edit.currentText()
        self.config['use_icc'] = (self.config['disable_xiwo'] and self.config['icc_or_zhihui'] == 'ICC-CE')
        
        ConfigManager.save(self.config)
        self._handle_auto_startup()
        
        QMessageBox.information(self, "提示", "设置已保存，部分改动需要重启程序生效")
        self.accept()
    
    def _handle_auto_startup(self):
        startup_lnk = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ClassSun.exe.lnk"))
        exe_path = Path(sys.argv[0]).resolve()
        
        if self.config['auto_start']:
            if startup_lnk.exists():
                return
            try:
                import pythoncom
                from win32com.client import Dispatch
                shell = Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(startup_lnk))
                shortcut.Targetpath = str(exe_path)
                shortcut.WorkingDirectory = str(exe_path.parent)
                shortcut.save()
            except ImportError:
                QMessageBox.warning(self, "提示", "缺少 pywin32 模块，无法创建开机启动项\n请安装: pip install pywin32")
            except Exception as e:
                print(f"创建快捷方式失败: {e}")
        else:
            if startup_lnk.exists():
                startup_lnk.unlink()


# ====================== 随机抽选 ======================
class RandomPickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("谷牌~随机抽选")
        self.setFixedSize(500, 450)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setWindowModality(Qt.ApplicationModal)
        self.nameList = self.load_names()
        self.roll_timer = QTimer()
        self.roll_timer.timeout.connect(self.roll_name)
        self.rolling = False
        self.init_ui()
    
    def load_names(self):
        names = []
        name_file = Path(sys.argv[0]).parent / "namelist.txt"
        if name_file.exists():
            try:
                with open(name_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        name = line.strip()
                        if name:
                            names.append(name)
            except:
                pass
        if not names:
            names = ["在", "存", "不", "件", "文", "Not Found Name Text"]
        return names
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("谷牌~随机抽选")
        title.setStyleSheet("font-size: 24px; font-weight: 500; border-bottom: 1px solid #e4e4e7; padding-bottom: 10px;")
        layout.addWidget(title)
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet("border: 1px solid #e2e2e6; background: #fefefe;")
        self.result_frame.setFixedHeight(150)
        result_layout = QVBoxLayout(self.result_frame)
        self.result_label = QLabel("来一发")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("font-size: 32px; font-weight: 500; color: #9ca3af;")
        result_layout.addWidget(self.result_label)
        layout.addWidget(self.result_frame)
        btn_layout = QHBoxLayout()
        self.draw_btn = QPushButton("抽一人")
        self.draw_btn.setFixedSize(120, 50)
        self.draw_btn.setStyleSheet("QPushButton { background: white; border: 1px solid #3b82f6; color: #1e40af; font-size: 14px; font-weight: 500; } QPushButton:hover { background: #eff6ff; }")
        self.draw_btn.clicked.connect(self.draw_one)
        self.roll_btn = QPushButton("快速切")
        self.roll_btn.setFixedSize(120, 50)
        self.roll_btn.setStyleSheet("QPushButton { background: white; border: 1px solid #f59e0b; color: #b45309; font-size: 14px; font-weight: 500; } QPushButton:hover { background: #fffbeb; }")
        self.roll_btn.clicked.connect(self.toggle_roll)
        btn_layout.addWidget(self.draw_btn, alignment=Qt.AlignCenter)
        btn_layout.addWidget(self.roll_btn, alignment=Qt.AlignCenter)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def draw_one(self):
        if not self.nameList:
            self.result_label.setText("无数据")
            return
        chosen = random.choice(self.nameList)
        self.result_label.setText(chosen)
        self.result_label.setStyleSheet("font-size: 32px; font-weight: 500; color: #1f2937;")
    
    def roll_name(self):
        if not self.nameList:
            return
        chosen = random.choice(self.nameList)
        self.result_label.setText(chosen)
        self.result_label.setStyleSheet("font-size: 32px; font-weight: 500; color: #f59e0b;")
    
    def toggle_roll(self):
        if self.rolling:
            self.roll_timer.stop()
            self.rolling = False
            self.roll_btn.setText("快速切")
            self.result_label.setStyleSheet("font-size: 32px; font-weight: 500; color: #1f2937;")
        else:
            if not self.nameList:
                QMessageBox.warning(self, "提示", "没有学生数据")
                return
            self.roll_timer.start(50)
            self.rolling = True
            self.roll_btn.setText("停！")


# ====================== ICC 协议检测 ======================
def check_icc_protocol():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "icc")
        winreg.CloseKey(key)
        return True
    except:
        return False

def prompt_install_icc(parent):
    reply = QMessageBox.question(
        parent,
        "安装 ICC-CE",
        "当前没有安装 ICC-CE（屏幕批注工具）\n\n是否前往官网下载安装？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes
    )
    if reply == QMessageBox.StandardButton.Yes:
        webbrowser.open("https://icc-ce.inkeys.top/")


# ====================== 小太阳主窗口 ======================
class SunWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager.load()
        self.drag_position = None
        self.center_point = None
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(60, 60)
        
        self.icon_label = QLabel(self)
        pixmap = QPixmap("sun.png")
        if pixmap.isNull():
            self.icon_label.setText("☀️")
            self.icon_label.setStyleSheet("font-size: 40px;")
        else:
            self.icon_label.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setGeometry(5, 5, 50, 50)
        
        self.init_menu()
        self.set_position()
    
    def init_menu(self):
        self.menu = QMenu(self)
        self.menu.setStyleSheet("""
            QMenu { background-color: #2c3e50; color: white; border-radius: 8px; padding: 5px; }
            QMenu::item { padding: 8px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #1abc9c; }
        """)
        
        # 批注子菜单
        self.annotation_menu = self.menu.addMenu("批注")
        self._build_annotation_menu()
        
        self.menu.addSeparator()
        
        timer_action = QAction("计时器", self)
        timer_action.triggered.connect(self.run_desktop_timer)
        self.menu.addAction(timer_action)
        
        self.menu.addSeparator()
        
        actions = [
            ("随机抽人", self.open_random_picker),
            ("课堂助手 ClassSoon(C)", self.class_assistant),
            ("设置", self.open_settings),
            ("退出", self.quit_with_password)
        ]
        for text, callback in actions:
            action = QAction(text, self)
            action.triggered.connect(callback)
            self.menu.addAction(action)
    
    def _build_annotation_menu(self):
        self.annotation_menu.clear()
        disable_xiwo = self.config.get('disable_xiwo', False)
        
        if not disable_xiwo:
            action = self.annotation_menu.addAction("启动批注")
            action.triggered.connect(self.run_desktop_annotation)
            return
        
        software = self.config.get('icc_or_zhihui', 'ICC-CE')
        if software == 'ICC-CE':
            if not check_icc_protocol():
                prompt_install_icc(self)
            tools = [
                ("笔", self.pen_tool),
                ("鼠标", self.mouse_tool),
                ("板擦(区域)", self.eraser_area),
                ("橡皮擦(笔画)", self.eraser_stroke),
            ]
            for name, func in tools:
                act = self.annotation_menu.addAction(name)
                act.triggered.connect(func)
            self.annotation_menu.addSeparator()
            modes = [
                ("折叠批注", self.fold_annotation),
                ("打开批注", self.unfold_annotation),
                ("切换状态", self.toggle_annotation),
            ]
            for name, func in modes:
                act = self.annotation_menu.addAction(name)
                act.triggered.connect(func)
            self.annotation_menu.addSeparator()
            others = [
                ("随机抽选(ICC)", self.random_pick),
                ("点名(ICC)", self.random_one),
                ("计时器(ICC)", self.timer_tool),
            ]
            for name, func in others:
                act = self.annotation_menu.addAction(name)
                act.triggered.connect(func)
        else:
            zhihui_path = self.config.get('zhihui_path', 'ZhiHuiJiao.exe')
            exe = Path(zhihui_path)
            if not exe.is_absolute():
                exe = Path(sys.argv[0]).parent / zhihui_path
            if not exe.exists():
                self.annotation_menu.addAction("智绘教(未安装)").setEnabled(False)
                QMessageBox.warning(self, "提示", f"智绘教程序未找到：{exe}\n请在设置中指定正确的路径")
            else:
                act = self.annotation_menu.addAction("启动智绘教")
                act.triggered.connect(lambda: subprocess.Popen([str(exe)]))
    
    def set_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.center_point = QPoint(screen.width() // 2, screen.height() // 2)
        x = screen.width() // 4 - self.width() // 2
        y = screen.height() * 3 // 4 - self.height() // 2
        self.move(x, y)
    
    def is_within_limit(self, pos):
        if self.center_point is None:
            return True
        window_center = QPoint(pos.x() + self.width() // 2, pos.y() + self.height() // 2)
        dx = window_center.x() - self.center_point.x()
        dy = window_center.y() - self.center_point.y()
        return (dx ** 2 + dy ** 2) ** 0.5 <= 200
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            icon_rect = self.icon_label.geometry()
            click_pos = event.position().toPoint()
            if icon_rect.contains(click_pos):
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
            else:
                self.menu.exec(self.mapToGlobal(click_pos))
    
    def mouseMoveEvent(self, event):
        if self.drag_position is not None:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            if self.is_within_limit(new_pos):
                self.move(new_pos)
    
    def mouseReleaseEvent(self, event):
        if self.drag_position is not None and event.button() == Qt.LeftButton:
            current_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            if self.drag_position == current_pos:
                self.menu.exec(self.mapToGlobal(event.position().toPoint()))
        self.drag_position = None
    
    # ---------- ICC 命令 ----------
    def _icc_command(self, uri):
        if not check_icc_protocol():
            prompt_install_icc(self)
            return
        subprocess.run(["cmd", "/c", "start", uri], shell=True)
    
    def pen_tool(self):        self._icc_command("icc://tool/pen")
    def mouse_tool(self):      self._icc_command("icc://tool/cursor")
    def eraser_area(self):     self._icc_command("icc://tool/eraser")
    def eraser_stroke(self):   self._icc_command("icc://tool/eraserbystrokes")
    def fold_annotation(self): self._icc_command("icc://fold")
    def unfold_annotation(self): self._icc_command("icc://unfold")
    def toggle_annotation(self): self._icc_command("icc://toggle")
    def random_one(self):      self._icc_command("icc://randone")
    def random_pick(self):     self._icc_command("icc://rand")
    def timer_tool(self):      self._icc_command("icc://timer")
    
    # ---------- 本地 exe ----------
    def run_desktop_annotation(self):
        exe_path = Path(sys.argv[0]).parent / self.config.get('desktop_annotation_path', 'DesktopAnnotation.exe')
        if exe_path.exists():
            subprocess.Popen([str(exe_path)])
        else:
            QMessageBox.warning(self, "提示", f"找不到批注程序\n{exe_path}")
    
    def run_desktop_timer(self):
        exe_path = Path(sys.argv[0]).parent / self.config.get('desktop_timer_path', 'DesktopTimer.exe')
        if exe_path.exists():
            subprocess.Popen([str(exe_path)])
        else:
            QMessageBox.warning(self, "提示", f"找不到计时器程序\n{exe_path}")
    
    # ---------- 其他功能 ----------
    def open_random_picker(self):
        dialog = RandomPickerDialog(self)
        dialog.exec()
    
    def class_assistant(self):
        exe_path = Path(sys.argv[0]).parent / self.config.get('classsoon_path', 'Soon.exe')
        if exe_path.exists():
            subprocess.Popen([str(exe_path)])
        else:
            QMessageBox.warning(self, "提示", f"找不到 Soon.exe\n{exe_path}")
    
    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.config = ConfigManager.load()
            self.init_menu()
    
    def quit_with_password(self):
        reply = QMessageBox.question(
            self, "确认退出", "确定要退出小太阳吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    sun = SunWidget()
    sun.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
