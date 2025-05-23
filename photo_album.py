import os
import sys
import time
import random
import warnings
import json

# 抑制PyQt5的弃用警告
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QListWidget, QFileDialog, QCheckBox, 
                             QSpinBox, QGroupBox, QSlider, QComboBox, QFrame, QStyle, QMenu, QAction, QMessageBox)
from PyQt5.QtGui import QPixmap, QImage, QCursor, QFont, QColor, QPalette, QDragEnterEvent, QDropEvent
from PyQt5.QtCore import Qt, QTimer, QSize, QPoint, QMimeData, QSettings

# 定义应用程序常量
APP_NAME = "电子相册"
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".photo_album_settings.json")

# 支持的图片格式（PyQt5原生支持，无需额外插件）
SUPPORTED_FORMATS = (
    # 常见格式
    '.jpg', '.jpeg', '.png', '.bmp', '.gif',
    # 扩展格式（原生支持）
    '.webp', '.tiff', '.tif', '.ico', '.xpm',
    '.pbm', '.pgm', '.ppm', '.xbm', '.jfif'
)

class ImageViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图片查看")
        # 修改窗口标志，移除标题栏并在任务栏中隐藏
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.resize(800, 600)
        self.is_dragging = False
        self.drag_start_position = QPoint()
        self.main_window = None  # 保存主窗口引用
        
        # 全屏相关变量
        self.is_fullscreen = False
        self.pre_fullscreen_geometry = None
        self.fullscreen_button_visible = False
        
        # 创建图片标签
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        self.image_label.setMinimumSize(1, 1)  # 设置最小尺寸为1x1
        layout.addWidget(self.image_label)
        
        # 创建全屏按钮
        self.fullscreen_button = QPushButton(self)
        self.fullscreen_button.setIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.fullscreen_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 150);
                border: none;
                border-radius: 15px;
                color: white;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 200);
            }
        """)
        self.fullscreen_button.setFixedSize(30, 30)
        self.fullscreen_button.setCursor(Qt.PointingHandCursor)
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_button.hide()  # 默认隐藏按钮
        
        # 创建打开文件夹按钮
        self.folder_button = QPushButton(self)
        self.folder_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.folder_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(40, 120, 200, 150);
                border: none;
                border-radius: 15px;
                color: white;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(40, 120, 200, 200);
            }
        """)
        self.folder_button.setFixedSize(30, 30)
        self.folder_button.setCursor(Qt.PointingHandCursor)
        self.folder_button.clicked.connect(self.open_image_folder)
        self.folder_button.hide()  # 默认隐藏按钮
        
        # 初始化大小调整标志
        self.resizing = False
        self.resize_start_pos = QPoint()
        self.resize_start_size = QSize()
        
        # 设置鼠标追踪
        self.setMouseTracking(True)
        self.image_label.setMouseTracking(True)
        
        # 添加右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def toggle_fullscreen(self):
        """切换全屏状态"""
        if not self.is_fullscreen:
            # 保存当前窗口位置和大小
            self.pre_fullscreen_geometry = self.geometry()
            
            # 进入全屏模式
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            self.showFullScreen()
            self.is_fullscreen = True
            
            # 更新按钮图标
            self.fullscreen_button.setIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarNormalButton))
        else:
            # 退出全屏模式
            self.exit_fullscreen()
    
    def exit_fullscreen(self):
        """退出全屏模式"""
        if self.is_fullscreen:
            # 恢复工具窗口标志
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
            if self.main_window and self.main_window.always_on_top.isChecked():
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            
            self.show()  # 需要重新显示窗口以应用标志更改
            
            # 恢复全屏前的位置和大小
            if self.pre_fullscreen_geometry:
                self.setGeometry(self.pre_fullscreen_geometry)
            
            self.is_fullscreen = False
            
            # 更新按钮图标
            self.fullscreen_button.setIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarMaxButton))
    
    def set_main_window(self, window):
        """设置主窗口引用"""
        self.main_window = window
    
    def show_context_menu(self, pos):
        """显示右键菜单"""
        if self.main_window:
            # 暂停播放
            if self.main_window.slideshow_active:
                self.main_window.toggle_slideshow()
            self.main_window.show()
    
    def display_image(self, pixmap):
        # 调整图片大小以适应标签，保持纵横比
        scaled_pixmap = pixmap.scaled(self.image_label.size(), 
                                      Qt.KeepAspectRatio, 
                                      Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        # 窗口大小改变时保存大小并重新显示当前图片
        if hasattr(self, 'current_pixmap'):
            self.display_image(self.current_pixmap)
        if self.main_window:
            self.main_window.save_settings()
            
        # 更新全屏按钮位置
        self.update_fullscreen_button_position()
            
        super().resizeEvent(event)
    
    def update_fullscreen_button_position(self):
        """更新按钮位置"""
        # 放在窗口右上角
        self.fullscreen_button.move(self.width() - self.fullscreen_button.width() - 10, 10)
        
        # 更新文件夹按钮位置 (左上角)
        self.folder_button.move(10, 10)
    
    def enterEvent(self, event):
        """鼠标进入窗口事件"""
        # 显示按钮
        self.fullscreen_button.show()
        self.folder_button.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开窗口事件"""
        # 隐藏按钮，除非鼠标正在按钮上
        if not (self.fullscreen_button.underMouse() or self.folder_button.underMouse()):
            self.fullscreen_button.hide()
            self.folder_button.hide()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 点击右下角区域，开始调整大小
            if self.is_resize_area(event.pos()):
                self.resizing = True
                self.resize_start_pos = event.globalPos()
                self.resize_start_size = self.size()
            else:
                # 若当前已全屏，不执行拖动操作
                if self.is_fullscreen:
                    event.accept()
                    return
                # 开始拖动
                self.is_dragging = True
                self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        # 调整鼠标样式
        if self.is_resize_area(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            
        if self.resizing:
            # 计算新的大小
            delta = event.globalPos() - self.resize_start_pos
            new_width = max(100, self.resize_start_size.width() + delta.x())  # 最小宽度设为100
            new_height = max(100, self.resize_start_size.height() + delta.y())  # 最小高度设为100
            self.resize(new_width, new_height)
        elif self.is_dragging:
            # 移动窗口
            self.move(event.globalPos() - self.drag_start_position)
        
        event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.resizing = False
        event.accept()
    
    def mouseDoubleClickEvent(self, event):
        # 双击切换全屏模式
        self.toggle_fullscreen()
        event.accept()
    
    def is_resize_area(self, pos):
        # 定义右下角的调整大小区域(20x20像素)
        width = self.width()
        height = self.height()
        bottom_right = QPoint(width, height)
        return (bottom_right - pos).manhattanLength() < 20
        
    def keyPressEvent(self, event):
        # ESC键处理
        if event.key() == Qt.Key_Escape:
            if self.is_fullscreen:
                # 如果当前是全屏状态，退出全屏
                self.exit_fullscreen()
            else:
                # 否则隐藏窗口
                self.hide()
                # 确保主窗口显示
                if self.main_window:
                    # 暂停播放
                    if self.main_window.slideshow_active:
                        self.main_window.toggle_slideshow()
                    self.main_window.show()
        event.accept()
    
    def closeEvent(self, event):
        # 窗口关闭时确保主窗口显示
        if self.main_window:
            # 暂停播放
            if self.main_window.slideshow_active:
                self.main_window.toggle_slideshow()
            self.main_window.show()
        event.accept()
    
    def moveEvent(self, event):
        # 窗口移动时保存位置
        if self.main_window:
            self.main_window.save_settings()
        super().moveEvent(event)
    
    def open_image_folder(self):
        """打开当前图片所在的文件夹"""
        if not self.main_window or not hasattr(self.main_window, 'images') or not self.main_window.images:
            return
            
        # 获取当前图片路径
        current_image = self.main_window.images[self.main_window.current_image_index]
        
        # 获取图片所在的文件夹并规范化路径
        folder_path = os.path.dirname(os.path.abspath(current_image))
        image_file = os.path.basename(current_image)
        
        try:
            # 在Windows中使用explorer打开文件夹并选中文件
            import subprocess
            if sys.platform == 'win32':
                # 使用双引号包裹路径，处理路径中可能包含的空格
                # 注意: 需要将反斜杠转义
                current_image_path = current_image.replace('/', '\\')
                
                # 直接打印调试信息
                print(f"打开文件: {current_image_path}")
                
                # 使用explorer打开并选中文件
                try:
                    # 方法1: 使用/select参数
                    subprocess.Popen(f'explorer /select,"{current_image_path}"', shell=True)
                except Exception as e1:
                    print(f"方法1失败: {e1}")
                    try:
                        # 方法2: 先打开文件夹，不选中文件
                        subprocess.Popen(f'explorer "{folder_path}"', shell=True)
                    except Exception as e2:
                        print(f"方法2失败: {e2}")
                        # 方法3: 使用os.startfile直接打开文件夹
                        os.startfile(folder_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', folder_path])
            else:  # Linux等其他平台
                subprocess.Popen(['xdg-open', folder_path])
                
        except Exception as e:
            # 显示错误信息
            QMessageBox.critical(self, "打开失败", f"无法打开文件夹: {str(e)}\n路径: {folder_path}")

class DropArea(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(240, 240, 240, 100);
                border: 2px dashed #cccccc;
                border-radius: 10px;
            }
            QFrame:hover {
                background-color: rgba(230, 230, 230, 100);
                border: 2px dashed #999999;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # 添加图标和文字
        icon_label = QLabel()
        icon_label.setPixmap(QApplication.style().standardIcon(QStyle.SP_DirIcon).pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        
        text_label = QLabel("拖放文件夹到这里\n或点击选择文件夹")
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("color: #666666; font-size: 14px;")
        
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            folder_path = url.toLocalFile()
            if os.path.isdir(folder_path):
                self.parent().add_folder(folder_path)

class PhotoAlbum(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 700)
        self.folders = []
        self.images = []
        self.current_image_index = 0
        self.slideshow_active = False
        self.play_order = "顺序播放"  # 默认播放顺序
        
        # 创建独立图片查看器
        self.image_viewer = ImageViewer()
        self.image_viewer.set_main_window(self)
        
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QSpinBox {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        self.init_ui()
        
        # 加载保存的设置
        self.load_settings()
    
    def init_ui(self):
        # 创建主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(300)
        
        # 添加拖放区域
        self.drop_area = DropArea()
        self.drop_area.mousePressEvent = self.select_folders
        left_layout.addWidget(self.drop_area)
        
        # 文件夹列表
        self.folder_list = QListWidget()
        self.folder_list.setContextMenuPolicy(Qt.CustomContextMenu)  # 设置自定义右键菜单
        self.folder_list.customContextMenuRequested.connect(self.show_folder_context_menu)  # 连接右键菜单信号
        self.folder_list.setStyleSheet("""
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
            }
        """)
        left_layout.addWidget(QLabel("已选择的文件夹:"))
        left_layout.addWidget(self.folder_list)
        
        # 包含子文件夹选项
        self.include_subfolders = QCheckBox("包含子文件夹")
        self.include_subfolders.setChecked(True)  # 默认选中
        self.include_subfolders.stateChanged.connect(self.reload_images)
        left_layout.addWidget(self.include_subfolders)
        
        # 创建控制组
        control_group = QGroupBox("播放控制")
        control_layout = QVBoxLayout()
        
        # 播放顺序设置
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("播放顺序:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems(["顺序播放", "随机播放", "倒序播放"])
        self.order_combo.currentTextChanged.connect(self.change_play_order)
        order_layout.addWidget(self.order_combo)
        control_layout.addLayout(order_layout)
        
        # 播放/暂停按钮
        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self.toggle_slideshow)
        control_layout.addWidget(self.play_btn)
        
        # 间隔时间设置
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("切换间隔(秒):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(5)
        interval_layout.addWidget(self.interval_spin)
        control_layout.addLayout(interval_layout)
        
        # 窗口置顶选项
        self.always_on_top = QCheckBox("窗口置顶")
        self.always_on_top.stateChanged.connect(self.toggle_always_on_top)
        control_layout.addWidget(self.always_on_top)
        
        # 独立窗口播放选项
        self.use_viewer_window = QCheckBox("独立窗口播放")
        self.use_viewer_window.setChecked(True)
        control_layout.addWidget(self.use_viewer_window)
        
        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)
        
        # 添加按钮区域
        btn_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一张")
        self.prev_btn.clicked.connect(self.show_prev_image)
        self.next_btn = QPushButton("下一张")
        self.next_btn.clicked.connect(self.show_next_image)
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.next_btn)
        
        left_layout.addLayout(btn_layout)
        left_layout.addStretch()
        
        # 右侧图片显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2c2c2c;
                border-radius: 4px;
            }
        """)
        self.image_label.setMinimumSize(1, 1)
        
        # 将左右两个面板添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.image_label, 1)
        
        # 设置计时器用于幻灯片播放
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_next_image)

    def add_folder(self, folder_path):
        """添加文件夹到列表"""
        if folder_path not in self.folders:
            self.folders.append(folder_path)
            self.folder_list.addItem(folder_path)
            self.load_images()
            self.show_current_image()
            # 保存设置
            self.save_settings()

    def select_folders(self, event=None):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        # 使用Windows 11风格的文件选择器
        dialog.setOption(QFileDialog.DontUseNativeDialog, False)  # 使用系统原生对话框
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.ReadOnly, True)
        dialog.setOption(QFileDialog.HideNameFilterDetails, True)
        dialog.setOption(QFileDialog.DontResolveSymlinks, True)
        
        # 设置对话框标题
        dialog.setWindowTitle("选择文件夹")
        
        # 设置初始目录（可选）
        if self.folders:
            dialog.setDirectory(self.folders[-1])
        
        if dialog.exec_():
            selected_folders = dialog.selectedFiles()
            for folder in selected_folders:
                self.add_folder(folder)

    def load_images(self):
        """加载所有图片"""
        self.images = []
        for folder in self.folders:
            if self.include_subfolders.isChecked():
                # 递归加载子文件夹中的图片
                for root, _, files in os.walk(folder):
                    for file in files:
                        if file.lower().endswith(SUPPORTED_FORMATS):
                            self.images.append(os.path.join(root, file))
            else:
                # 只加载当前文件夹中的图片，不包括子文件夹
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    if os.path.isfile(file_path) and file.lower().endswith(SUPPORTED_FORMATS):
                        self.images.append(file_path)
        
        if self.images:
            self.current_image_index = 0
            self.show_current_image()
            
    def show_current_image(self):
        if not self.images:
            return
        
        try:
            image_path = self.images[self.current_image_index]
            pixmap = QPixmap(image_path)
            
            # 根据模式选择显示位置
            if self.slideshow_active and self.use_viewer_window.isChecked():
                # 在独立窗口中显示
                self.image_viewer.current_pixmap = pixmap  # 保存当前图片
                self.image_viewer.display_image(pixmap)
                if not self.image_viewer.isVisible():
                    self.image_viewer.show()
                
                # 隐藏主窗口
                if self.isVisible():
                    self.hide()
                
                # 更新窗口标题
                self.image_viewer.setWindowTitle(f"电子相册 - {os.path.basename(image_path)}")
            else:
                # 调整图片大小以适应标签，保持纵横比
                scaled_pixmap = pixmap.scaled(self.image_label.size(), 
                                       Qt.KeepAspectRatio, 
                                       Qt.SmoothTransformation)
                
                self.image_label.setPixmap(scaled_pixmap)
                self.setWindowTitle(f"电子相册 - {os.path.basename(image_path)}")
                
                # 隐藏独立窗口
                if self.image_viewer.isVisible():
                    self.image_viewer.hide()
                
        except Exception as e:
            print(f"显示图片时出错: {e}")
    
    def show_next_image(self):
        if not self.images:
            return
            
        if self.play_order == "顺序播放":
            self.current_image_index = (self.current_image_index + 1) % len(self.images)
        elif self.play_order == "随机播放":
            self.current_image_index = random.randint(0, len(self.images) - 1)
        elif self.play_order == "倒序播放":
            self.current_image_index = (self.current_image_index - 1) % len(self.images)
            
        self.show_current_image()
    
    def show_prev_image(self):
        if not self.images:
            return
            
        if self.play_order == "顺序播放":
            self.current_image_index = (self.current_image_index - 1) % len(self.images)
        elif self.play_order == "随机播放":
            self.current_image_index = random.randint(0, len(self.images) - 1)
        elif self.play_order == "倒序播放":
            self.current_image_index = (self.current_image_index + 1) % len(self.images)
            
        self.show_current_image()
    
    def toggle_slideshow(self):
        if self.slideshow_active:
            self.timer.stop()
            self.slideshow_active = False
            self.play_btn.setText("播放")
            
            # 隐藏独立窗口
            if self.image_viewer.isVisible():
                self.image_viewer.hide()
                
            # 恢复在主窗口中显示
            self.show()
            self.show_current_image()
        else:
            interval = self.interval_spin.value() * 1000  # 转换为毫秒
            self.timer.start(interval)
            self.slideshow_active = True
            self.play_btn.setText("暂停")
            
            # 如果选择了独立窗口模式，立即显示独立窗口并隐藏主窗口
            if self.use_viewer_window.isChecked():
                self.show_current_image()
    
    def toggle_always_on_top(self, state):
        # 设置主窗口置顶
        if state == Qt.Checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            # 图片查看器也置顶，保持工具窗口属性
            self.image_viewer.setWindowFlags(self.image_viewer.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            # 图片查看器不置顶，保持工具窗口属性
            self.image_viewer.setWindowFlags((self.image_viewer.windowFlags() & ~Qt.WindowStaysOnTopHint) | Qt.Tool)
        
        # 需要重新显示窗口以应用新标志
        self.show()
        
        # 如果图片查看器是可见的，也需要重新显示
        if self.image_viewer.isVisible():
            self.image_viewer.show()
            
        # 保存设置
        self.save_settings()
    
    def resizeEvent(self, event):
        # 窗口大小改变时重新显示当前图片以适应新尺寸
        self.show_current_image()
        super().resizeEvent(event)
    
    def closeEvent(self, event):
        # 保存设置
        self.save_settings()
        
        # 关闭主窗口时也关闭图片查看器
        self.image_viewer.close()
        super().closeEvent(event)
    
    def change_play_order(self, order):
        """更改播放顺序"""
        self.play_order = order
        # 保存设置
        self.save_settings()
        if self.slideshow_active:
            # 如果正在播放，重新开始播放以应用新的顺序
            self.toggle_slideshow()
            self.toggle_slideshow()

    def reload_images(self):
        """重新加载图片（当设置改变时）"""
        # 记住当前播放状态
        was_playing = self.slideshow_active
        
        # 如果正在播放，先暂停
        if was_playing:
            self.toggle_slideshow()
            
        # 重新加载图片
        self.load_images()
        
        # 如果之前在播放，恢复播放
        if was_playing:
            self.toggle_slideshow()
            
        # 保存设置
        self.save_settings()

    def load_settings(self):
        """加载应用程序设置"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                    # 加载文件夹
                    folders = settings.get('folders', [])
                    for folder in folders:
                        if os.path.exists(folder) and folder not in self.folders:
                            self.folders.append(folder)
                            self.folder_list.addItem(folder)
                    
                    # 加载播放顺序
                    play_order = settings.get('play_order', '顺序播放')
                    if play_order in ["顺序播放", "随机播放", "倒序播放"]:
                        self.play_order = play_order
                        index = self.order_combo.findText(play_order)
                        if index >= 0:
                            self.order_combo.setCurrentIndex(index)
                    
                    # 加载窗口置顶状态
                    always_on_top = settings.get('always_on_top', False)
                    self.always_on_top.setChecked(always_on_top)
                    
                    # 加载独立窗口播放设置
                    use_viewer = settings.get('use_viewer_window', True)
                    self.use_viewer_window.setChecked(use_viewer)
                    
                    # 加载切换间隔
                    interval = settings.get('interval', 5)
                    self.interval_spin.setValue(interval)
                    
                    # 加载子文件夹包含设置
                    include_subfolders = settings.get('include_subfolders', True)
                    self.include_subfolders.setChecked(include_subfolders)
                    
                    # 加载独立窗口位置和大小
                    viewer_geometry = settings.get('viewer_geometry', {})
                    if viewer_geometry:
                        self.image_viewer.resize(
                            viewer_geometry.get('width', 800),
                            viewer_geometry.get('height', 600)
                        )
                        self.image_viewer.move(
                            viewer_geometry.get('x', 100),
                            viewer_geometry.get('y', 100)
                        )
                
                # 如果有文件夹，加载图片
                if self.folders:
                    self.load_images()
                    
        except Exception as e:
            print(f"加载设置时出错: {e}")
    
    def save_settings(self):
        """保存应用程序设置"""
        try:
            settings = {
                'folders': self.folders,
                'play_order': self.play_order,
                'always_on_top': self.always_on_top.isChecked(),
                'use_viewer_window': self.use_viewer_window.isChecked(),
                'interval': self.interval_spin.value(),
                'include_subfolders': self.include_subfolders.isChecked(),
                'viewer_geometry': {
                    'x': self.image_viewer.x(),
                    'y': self.image_viewer.y(),
                    'width': self.image_viewer.width(),
                    'height': self.image_viewer.height()
                }
            }
            
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存设置时出错: {e}")

    def show_folder_context_menu(self, position):
        """显示文件夹列表的右键菜单"""
        # 创建右键菜单
        menu = QMenu()
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_selected_folder)
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(self.folder_list.mapToGlobal(position))
    
    def delete_selected_folder(self):
        """删除选中的文件夹"""
        # 获取选中的文件夹
        selected_items = self.folder_list.selectedItems()
        if not selected_items:
            return
            
        # 删除选中的文件夹
        for item in selected_items:
            folder_path = item.text()
            # 从folders列表中删除
            if folder_path in self.folders:
                self.folders.remove(folder_path)
            
            # 从列表控件中删除
            row = self.folder_list.row(item)
            self.folder_list.takeItem(row)
        
        # 重新加载图片
        self.load_images()
        self.current_image_index = 0
        
        # 如果还有图片，显示第一张；否则清空显示
        if self.images:
            self.show_current_image()
        else:
            # 清空图片显示
            self.image_label.clear()
            self.setWindowTitle(APP_NAME)
            
            # 如果独立窗口是可见的，也清空它并隐藏
            if self.image_viewer.isVisible():
                self.image_viewer.image_label.clear()
                self.image_viewer.hide()
        
        # 保存设置
        self.save_settings()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhotoAlbum()
    window.show()
    sys.exit(app.exec_()) 