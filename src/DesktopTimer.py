import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel
)
from PySide6.QtCore import Qt, QTimer, QUrl, QSharedMemory, QPoint
from PySide6.QtGui import QFont, QPainter, QBrush, QColor, QMouseEvent
from PySide6.QtMultimedia import QSoundEffect

class PlayPauseButton(QPushButton):
    """播放/暂停按钮 (纯绘制矢量图形, 不使用Emoji)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = False
        self.setFixedSize(80, 80)
        self.setStyleSheet("border: none; background: transparent;")

    def set_playing(self, playing):
        self.is_playing = playing
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(39, 192, 109)))
        painter.drawEllipse(0, 0, self.width(), self.height())

        painter.setBrush(QBrush(Qt.white))
        if self.is_playing:
            rect_width = self.width() * 0.25
            rect_height = self.height() * 0.4
            x1 = self.width() * 0.3
            x2 = self.width() * 0.6
            y = self.height() * 0.3
            painter.drawRect(int(x1), int(y), int(rect_width), int(rect_height))
            painter.drawRect(int(x2), int(y), int(rect_width), int(rect_height))
        else:
            points = [
                QPoint(int(self.width() * 0.35), int(self.height() * 0.3)),
                QPoint(int(self.width() * 0.35), int(self.height() * 0.7)),
                QPoint(int(self.width() * 0.7), int(self.height() * 0.5))
            ]
            painter.drawPolygon(points)
        painter.end()

class TimerApp(QMainWindow):
    _shared_memory_key = "TimerApp_Single_9876"

    @classmethod
    def check_single_instance(cls):
        cls.shared_memory = QSharedMemory(cls._shared_memory_key)
        if cls.shared_memory.attach():
            return False
        if not cls.shared_memory.create(1):
            return False
        return True

    def __init__(self):
        super().__init__()
        # --- 计时状态 ---
        self.is_running = False
        self.current_mode = "countdown"
        self.countdown_set = 5 * 60
        self.countdown_remain = 5 * 60
        self.stopwatch_sec = 0

        # --- UI 状态标志位 ---
        self.is_fullscreen = False
        self.is_compact = False
        self.normal_geometry = None
        self.fullscreen_geometry = None
        self.drag_pos = None

        # --- 定时器 ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._enter_compact_mode)

        # --- 主窗口布局 ---
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("background-color: white;")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 30, 20, 30)
        main_layout.setSpacing(20)

        self.control_widgets = []

        # ----- 标题栏 -----
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet("background-color: transparent;")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_label = QLabel("计时器")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; font-size: 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #ff4444; color: white; }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        main_layout.addWidget(self.title_bar)
        self.control_widgets.append(self.title_bar)

        # ----- 模式切换按钮 -----
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(0)
        self.countdown_btn = QPushButton("倒计时")
        self.stopwatch_btn = QPushButton("计时器")
        for btn in (self.countdown_btn, self.stopwatch_btn):
            btn.setFixedSize(120, 40)
        self.countdown_btn.setStyleSheet("background-color: #27c06d; color: white; border: none; border-radius: 6px 0 0 6px; font-size: 16px;")
        self.stopwatch_btn.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; border-left: none; border-radius: 0 6px 6px 0; font-size: 16px;")
        self.countdown_btn.clicked.connect(lambda: self._switch_mode("countdown"))
        self.stopwatch_btn.clicked.connect(lambda: self._switch_mode("stopwatch"))
        mode_layout.addWidget(self.countdown_btn)
        mode_layout.addWidget(self.stopwatch_btn)
        main_layout.addLayout(mode_layout)
        main_layout.setAlignment(mode_layout, Qt.AlignCenter)
        self.control_widgets.extend([self.countdown_btn, self.stopwatch_btn])

        # ----- 时间显示区域 -----
        self.time_boxes = {}
        self.colons = []
        time_layout = QHBoxLayout()
        time_layout.setSpacing(5)

        hour_widget = self._create_time_unit("时")
        self.time_boxes["时"] = hour_widget
        time_layout.addWidget(hour_widget)

        colon1 = QLabel(":")
        colon1.setFont(QFont("Arial", 48))
        colon1.setStyleSheet("padding-bottom: 20px;")
        time_layout.addWidget(colon1)
        self.colons.append(colon1)

        minute_widget = self._create_time_unit("分")
        self.time_boxes["分"] = minute_widget
        time_layout.addWidget(minute_widget)

        colon2 = QLabel(":")
        colon2.setFont(QFont("Arial", 48))
        colon2.setStyleSheet("padding-bottom: 20px;")
        time_layout.addWidget(colon2)
        self.colons.append(colon2)

        second_widget = self._create_time_unit("秒")
        self.time_boxes["秒"] = second_widget
        time_layout.addWidget(second_widget)

        main_layout.addLayout(time_layout)

        # ----- 底部按钮栏 -----
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(40)

        self.fullscreen_btn = QPushButton("全屏")
        self.fullscreen_btn.setStyleSheet("font-size: 14px; color: #666; background: none; border: none;")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)

        self.play_btn = PlayPauseButton()
        self.play_btn.clicked.connect(self._toggle_timer)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setStyleSheet("font-size: 14px; color: #666; background: none; border: none;")
        self.reset_btn.clicked.connect(self._reset_timer)

        bottom_layout.addWidget(self.fullscreen_btn)
        bottom_layout.addWidget(self.play_btn, alignment=Qt.AlignCenter)
        bottom_layout.addWidget(self.reset_btn)
        main_layout.addLayout(bottom_layout)
        self.control_widgets.extend([self.fullscreen_btn, self.play_btn, self.reset_btn])

        # ----- 全屏退出按钮 -----
        self.exit_fullscreen_btn = QPushButton("退出全屏")
        self.exit_fullscreen_btn.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                color: white;
                background-color: rgba(0,0,0,0.7);
                border: 1px solid white;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: rgba(255,255,255,0.2); }
        """)
        self.exit_fullscreen_btn.setFixedSize(120, 40)
        self.exit_fullscreen_btn.hide()
        self.exit_fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        main_layout.addWidget(self.exit_fullscreen_btn, alignment=Qt.AlignBottom | Qt.AlignRight)

        # ----- 声音 -----
        self.sound = QSoundEffect()
        if os.path.exists("time.wav"):
            self.sound.setSource(QUrl.fromLocalFile(os.path.abspath("time.wav")))
            self.sound.setLoopCount(1)
            self.sound.setVolume(1.0)

        self._refresh_display()
        self._update_buttons_enabled()
        self.setFixedSize(600, 480)
        self._center_window()

        self.centralWidget().installEventFilter(self)
        for w in self.findChildren(QWidget):
            w.installEventFilter(self)

    # ------------------ 辅助函数 ------------------
    def _center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _create_time_unit(self, unit_name):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)

        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(40, 40)
        btn_plus.setStyleSheet("border: 1px solid #ccc; background: white; border-radius: 6px; font-size: 24px; font-weight: bold;")
        btn_plus.clicked.connect(lambda: self._adjust_time(unit_name, +1))

        num_label = QLabel("00")
        num_label.setAlignment(Qt.AlignCenter)
        num_label.setFont(QFont("Arial", 60))
        num_label.setMinimumWidth(90)

        btn_minus = QPushButton("-")
        btn_minus.setFixedSize(40, 40)
        btn_minus.setStyleSheet("border: 1px solid #ccc; background: white; border-radius: 6px; font-size: 24px; font-weight: bold;")
        btn_minus.clicked.connect(lambda: self._adjust_time(unit_name, -1))

        unit_label = QLabel(unit_name)
        unit_label.setAlignment(Qt.AlignCenter)
        unit_label.setStyleSheet("font-size: 14px; color: #444;")

        layout.addWidget(btn_plus, alignment=Qt.AlignCenter)
        layout.addWidget(num_label, alignment=Qt.AlignCenter)
        layout.addWidget(btn_minus, alignment=Qt.AlignCenter)
        layout.addWidget(unit_label, alignment=Qt.AlignCenter)

        widget.setLayout(layout)
        widget.btn_plus = btn_plus
        widget.btn_minus = btn_minus
        widget.num_label = num_label
        widget.unit_label = unit_label
        return widget

    def _adjust_time(self, unit, delta):
        if self.is_running:
            return
        current = int(self.time_boxes[unit].num_label.text())
        new = current + delta
        if unit == "时":
            new = max(0, min(99, new))
        else:
            new = max(0, min(59, new))
        self.time_boxes[unit].num_label.setText(f"{new:02d}")

        h = int(self.time_boxes["时"].num_label.text())
        m = int(self.time_boxes["分"].num_label.text())
        s = int(self.time_boxes["秒"].num_label.text())
        total = h * 3600 + m * 60 + s
        if self.current_mode == "countdown":
            self.countdown_set = total
            self.countdown_remain = total
        else:
            self.stopwatch_sec = total

    def _refresh_display(self):
        if self.current_mode == "countdown":
            secs = self.countdown_remain
        else:
            secs = self.stopwatch_sec
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        self.time_boxes["时"].num_label.setText(f"{h:02d}")
        self.time_boxes["分"].num_label.setText(f"{m:02d}")
        self.time_boxes["秒"].num_label.setText(f"{s:02d}")

        is_red = (self.current_mode == "countdown" and 0 < secs <= 10)
        for unit in ["时", "分", "秒"]:
            if is_red:
                self.time_boxes[unit].num_label.setStyleSheet("color: red;")
            else:
                self.time_boxes[unit].num_label.setStyleSheet("color: black;")

    def _update_buttons_enabled(self):
        enable = not self.is_running
        for unit in self.time_boxes.values():
            unit.btn_plus.setEnabled(enable)
            unit.btn_minus.setEnabled(enable)
        self.countdown_btn.setEnabled(enable)
        self.stopwatch_btn.setEnabled(enable)

    def _switch_mode(self, mode):
        if self.is_running or self.current_mode == mode:
            return
        if self.timer.isActive():
            self.timer.stop()
            self.is_running = False
            self.play_btn.set_playing(False)
        self.current_mode = mode
        if mode == "countdown":
            self.countdown_btn.setStyleSheet("background-color: #27c06d; color: white; border: none; border-radius: 6px 0 0 6px; font-size: 16px;")
            self.stopwatch_btn.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; border-left: none; border-radius: 0 6px 6px 0; font-size: 16px;")
        else:
            self.countdown_btn.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; border-right: none; border-radius: 6px 0 0 6px; font-size: 16px;")
            self.stopwatch_btn.setStyleSheet("background-color: #27c06d; color: white; border: none; border-radius: 0 6px 6px 0; font-size: 16px;")
        self._refresh_display()
        self._update_buttons_enabled()

    # ------------------ 核心计时 ------------------
    def _toggle_timer(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.play_btn.set_playing(False)
            self._update_buttons_enabled()
            self.idle_timer.stop()
            if self.is_compact:
                self._exit_compact_mode()
        else:
            if self.current_mode == "countdown" and self.countdown_remain <= 0:
                self.countdown_remain = self.countdown_set
                self._refresh_display()
            self.timer.start(1000)
            self.is_running = True
            self.play_btn.set_playing(True)
            self._update_buttons_enabled()
            if not self.is_fullscreen and not self.is_compact:
                self.idle_timer.start(3000)

    def _update_timer(self):
        if self.current_mode == "countdown":
            if self.countdown_remain > 0:
                self.countdown_remain -= 1
                self._refresh_display()
                if self.countdown_remain == 0:
                    self.timer.stop()
                    self.is_running = False
                    self.play_btn.set_playing(False)
                    self._update_buttons_enabled()
                    if self.sound.isLoaded() or os.path.exists("time.wav"):
                        self.sound.play()
                    if self.is_compact:
                        self._exit_compact_mode()
            else:
                if self.timer.isActive():
                    self.timer.stop()
                    self.is_running = False
                    self.play_btn.set_playing(False)
                    self._update_buttons_enabled()
        else:
            if self.stopwatch_sec < 359999:
                self.stopwatch_sec += 1
                self._refresh_display()
            else:
                if self.timer.isActive():
                    self.timer.stop()
                    self.is_running = False
                    self.play_btn.set_playing(False)
                    self._update_buttons_enabled()

    def _reset_timer(self):
        if self.timer.isActive():
            self.timer.stop()
        self.is_running = False
        self.play_btn.set_playing(False)
        if self.current_mode == "countdown":
            self.countdown_remain = self.countdown_set
            self._refresh_display()
        else:
            self.stopwatch_sec = 0
            self._refresh_display()
        self._update_buttons_enabled()
        if self.is_compact:
            self._exit_compact_mode()

    # ------------------ 紧凑模式（修复上下裁剪）------------------
    def _enter_compact_mode(self):
        if not self.is_running or self.is_fullscreen or self.is_compact:
            return
        self.normal_geometry = self.geometry()

        for w in self.control_widgets:
            w.hide()
        for unit in self.time_boxes.values():
            unit.btn_plus.hide()
            unit.btn_minus.hide()
            unit.unit_label.hide()

        # 设置紧凑模式字体和样式
        compact_font_size = 56
        for unit in ["时", "分", "秒"]:
            label = self.time_boxes[unit].num_label
            label.setFont(QFont("Arial", compact_font_size))
            label.setStyleSheet("color: black;")
            label.setMinimumHeight(70)   # 确保垂直空间足够
        for colon in self.colons:
            colon.setFont(QFont("Arial", compact_font_size))
            colon.setStyleSheet("padding-bottom: 0; color: black;")
            colon.setMinimumHeight(70)

        # 增加窗口高度到 150，并增加宽度到 520，确保完全显示
        self.setFixedWidth(520)
        self.setFixedHeight(150)
        # 移除中央布局的额外边距，让时间区域更宽松
        self.centralWidget().layout().setContentsMargins(10, 10, 10, 10)
        self.centralWidget().layout().activate()
        self.adjustSize()
        self.setFixedSize(self.size())

        self.is_compact = True
        self.idle_timer.stop()

    def _exit_compact_mode(self):
        if not self.is_compact or self.is_fullscreen:
            return
        for w in self.control_widgets:
            w.show()
        for unit in self.time_boxes.values():
            unit.btn_plus.show()
            unit.btn_minus.show()
            unit.unit_label.show()

        for unit in ["时", "分", "秒"]:
            label = self.time_boxes[unit].num_label
            label.setFont(QFont("Arial", 60))
            label.setStyleSheet("")
            label.setMinimumHeight(0)   # 恢复默认
        for colon in self.colons:
            colon.setFont(QFont("Arial", 48))
            colon.setStyleSheet("padding-bottom: 20px;")
            colon.setMinimumHeight(0)

        # 恢复边距
        self.centralWidget().layout().setContentsMargins(20, 30, 20, 30)
        if self.normal_geometry:
            self.setGeometry(self.normal_geometry)
            self.setFixedSize(self.normal_geometry.size())
        else:
            self.setFixedSize(600, 480)
        self.is_compact = False
        self._refresh_display()
        if self.is_running and not self.is_fullscreen:
            self.idle_timer.start(3000)

    # ------------------ 全屏模式 ------------------
    def _toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            if self.fullscreen_geometry:
                self.setGeometry(self.fullscreen_geometry)
                self.setFixedSize(self.fullscreen_geometry.size())
            self._exit_fullscreen_mode()
            self.fullscreen_btn.setText("全屏")
            self.is_fullscreen = False
            if self.is_compact:
                self._exit_compact_mode()
        else:
            self.fullscreen_geometry = self.geometry()
            self._enter_fullscreen_mode()
            self.showFullScreen()
            self.fullscreen_btn.setText("退出全屏")
            self.is_fullscreen = True

    def _enter_fullscreen_mode(self):
        for w in self.control_widgets:
            w.hide()
        for unit in self.time_boxes.values():
            unit.btn_plus.hide()
            unit.btn_minus.hide()
            unit.unit_label.hide()
        self.centralWidget().setStyleSheet("background-color: black;")
        for unit in ["时", "分", "秒"]:
            label = self.time_boxes[unit].num_label
            label.setFont(QFont("Arial", 120))
            label.setStyleSheet("color: white;")
            label.setMinimumWidth(160)
        for colon in self.colons:
            colon.setFont(QFont("Arial", 120))
            colon.setStyleSheet("padding-bottom: 0; color: white;")
        self.exit_fullscreen_btn.show()
        self.centralWidget().layout().activate()
        self.update()

    def _exit_fullscreen_mode(self):
        self.centralWidget().setStyleSheet("background-color: white;")
        for unit in ["时", "分", "秒"]:
            label = self.time_boxes[unit].num_label
            label.setFont(QFont("Arial", 60))
            label.setStyleSheet("")
            label.setMinimumWidth(90)
        for colon in self.colons:
            colon.setFont(QFont("Arial", 48))
            colon.setStyleSheet("padding-bottom: 20px;")
        for w in self.control_widgets:
            w.show()
        for unit in self.time_boxes.values():
            unit.btn_plus.show()
            unit.btn_minus.show()
            unit.unit_label.show()
        self.exit_fullscreen_btn.hide()
        self._refresh_display()
        self.centralWidget().layout().activate()
        self.update()

    # ------------------ 事件过滤器 ------------------
    def eventFilter(self, obj, event):
        if event.type() in (QMouseEvent.MouseMove, QMouseEvent.MouseButtonPress):
            if self.is_running and not self.is_fullscreen and not self.is_compact:
                self.idle_timer.start(3000)
            if self.is_compact and not self.is_running and not self.is_fullscreen:
                self._exit_compact_mode()
        return super().eventFilter(obj, event)

    # ------------------ 窗口拖动 ------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_compact:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
            elif self.title_bar.geometry().contains(event.pos()):
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            new_pos = event.globalPosition().toPoint() - self.drag_pos
            screen = QApplication.primaryScreen().availableGeometry()
            new_pos.setX(max(screen.left(), min(new_pos.x(), screen.right() - self.width())))
            new_pos.setY(max(screen.top(), min(new_pos.y(), screen.bottom() - self.height())))
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        super().mouseReleaseEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if not TimerApp.check_single_instance():
        print("程序已在运行。")
        sys.exit(0)
    window = TimerApp()
    window.show()
    sys.exit(app.exec())
