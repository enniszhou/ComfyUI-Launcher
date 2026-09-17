"""Main window with sidebar navigation and 5 pages."""
import sys
import os
import webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QLineEdit, QSpinBox, QCheckBox, QTextEdit,
    QGroupBox, QFileDialog, QMessageBox, QStackedWidget, QListWidget,
    QListWidgetItem, QScrollArea, QFrame, QSizePolicy, QSplitter,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from .settings import Settings
from .theme import get_stylesheet
from .gpu_detector import detect_gpu, get_gpu_type, get_torch_versions_for_gpu, GPUType
from .torch_manager import get_installed_torch
from .comfyui_runner import ComfyUIRunner
from .git_manager import (
    find_git, get_current_branch, get_current_commit, get_branches,
    get_tags, switch_branch, switch_tag, pull, fetch, get_log,
)
from .extension_manager import (
    list_extensions, install_extension, remove_extension,
    toggle_extension, update_extension,
)
from .mirror_manager import PIP_MIRRORS, HF_MIRRORS, set_pip_mirror, get_current_pip_mirror
from .patch_manager import PatchManager
from .workers import DetectWorker, PipWorker, GitWorker, ExtensionWorker


SIDEBAR_WIDTH = 180

NAV_ITEMS = [
    ("launch", "\u542f\u52a8"),
    ("environment", "\u73af\u5883"),
    ("extensions", "\u6269\u5c55"),
    ("settings", "\u8bbe\u7f6e"),
    ("log", "\u65e5\u5fd7"),
]


class SidebarButton(QPushButton):
    def __init__(self, page_id, text, parent=None):
        super().__init__(text, parent)
        self.page_id = page_id
        self.setCheckable(True)
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(False)

    def set_active(self, active: bool):
        self.setChecked(active)
        self._update_style(active)

    def _update_style(self, active: bool):
        if active:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    color: #89b4fa;
                    border: none;
                    border-left: 3px solid #89b4fa;
                    border-radius: 0;
                    padding-left: 14px;
                    text-align: left;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #a6adc8;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0;
                    padding-left: 14px;
                    text-align: left;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #181825;
                    color: #cdd6f4;
                }
            """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.runner = None
        self.gpu_info = {}
        self._workers = []
        self._log_buffer = []
        self._detect_python_exe = ""
        self._init_ui()
        self._apply_theme()
        self._load_settings_to_ui()
        self._auto_detect_gpu()

    def _init_ui(self):
        self.setWindowTitle("ComfyUI Launcher")
        self.setMinimumSize(900, 650)
        w = self.settings.get("window_width", 1100)
        h = self.settings.get("window_height", 750)
        self.resize(w, h)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self.sidebar.setStyleSheet("background-color: #181825;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(2)

        title_label = QLabel("ComfyUI")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "color: #89b4fa; font-size: 18px; font-weight: bold; padding: 16px 0 4px 0;"
        )
        sidebar_layout.addWidget(title_label)

        subtitle = QLabel("Launcher")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "color: #6c7086; font-size: 12px; padding: 0 0 16px 0;"
        )
        sidebar_layout.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #313244;")
        sidebar_layout.addWidget(sep)

        sidebar_layout.addSpacing(8)

        self.nav_buttons = {}
        for page_id, text in NAV_ITEMS:
            btn = SidebarButton(page_id, f"  {text}")
            btn.clicked.connect(lambda checked, pid=page_id: self._switch_page(pid))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[page_id] = btn

        sidebar_layout.addStretch()

        self.status_indicator = QLabel("\u25cf \u672a\u8fd0\u884c")
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_indicator.setStyleSheet(
            "color: #6c7086; font-size: 12px; padding: 12px;"
        )
        sidebar_layout.addWidget(self.status_indicator)

        main_layout.addWidget(self.sidebar)

        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)

        self.pages = {}
        self._create_launch_page()
        self._create_environment_page()
        self._create_extensions_page()
        self._create_settings_page()
        self._create_log_page()

        self._switch_page("launch")

    def _apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.settings.theme))

    def _switch_page(self, page_id: str):
        for pid, btn in self.nav_buttons.items():
            btn.set_active(pid == page_id)
        if page_id in self.pages:
            self.page_stack.setCurrentWidget(self.pages[page_id])

    # ── Launch Page ──────────────────────────────────────────────

    def _create_launch_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QLabel("\u542f\u52a8 ComfyUI")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)

        gpu_card = QGroupBox("GPU \u72b6\u6001")
        gpu_card_layout = QVBoxLayout(gpu_card)

        self.launch_gpu_label = QLabel("\u68c0\u6d4b\u4e2d...")
        self.launch_gpu_label.setStyleSheet("font-size: 13px;")
        gpu_card_layout.addWidget(self.launch_gpu_label)

        self.launch_torch_label = QLabel("")
        self.launch_torch_label.setStyleSheet("font-size: 13px; color: #a6adc8;")
        gpu_card_layout.addWidget(self.launch_torch_label)

        layout.addWidget(gpu_card)

        control_card = QGroupBox("\u542f\u52a8\u63a7\u5236")
        control_layout = QVBoxLayout(control_card)

        params_row = QHBoxLayout()
        params_row.addWidget(QLabel("\u7aef\u53e3:"))
        self.launch_port_spin = QSpinBox()
        self.launch_port_spin.setRange(1024, 65535)
        self.launch_port_spin.setValue(self.settings.port)
        self.launch_port_spin.valueChanged.connect(lambda v: self.settings.set("port", v))
        params_row.addWidget(self.launch_port_spin)

        self.launch_listen_check = QCheckBox("--listen")
        self.launch_listen_check.setChecked(self.settings.listen)
        self.launch_listen_check.toggled.connect(lambda v: self.settings.set("listen", v))
        params_row.addWidget(self.launch_listen_check)

        params_row.addWidget(QLabel("\u989d\u5916\u53c2\u6570:"))
        self.launch_extra_edit = QLineEdit()
        self.launch_extra_edit.setPlaceholderText("--highvram --cuda-device 0")
        self.launch_extra_edit.setText(self.settings.extra_args)
        self.launch_extra_edit.editingFinished.connect(
            lambda: self.settings.set("extra_args", self.launch_extra_edit.text())
        )
        params_row.addWidget(self.launch_extra_edit)
        control_layout.addLayout(params_row)

        btn_row = QHBoxLayout()

        self.start_btn = QPushButton("\u25b6  \u542f\u52a8 ComfyUI")
        self.start_btn.setObjectName("successBtn")
        self.start_btn.setMinimumHeight(44)
        self.start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("\u25a0  \u505c\u6b62")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setMinimumHeight(44)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self.stop_btn)

        self.browser_btn = QPushButton("\u6253\u5f00\u6d4f\u89c8\u5668")
        self.browser_btn.setMinimumHeight(44)
        self.browser_btn.clicked.connect(self._on_open_browser)
        btn_row.addWidget(self.browser_btn)

        control_layout.addLayout(btn_row)
        layout.addWidget(control_card)

        log_card = QGroupBox("\u8fd0\u884c\u65e5\u5fd7")
        log_card_layout = QVBoxLayout(log_card)
        self.launch_log = QTextEdit()
        self.launch_log.setReadOnly(True)
        log_card_layout.addWidget(self.launch_log)
        layout.addWidget(log_card)

        self.pages["launch"] = page
        self.page_stack.addWidget(page)

    # ── Environment Page ─────────────────────────────────────────

    def _create_environment_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QLabel("\u73af\u5883\u7ef4\u62a4")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)

        gpu_group = QGroupBox("GPU \u68c0\u6d4b")
        gpu_layout = QVBoxLayout(gpu_group)
        detect_row = QHBoxLayout()
        self.env_detect_btn = QPushButton("\u68c0\u6d4b GPU")
        self.env_detect_btn.setObjectName("primaryBtn")
        self.env_detect_btn.clicked.connect(self._on_detect_gpu)
        detect_row.addWidget(self.env_detect_btn)
        detect_row.addStretch()
        gpu_layout.addLayout(detect_row)

        self.env_gpu_result = QLabel("\u70b9\u51fb\u201c\u68c0\u6d4b GPU\u201d\u5f00\u59cb")
        self.env_gpu_result.setWordWrap(True)
        gpu_layout.addWidget(self.env_gpu_result)
        layout.addWidget(gpu_group)

        torch_group = QGroupBox("PyTorch \u7ba1\u7406")
        torch_layout = QVBoxLayout(torch_group)

        installed_row = QHBoxLayout()
        installed_row.addWidget(QLabel("\u5f53\u524d\u5b89\u88c5:"))
        self.env_installed_torch = QLabel("\u68c0\u6d4b\u4e2d...")
        self.env_installed_torch.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        installed_row.addWidget(self.env_installed_torch)
        installed_row.addStretch()
        torch_layout.addLayout(installed_row)

        torch_layout.addWidget(QLabel("\u53ef\u7528\u7248\u672c:"))
        self.env_torch_combo = QComboBox()
        torch_layout.addWidget(self.env_torch_combo)

        torch_btn_row = QHBoxLayout()
        self.env_install_btn = QPushButton("\u5b89\u88c5\u9009\u4e2d\u7248\u672c")
        self.env_install_btn.setObjectName("primaryBtn")
        self.env_install_btn.clicked.connect(self._on_install_torch)
        torch_btn_row.addWidget(self.env_install_btn)
        self.env_uninstall_btn = QPushButton("\u5378\u8f7d\u5f53\u524d\u7248\u672c")
        self.env_uninstall_btn.setObjectName("dangerBtn")
        self.env_uninstall_btn.clicked.connect(self._on_uninstall_torch)
        torch_btn_row.addWidget(self.env_uninstall_btn)
        torch_btn_row.addStretch()
        torch_layout.addLayout(torch_btn_row)

        self.env_torch_log = QTextEdit()
        self.env_torch_log.setReadOnly(True)
        self.env_torch_log.setMaximumHeight(150)
        torch_layout.addWidget(self.env_torch_log)
        layout.addWidget(torch_group)

        git_group = QGroupBox("Git \u7248\u672c\u7ba1\u7406")
        git_layout = QVBoxLayout(git_group)

        git_info_row = QHBoxLayout()
        git_info_row.addWidget(QLabel("\u5f53\u524d\u5206\u652f:"))
        self.env_branch_label = QLabel("-")
        self.env_branch_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        git_info_row.addWidget(self.env_branch_label)
        git_info_row.addWidget(QLabel("  \u5f53\u524d\u63d0\u4ea4:"))
        self.env_commit_label = QLabel("-")
        self.env_commit_label.setStyleSheet("color: #a6adc8;")
        git_info_row.addWidget(self.env_commit_label)
        git_info_row.addStretch()
        git_layout.addLayout(git_info_row)

        branch_row = QHBoxLayout()
        branch_row.addWidget(QLabel("\u5206\u652f:"))
        self.env_branch_combo = QComboBox()
        branch_row.addWidget(self.env_branch_combo)
        self.env_switch_branch_btn = QPushButton("\u5207\u6362")
        self.env_switch_branch_btn.clicked.connect(self._on_switch_branch)
        branch_row.addWidget(self.env_switch_branch_btn)
        git_layout.addLayout(branch_row)

        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel("\u6807\u7b7e:"))
        self.env_tag_combo = QComboBox()
        tag_row.addWidget(self.env_tag_combo)
        self.env_switch_tag_btn = QPushButton("\u5207\u6362")
        self.env_switch_tag_btn.clicked.connect(self._on_switch_tag)
        tag_row.addWidget(self.env_switch_tag_btn)
        git_layout.addLayout(tag_row)

        git_btn_row = QHBoxLayout()
        self.env_fetch_btn = QPushButton("Fetch")
        self.env_fetch_btn.clicked.connect(self._on_git_fetch)
        git_btn_row.addWidget(self.env_fetch_btn)
        self.env_pull_btn = QPushButton("Pull")
        self.env_pull_btn.clicked.connect(self._on_git_pull)
        git_btn_row.addWidget(self.env_pull_btn)
        self.env_refresh_git_btn = QPushButton("\u5237\u65b0\u7248\u672c\u4fe1\u606f")
        self.env_refresh_git_btn.clicked.connect(self._refresh_git_info)
        git_btn_row.addWidget(self.env_refresh_git_btn)
        git_btn_row.addStretch()
        git_layout.addLayout(git_btn_row)

        self.env_git_log = QTextEdit()
        self.env_git_log.setReadOnly(True)
        self.env_git_log.setMaximumHeight(120)
        git_layout.addWidget(self.env_git_log)
        layout.addWidget(git_group)

        patch_group = QGroupBox("\u8865\u4e01\u7ba1\u7406")
        patch_layout = QVBoxLayout(patch_group)
        self.env_patch_list = QListWidget()
        patch_layout.addWidget(self.env_patch_list)

        patch_btn_row = QHBoxLayout()
        self.env_apply_patch_btn = QPushButton("\u5e94\u7528\u8865\u4e01")
        self.env_apply_patch_btn.clicked.connect(self._on_apply_patch)
        patch_btn_row.addWidget(self.env_apply_patch_btn)
        self.env_revert_patch_btn = QPushButton("\u8fd8\u539f\u8865\u4e01")
        self.env_revert_patch_btn.clicked.connect(self._on_revert_patch)
        patch_btn_row.addWidget(self.env_revert_patch_btn)
        self.env_toggle_patch_btn = QPushButton("\u542f\u7528/\u7981\u7528")
        self.env_toggle_patch_btn.clicked.connect(self._on_toggle_patch)
        patch_btn_row.addWidget(self.env_toggle_patch_btn)
        patch_btn_row.addStretch()
        patch_layout.addLayout(patch_btn_row)
        layout.addWidget(patch_group)

        layout.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.pages["environment"] = page
        self.page_stack.addWidget(page)

    # ── Extensions Page ──────────────────────────────────────────

    def _create_extensions_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QLabel("\u6269\u5c55\u7ba1\u7406")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)

        install_group = QGroupBox("\u5b89\u88c5\u6269\u5c55")
        install_layout = QVBoxLayout(install_group)
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("Git URL:"))
        self.ext_url_edit = QLineEdit()
        self.ext_url_edit.setPlaceholderText("https://github.com/user/comfyui-node-name")
        url_row.addWidget(self.ext_url_edit)
        self.ext_install_btn = QPushButton("\u5b89\u88c5")
        self.ext_install_btn.setObjectName("primaryBtn")
        self.ext_install_btn.clicked.connect(self._on_install_ext)
        url_row.addWidget(self.ext_install_btn)
        install_layout.addLayout(url_row)
        self.ext_install_log = QTextEdit()
        self.ext_install_log.setReadOnly(True)
        self.ext_install_log.setMaximumHeight(80)
        install_layout.addWidget(self.ext_install_log)
        layout.addWidget(install_group)

        list_group = QGroupBox("\u5df2\u5b89\u88c5\u6269\u5c55")
        list_layout = QVBoxLayout(list_group)

        list_btn_row = QHBoxLayout()
        self.ext_refresh_btn = QPushButton("\u5237\u65b0\u5217\u8868")
        self.ext_refresh_btn.clicked.connect(self._refresh_extensions)
        list_btn_row.addWidget(self.ext_refresh_btn)
        self.ext_update_all_btn = QPushButton("\u66f4\u65b0\u5168\u90e8")
        self.ext_update_all_btn.clicked.connect(self._on_update_all_ext)
        list_btn_row.addWidget(self.ext_update_all_btn)
        list_btn_row.addStretch()
        list_layout.addLayout(list_btn_row)

        self.ext_list = QListWidget()
        self.ext_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        list_layout.addWidget(self.ext_list)

        ext_btn_row = QHBoxLayout()
        self.ext_update_btn = QPushButton("\u66f4\u65b0")
        self.ext_update_btn.clicked.connect(self._on_update_ext)
        ext_btn_row.addWidget(self.ext_update_btn)
        self.ext_toggle_btn = QPushButton("\u542f\u7528/\u7981\u7528")
        self.ext_toggle_btn.clicked.connect(self._on_toggle_ext)
        ext_btn_row.addWidget(self.ext_toggle_btn)
        self.ext_remove_btn = QPushButton("\u5220\u9664")
        self.ext_remove_btn.setObjectName("dangerBtn")
        self.ext_remove_btn.clicked.connect(self._on_remove_ext)
        ext_btn_row.addWidget(self.ext_remove_btn)
        ext_btn_row.addStretch()
        list_layout.addLayout(ext_btn_row)

        layout.addWidget(list_group)
        self.pages["extensions"] = page
        self.page_stack.addWidget(page)

    # ── Settings Page ────────────────────────────────────────────

    def _create_settings_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QLabel("\u8bbe\u7f6e")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)

        path_group = QGroupBox("\u8def\u5f84\u914d\u7f6e")
        path_layout = QVBoxLayout(path_group)

        for label_text, attr_name, is_dir in [
            ("ComfyUI \u76ee\u5f55:", "comfyui_dir_edit", True),
            ("Python \u53ef\u6267\u884c\u6587\u4ef6:", "python_exe_edit", False),
            ("Git \u53ef\u6267\u884c\u6587\u4ef6:", "git_exe_edit", False),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            edit = QLineEdit()
            setattr(self, attr_name, edit)
            row.addWidget(edit)
            browse_btn = QPushButton("\u6d4f\u89c8...")
            browse_btn.clicked.connect(lambda checked, e=edit, d=is_dir: self._on_browse(e, d))
            row.addWidget(browse_btn)
            path_layout.addLayout(row)

        layout.addWidget(path_group)

        server_group = QGroupBox("\u670d\u52a1\u5668\u8bbe\u7f6e")
        server_layout = QVBoxLayout(server_group)
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("\u7aef\u53e3:"))
        self.settings_port_spin = QSpinBox()
        self.settings_port_spin.setRange(1024, 65535)
        self.settings_port_spin.setValue(self.settings.port)
        port_row.addWidget(self.settings_port_spin)
        port_row.addStretch()
        server_layout.addLayout(port_row)

        self.settings_listen_check = QCheckBox("\u76d1\u542c\u6240\u6709\u63a5\u53e3 (--listen)")
        self.settings_listen_check.setChecked(self.settings.listen)
        server_layout.addWidget(self.settings_listen_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("\u989d\u5916\u542f\u52a8\u53c2\u6570:"))
        self.settings_extra_edit = QLineEdit()
        self.settings_extra_edit.setPlaceholderText("--highvram --cuda-device 0")
        self.settings_extra_edit.setText(self.settings.extra_args)
        row.addWidget(self.settings_extra_edit)
        server_layout.addLayout(row)
        layout.addWidget(server_group)

        mirror_group = QGroupBox("\u955c\u50cf\u914d\u7f6e")
        mirror_layout = QVBoxLayout(mirror_group)

        pip_row = QHBoxLayout()
        pip_row.addWidget(QLabel("pip \u955c\u50cf:"))
        self.settings_pip_mirror = QComboBox()
        for key, m in PIP_MIRRORS.items():
            self.settings_pip_mirror.addItem(f"{m['name']}  ({m['url']})", key)
        idx = self.settings_pip_mirror.findData(self.settings.pip_mirror)
        if idx >= 0:
            self.settings_pip_mirror.setCurrentIndex(idx)
        pip_row.addWidget(self.settings_pip_mirror)
        self.settings_apply_pip_btn = QPushButton("\u5e94\u7528")
        self.settings_apply_pip_btn.clicked.connect(self._on_apply_pip_mirror)
        pip_row.addWidget(self.settings_apply_pip_btn)
        mirror_layout.addLayout(pip_row)

        hf_row = QHBoxLayout()
        hf_row.addWidget(QLabel("HuggingFace \u955c\u50cf:"))
        self.settings_hf_mirror = QComboBox()
        for key, m in HF_MIRRORS.items():
            self.settings_hf_mirror.addItem(f"{m['name']}  ({m['url']})", key)
        idx = self.settings_hf_mirror.findData(self.settings.hf_mirror)
        if idx >= 0:
            self.settings_hf_mirror.setCurrentIndex(idx)
        hf_row.addWidget(self.settings_hf_mirror)
        mirror_layout.addLayout(hf_row)

        layout.addWidget(mirror_group)

        proxy_group = QGroupBox("\u4ee3\u7406\u8bbe\u7f6e")
        proxy_layout = QVBoxLayout(proxy_group)

        self.settings_proxy_enabled = QCheckBox("\u542f\u7528\u4ee3\u7406")
        self.settings_proxy_enabled.setChecked(self.settings.proxy_enabled)
        proxy_layout.addWidget(self.settings_proxy_enabled)

        proxy_row = QHBoxLayout()
        proxy_row.addWidget(QLabel("\u4ee3\u7406\u5730\u5740:"))
        self.settings_proxy_edit = QLineEdit()
        self.settings_proxy_edit.setPlaceholderText("http://127.0.0.1:7890")
        self.settings_proxy_edit.setText(self.settings.proxy_address)
        proxy_row.addWidget(self.settings_proxy_edit)
        proxy_layout.addLayout(proxy_row)

        proxy_check_row = QHBoxLayout()
        self.settings_proxy_git = QCheckBox("Git")
        self.settings_proxy_pip = QCheckBox("pip")
        self.settings_proxy_hf = QCheckBox("HuggingFace")
        proxy_check_row.addWidget(self.settings_proxy_git)
        proxy_check_row.addWidget(self.settings_proxy_pip)
        proxy_check_row.addWidget(self.settings_proxy_hf)
        proxy_check_row.addStretch()
        proxy_layout.addLayout(proxy_check_row)

        layout.addWidget(proxy_group)

        theme_group = QGroupBox("\u4e3b\u9898")
        theme_layout = QHBoxLayout(theme_group)
        theme_layout.addWidget(QLabel("\u4e3b\u9898\u6a21\u5f0f:"))
        self.settings_theme_combo = QComboBox()
        self.settings_theme_combo.addItem("\u6df1\u8272", "dark")
        self.settings_theme_combo.addItem("\u6d45\u8272", "light")
        idx = self.settings_theme_combo.findData(self.settings.theme)
        if idx >= 0:
            self.settings_theme_combo.setCurrentIndex(idx)
        self.settings_theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.settings_theme_combo)
        theme_layout.addStretch()
        layout.addWidget(theme_group)

        save_btn = QPushButton("\u4fdd\u5b58\u8bbe\u7f6e")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self._on_save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.pages["settings"] = page
        self.page_stack.addWidget(page)

    # ── Log Page ─────────────────────────────────────────────────

    def _create_log_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QLabel("\u65e5\u5fd7")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)

        btn_row = QHBoxLayout()
        self.log_clear_btn = QPushButton("\u6e05\u9664\u65e5\u5fd7")
        self.log_clear_btn.clicked.connect(self._on_clear_log)
        btn_row.addWidget(self.log_clear_btn)
        self.log_export_btn = QPushButton("\u5bfc\u51fa\u65e5\u5fd7")
        self.log_export_btn.clicked.connect(self._on_export_log)
        btn_row.addWidget(self.log_export_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.full_log = QTextEdit()
        self.full_log.setReadOnly(True)
        layout.addWidget(self.full_log)

        self.pages["log"] = page
        self.page_stack.addWidget(page)

    # ── Settings Load/Save ───────────────────────────────────────

    def _load_settings_to_ui(self):
        self.launch_port_spin.setValue(self.settings.port)
        self.launch_listen_check.setChecked(self.settings.listen)
        self.launch_extra_edit.setText(self.settings.extra_args)

        self.settings_port_spin.setValue(self.settings.port)
        self.settings_listen_check.setChecked(self.settings.listen)
        self.settings_extra_edit.setText(self.settings.extra_args)
        self.comfyui_dir_edit.setText(self.settings.comfyui_dir)
        self.python_exe_edit.setText(self.settings.python_exe)
        self.git_exe_edit.setText(self.settings.git_exe)
        self.settings_proxy_edit.setText(self.settings.proxy_address)
        self.settings_proxy_enabled.setChecked(self.settings.proxy_enabled)
        self.settings_proxy_git.setChecked(self.settings.proxy_git)
        self.settings_proxy_pip.setChecked(self.settings.proxy_pip)

    def _on_save_settings(self):
        self.settings.comfyui_dir = self.comfyui_dir_edit.text()
        self.settings.python_exe = self.python_exe_edit.text()
        self.settings.git_exe = self.git_exe_edit.text()
        self.settings.port = self.settings_port_spin.value()
        self.settings.listen = self.settings_listen_check.isChecked()
        self.settings.extra_args = self.settings_extra_edit.text()
        self.settings.proxy_address = self.settings_proxy_edit.text()
        self.settings.proxy_enabled = self.settings_proxy_enabled.isChecked()
        self.settings.proxy_git = self.settings_proxy_git.isChecked()
        self.settings.proxy_pip = self.settings_proxy_pip.isChecked()
        self.settings.hf_mirror = self.settings_hf_mirror.currentData() or "official"

        self.launch_port_spin.setValue(self.settings.port)
        self.launch_listen_check.setChecked(self.settings.listen)
        self.launch_extra_edit.setText(self.settings.extra_args)

        if self.settings.proxy_enabled and self.settings.proxy_git:
            from .mirror_manager import set_git_proxy
            git_exe = self.settings.git_exe or "git"
            set_git_proxy(git_exe, self.settings.proxy_address)
        else:
            from .mirror_manager import set_git_proxy
            git_exe = self.settings.git_exe or "git"
            set_git_proxy(git_exe, "")

        QMessageBox.information(self, "\u5df2\u4fdd\u5b58", "\u8bbe\u7f6e\u5df2\u4fdd\u5b58")

    def _on_browse(self, edit: QLineEdit, is_dir: bool):
        if is_dir:
            path = QFileDialog.getExistingDirectory(self, "\u9009\u62e9\u76ee\u5f55")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "\u9009\u62e9\u6587\u4ef6", "", "Executables (*.exe);;All Files (*)")
        if path:
            edit.setText(path)

    def _on_theme_changed(self, index):
        theme = self.settings_theme_combo.currentData()
        self.settings.theme = theme
        self._apply_theme()

    # ── GPU Detection ────────────────────────────────────────────

    def _auto_detect_gpu(self):
        python_exe = self.settings.python_exe
        if python_exe and os.path.isfile(python_exe):
            self._run_detect(python_exe)

    def _on_detect_gpu(self):
        python_exe = self.python_exe_edit.text()
        if not python_exe or not os.path.isfile(python_exe):
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u5148\u8bbe\u7f6e\u6709\u6548\u7684 Python \u53ef\u6267\u884c\u6587\u4ef6")
            return
        self.settings.python_exe = python_exe
        self._run_detect(python_exe)

    def _run_detect(self, python_exe: str):
        self.launch_gpu_label.setText("\u68c0\u6d4b\u4e2d...")
        self.launch_torch_label.setText("")
        self.env_gpu_result.setText("\u68c0\u6d4b\u4e2d...")
        self._detect_python_exe = python_exe

        worker = DetectWorker(python_exe)
        worker.result.connect(self._on_gpu_detected)
        worker.finished.connect(lambda ok, msg: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_gpu_detected(self, info: dict):
        self.gpu_info = info
        if "error" in info:
            err = info["error"]
            self.launch_gpu_label.setText(f"\u68c0\u6d4b\u5931\u8d25: {err}")
            self.env_gpu_result.setText(f"\u68c0\u6d4b\u5931\u8d25: {err}")
            return

        gpu_type = get_gpu_type(info)
        device = info.get("device_name", "N/A")
        mem = info.get("total_memory_gb", "?")
        torch_ver = info.get("torch_version", "N/A")
        cuda_ver = info.get("cuda_version") or "N/A"
        hip_ver = info.get("hip_version") or "N/A"
        gcn = info.get("gcn_arch", "")

        self.launch_gpu_label.setText(f"{device} ({gpu_type.upper()})  |  \u663e\u5b58: {mem} GB")
        detail_parts = [f"PyTorch {torch_ver}"]
        if cuda_ver != "N/A":
            detail_parts.append(f"CUDA {cuda_ver}")
        if hip_ver != "N/A":
            detail_parts.append(f"HIP/ROCm {hip_ver}")
        if gcn:
            detail_parts.append(f"Arch: {gcn}")
        self.launch_torch_label.setText("  |  ".join(detail_parts))

        self.env_gpu_result.setText(
            f"GPU \u7c7b\u578b: {gpu_type.upper()}\n"
            f"\u8bbe\u5907: {device}\n"
            f"\u663e\u5b58: {mem} GB\n"
            f"PyTorch: {torch_ver}\n"
            f"CUDA: {cuda_ver}\n"
            f"HIP/ROCm: {hip_ver}\n"
            + (f"GCN Arch: {gcn}" if gcn else "")
        )

        self.env_torch_combo.clear()
        versions = get_torch_versions_for_gpu(gpu_type)
        for v in versions:
            self.env_torch_combo.addItem(v["name"], v["cmd"])

        installed_parts = [torch_ver]
        if cuda_ver != "N/A":
            installed_parts.append(f"CUDA {cuda_ver}")
        if hip_ver != "N/A":
            installed_parts.append(f"HIP {hip_ver}")
        self.env_installed_torch.setText("  ".join(installed_parts))

        self._refresh_git_info()
        self._refresh_patches()
        self._refresh_extensions()

    # ── PyTorch Install/Uninstall ────────────────────────────────

    def _on_install_torch(self):
        python_exe = self.python_exe_edit.text() or self.settings.python_exe
        if not python_exe or not os.path.isfile(python_exe):
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u5148\u8bbe\u7f6e\u6709\u6548\u7684 Python")
            return
        cmd = self.env_torch_combo.currentData()
        if not cmd:
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u5148\u68c0\u6d4b GPU \u4ee5\u52a0\u8f7d\u53ef\u7528\u7248\u672c")
            return
        self.env_torch_log.clear()
        self.env_install_btn.setEnabled(False)
        worker = PipWorker(python_exe, cmd)
        worker.output.connect(lambda line: self.env_torch_log.append(line))
        worker.finished.connect(self._on_torch_op_done)
        worker.finished.connect(lambda ok, msg: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_uninstall_torch(self):
        python_exe = self.python_exe_edit.text() or self.settings.python_exe
        if not python_exe or not os.path.isfile(python_exe):
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u5148\u8bbe\u7f6e\u6709\u6548\u7684 Python")
            return
        reply = QMessageBox.question(self, "\u786e\u8ba4", "\u786e\u5b9a\u5378\u8f7d\u5f53\u524d PyTorch\uff1f")
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.env_torch_log.clear()
        self.env_uninstall_btn.setEnabled(False)
        worker = PipWorker(python_exe, "uninstall")
        worker.output.connect(lambda line: self.env_torch_log.append(line))
        worker.finished.connect(self._on_torch_op_done)
        worker.finished.connect(lambda ok, msg: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_torch_op_done(self, success, msg):
        self.env_install_btn.setEnabled(True)
        self.env_uninstall_btn.setEnabled(True)
        self.env_torch_log.append(f"\n{'Success' if success else 'Failed'}: {msg}")
        if success:
            self._run_detect(self.settings.python_exe)

    # ── Git Operations ───────────────────────────────────────────

    def _refresh_git_info(self):
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        if not comfyui_dir or not os.path.isdir(comfyui_dir):
            return
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        branch = get_current_branch(git_exe, comfyui_dir)
        commit = get_current_commit(git_exe, comfyui_dir)
        self.env_branch_label.setText(branch or "-")
        self.env_commit_label.setText(commit or "-")

        branches = get_branches(git_exe, comfyui_dir)
        self.env_branch_combo.clear()
        self.env_branch_combo.addItems(branches)
        if branch and branch in branches:
            self.env_branch_combo.setCurrentText(branch)

        tags = get_tags(git_exe, comfyui_dir)
        self.env_tag_combo.clear()
        self.env_tag_combo.addItems(tags)

        log_lines = get_log(git_exe, comfyui_dir, 10)
        self.env_git_log.setPlainText("\n".join(log_lines))

    def _on_switch_branch(self):
        branch = self.env_branch_combo.currentText()
        if not branch:
            return
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        self._run_git(git_exe, comfyui_dir, ["checkout", branch],
                      on_done=lambda: self._refresh_git_info())

    def _on_switch_tag(self):
        tag = self.env_tag_combo.currentText()
        if not tag:
            return
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        self._run_git(git_exe, comfyui_dir, ["checkout", tag],
                      on_done=lambda: self._refresh_git_info())

    def _on_git_fetch(self):
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        self._run_git(git_exe, comfyui_dir, ["fetch", "--all", "--tags"],
                      on_done=lambda: self._refresh_git_info())

    def _on_git_pull(self):
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        self._run_git(git_exe, comfyui_dir, ["pull"],
                      on_done=lambda: self._refresh_git_info())

    def _run_git(self, git_exe, cwd, args, on_done=None):
        self.env_git_log.append(f"\n$ git {' '.join(args)}")
        worker = GitWorker(git_exe, cwd, args)
        worker.output.connect(lambda line: self.env_git_log.append(line))
        def _git_done(ok, msg):
            self.env_git_log.append(msg)
            self._cleanup_worker(worker)
            if on_done:
                on_done()
        worker.finished.connect(_git_done)
        self._workers.append(worker)
        worker.start()

    # ── Patches ──────────────────────────────────────────────────

    def _refresh_patches(self):
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        if not comfyui_dir or not os.path.isdir(comfyui_dir):
            return
        pm = PatchManager(comfyui_dir)
        patches = pm.list_patches()
        self.env_patch_list.clear()
        for p in patches:
            status = "\u2714 \u5df2\u5e94\u7528" if p["applied"] else "\u2718 \u672a\u5e94\u7528"
            enabled = "\u5df2\u542f\u7528" if p["enabled"] else "\u5df2\u7981\u7528"
            item = QListWidgetItem(f"{p['name']}  [{status}] [{enabled}]")
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.env_patch_list.addItem(item)

    def _on_apply_patch(self):
        item = self.env_patch_list.currentItem()
        if not item:
            return
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        pm = PatchManager(comfyui_dir)
        ok, msg = pm.apply_patch(item.data(Qt.ItemDataRole.UserRole))
        self._log(msg)
        self._refresh_patches()

    def _on_revert_patch(self):
        item = self.env_patch_list.currentItem()
        if not item:
            return
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        pm = PatchManager(comfyui_dir)
        ok, msg = pm.revert_patch(item.data(Qt.ItemDataRole.UserRole))
        self._log(msg)
        self._refresh_patches()

    def _on_toggle_patch(self):
        item = self.env_patch_list.currentItem()
        if not item:
            return
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        pm = PatchManager(comfyui_dir)
        ok, msg = pm.toggle_enabled(item.data(Qt.ItemDataRole.UserRole))
        self._log(msg)
        self._refresh_patches()

    # ── Extensions ───────────────────────────────────────────────

    def _refresh_extensions(self):
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        if not comfyui_dir or not os.path.isdir(comfyui_dir):
            return
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        exts = list_extensions(comfyui_dir, git_exe)
        self.ext_list.clear()
        for ext in exts:
            status = "\u5df2\u7981\u7528" if ext["disabled"] else "\u5df2\u542f\u7528"
            ver = ext.get("version", "")
            text = f"{ext['name']}  [{status}]"
            if ver:
                text += f"  {ver}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ext["name"])
            self.ext_list.addItem(item)

    def _on_install_ext(self):
        url = self.ext_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u8f93\u5165 Git URL")
            return
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        if not comfyui_dir:
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u5148\u8bbe\u7f6e ComfyUI \u76ee\u5f55")
            return
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        self.ext_install_log.clear()
        self.ext_install_btn.setEnabled(False)
        worker = ExtensionWorker(git_exe, comfyui_dir, "install", ext_url=url)
        worker.output.connect(lambda line: self.ext_install_log.append(line))
        def _done(ok, msg):
            self.ext_install_btn.setEnabled(True)
            self.ext_install_log.append(msg)
            self._cleanup_worker(worker)
            if ok:
                self._refresh_extensions()
        worker.finished.connect(_done)
        self._workers.append(worker)
        worker.start()

    def _on_update_ext(self):
        item = self.ext_list.currentItem()
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        ok, msg = update_extension(comfyui_dir, name, git_exe)
        self._log(msg)
        self._refresh_extensions()

    def _on_toggle_ext(self):
        item = self.ext_list.currentItem()
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        ok, msg = toggle_extension(comfyui_dir, name)
        self._log(msg)
        self._refresh_extensions()

    def _on_remove_ext(self):
        item = self.ext_list.currentItem()
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "\u786e\u8ba4", f"\u786e\u5b9a\u5220\u9664\u6269\u5c55 '{name}'\uff1f")
        if reply != QMessageBox.StandardButton.Yes:
            return
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        ok, msg = remove_extension(comfyui_dir, name)
        self._log(msg)
        self._refresh_extensions()

    def _on_update_all_ext(self):
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        if not comfyui_dir:
            return
        git_exe = self.git_exe_edit.text() or self.settings.git_exe
        self.ext_install_log.clear()
        self.ext_update_all_btn.setEnabled(False)
        worker = ExtensionWorker(git_exe, comfyui_dir, "update_all")
        worker.output.connect(lambda line: self.ext_install_log.append(line))
        def _done(ok, msg):
            self.ext_update_all_btn.setEnabled(True)
            self._cleanup_worker(worker)
            self._refresh_extensions()
        worker.finished.connect(_done)
        self._workers.append(worker)
        worker.start()

    # ── Mirror ───────────────────────────────────────────────────

    def _on_apply_pip_mirror(self):
        python_exe = self.python_exe_edit.text() or self.settings.python_exe
        if not python_exe or not os.path.isfile(python_exe):
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u5148\u8bbe\u7f6e Python")
            return
        mirror_key = self.settings_pip_mirror.currentData()
        self.settings.pip_mirror = mirror_key
        ok = set_pip_mirror(python_exe, mirror_key)
        if ok:
            QMessageBox.information(self, "\u5df2\u5e94\u7528", f"pip \u955c\u50cf\u5df2\u5207\u6362")
        else:
            QMessageBox.warning(self, "\u5931\u8d25", "\u5207\u6362 pip \u955c\u50cf\u5931\u8d25")

    # ── Launch/Stop ──────────────────────────────────────────────

    def _on_start(self):
        comfyui_dir = self.comfyui_dir_edit.text() or self.settings.comfyui_dir
        python_exe = self.python_exe_edit.text() or self.settings.python_exe

        if not comfyui_dir or not os.path.isdir(comfyui_dir):
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u5148\u8bbe\u7f6e ComfyUI \u76ee\u5f55")
            return
        if not python_exe or not os.path.isfile(python_exe):
            QMessageBox.warning(self, "\u9519\u8bef", "\u8bf7\u5148\u8bbe\u7f6e Python \u53ef\u6267\u884c\u6587\u4ef6")
            return

        self.settings.comfyui_dir = comfyui_dir
        self.settings.python_exe = python_exe

        main_py = os.path.join(comfyui_dir, "main.py")
        if not os.path.isfile(main_py):
            QMessageBox.warning(self, "\u9519\u8bef", f"\u672a\u627e\u5230 main.py: {main_py}")
            return

        self.runner = ComfyUIRunner(comfyui_dir, python_exe)
        self.runner.started.connect(self._on_runner_started)
        self.runner.output_line.connect(self._on_runner_output)
        self.runner.finished.connect(self._on_runner_finished)

        port = self.launch_port_spin.value()
        listen = self.launch_listen_check.isChecked()
        extra = self.launch_extra_edit.text().split() if self.launch_extra_edit.text().strip() else []

        success = self.runner.start(port=port, listen=listen, extra_args=extra)
        if not success:
            QMessageBox.warning(self, "\u9519\u8bef", "\u542f\u52a8 ComfyUI \u5931\u8d25")

    def _on_runner_started(self, pid: int):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_indicator.setText("\u25cf \u8fd0\u884c\u4e2d")
        self.status_indicator.setStyleSheet("color: #a6e3a1; font-size: 12px; padding: 12px;")
        port = self.launch_port_spin.value()
        self._log(f"ComfyUI \u5df2\u542f\u52a8 (PID: {pid})")
        self._log(f"\u5730\u5740: http://localhost:{port}")

    def _on_runner_output(self, line: str):
        self.launch_log.append(line)
        ts = datetime.now().strftime("%H:%M:%S")
        self.full_log.append(f"[{ts}] {line}")

    def _on_runner_finished(self, return_code: int):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_indicator.setText("\u25cf \u5df2\u7ed3\u675f")
        self.status_indicator.setStyleSheet("color: #f38ba8; font-size: 12px; padding: 12px;")
        self._log(f"ComfyUI \u5df2\u7ed3\u675f (exit code: {return_code})")

    def _on_stop(self):
        if self.runner:
            self.runner.stop()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_indicator.setText("\u25cf \u672a\u8fd0\u884c")
            self.status_indicator.setStyleSheet("color: #6c7086; font-size: 12px; padding: 12px;")
            self._log("ComfyUI \u5df2\u505c\u6b62")

    def _on_open_browser(self):
        port = self.launch_port_spin.value()
        webbrowser.open(f"http://localhost:{port}")

    # ── Log Page ─────────────────────────────────────────────────

    def _on_clear_log(self):
        self.full_log.clear()
        self.launch_log.clear()

    def _on_export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "\u5bfc\u51fa\u65e5\u5fd7", "comfyui_log.txt", "Text (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.full_log.toPlainText())
            QMessageBox.information(self, "\u5df2\u5bfc\u51fa", f"\u65e5\u5fd7\u5df2\u4fdd\u5b58\u5230 {path}")

    # ── Helpers ──────────────────────────────────────────────────

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.launch_log.append(msg)
        self.full_log.append(f"[{ts}] {msg}")

    def _cleanup_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def closeEvent(self, event):
        self.settings.set("window_width", self.width())
        self.settings.set("window_height", self.height())
        if self.runner and self.runner.is_running():
            self.runner.stop()
        for w in self._workers:
            w.cancel()
            w.quit()
            w.wait(2000)
        event.accept()
