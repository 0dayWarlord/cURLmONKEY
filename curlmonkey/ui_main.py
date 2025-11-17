#ain window UI

import json
import logging
from datetime import datetime
from typing import Dict
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QComboBox, QLineEdit, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QPlainTextEdit, QLabel, QStatusBar, QMenuBar,
    QMessageBox, QDialog, QRadioButton, QButtonGroup, QFileDialog,
    QHeaderView, QCheckBox, QGroupBox, QFormLayout, QSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QClipboard, QShortcut, QKeySequence, QTextCharFormat, QColor, QSyntaxHighlighter, QIcon

from .models import (
    RequestModel, ResponseModel, HttpMethod, BodyType, RawBodyType,
    AuthType, KeyValuePair, MultipartItem, AuthConfig, HistoryEntry, Environment
)
from .http_client import send_request
from .curl_export import generate_curl_command
from .curl_import import parse_curl_command
from .ui_settings import SettingsDialog
from .ui_history import HistoryWidget, CollectionsWidget

logger = logging.getLogger(__name__)


class JsonHighlighter(QSyntaxHighlighter):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor(136, 19, 145))  # Purple
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(26, 26, 166))  # Blue
        
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(28, 0, 207))  # Dark blue
        
        self.bool_format = QTextCharFormat()
        self.bool_format.setForeground(QColor(0, 0, 255))  # Blue
        
        self.null_format = QTextCharFormat()
        self.null_format.setForeground(QColor(128, 128, 128))  # Gray
    
    def highlightBlock(self, text):
        import re
        #simple highlighting
        for match in re.finditer(r'"([^"]+)":', text):
            self.setFormat(match.start(), match.end(), self.key_format)
        #strings
        for match in re.finditer(r'"[^"]*"', text):
            if ':' not in match.group() or match.group().endswith(':'):
                continue
            self.setFormat(match.start(), match.end(), self.string_format)
        #numbers
        for match in re.finditer(r'\b\d+\.?\d*\b', text):
            self.setFormat(match.start(), match.end(), self.number_format)
        #booleans and null
        for match in re.finditer(r'\b(true|false|null)\b', text):
            self.setFormat(match.start(), match.end(), self.bool_format if match.group() in ('true', 'false') else self.null_format)


class RequestWorker(QThread):
    
    finished = Signal(ResponseModel)
    error = Signal(str)
    
    def __init__(self, request: RequestModel, settings, environments):
        super().__init__()
        self.request = request
        self.settings = settings
        self.environments = environments
    
    def run(self):
        try:
            response = send_request(self.request, self.settings, self.environments)
            self.finished.emit(response)
        except Exception as e:
            logger.error(f"Request worker error: {e}", exc_info=True)
            self.error.emit(str(e))


class CurlImportDialog(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.request = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Import from cURL")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Paste your cURL command:")
        layout.addWidget(label)
        
        self.curl_edit = QPlainTextEdit()
        self.curl_edit.setPlaceholderText('curl -X POST "https://api.example.com/endpoint" -H "Content-Type: application/json" -d \'{"key":"value"}\'')
        layout.addWidget(self.curl_edit)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self.do_import)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def do_import(self):
        curl_text = self.curl_edit.toPlainText().strip()
        if not curl_text:
            QMessageBox.warning(self, "Error", "Please enter a cURL command.")
            return
        
        try:
            self.request = parse_curl_command(curl_text)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Parse Error", f"Failed to parse cURL command:\n{str(e)}")


class CurlExportDialog(QDialog):
    
    def __init__(self, curl_command: str, parent=None):
        super().__init__(parent)
        self.init_ui(curl_command)
    
    def init_ui(self, curl_command: str):
        self.setWindowTitle("Generated cURL")
        self.setMinimumSize(700, 400)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Generated cURL command:")
        layout.addWidget(label)
        
        self.curl_edit = QPlainTextEdit()
        self.curl_edit.setPlainText(curl_command)
        self.curl_edit.setReadOnly(True)
        layout.addWidget(self.curl_edit)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def copy_to_clipboard(self):
        clipboard = QClipboard()
        clipboard.setText(self.curl_edit.toPlainText())
        QMessageBox.information(self, "Copied", "cURL command copied to clipboard!")


class KeyValueTable(QTableWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Enabled", "Key", "Value"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(0, 70)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        self.setGridStyle(Qt.PenStyle.SolidLine)
        self.setAlternatingRowColors(True)
        
        #make column dividers more visible

        self.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                border-right: 2px solid palette(mid);
                background-color: palette(alternateBase);
            }
            QHeaderView::section:first {
                border-right: 3px solid palette(dark);
            }
        """)
    
    def add_row(self, key: str = "", value: str = "", enabled: bool = True):
        row = self.rowCount()
        self.insertRow(row)
        
        enabled_item = QTableWidgetItem()
        enabled_item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
        #make enabled column non-editable (only checkbox can be toggled)
        enabled_item.setFlags(enabled_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 0, enabled_item)
        
        self.setItem(row, 1, QTableWidgetItem(key))
        self.setItem(row, 2, QTableWidgetItem(value))
    
    def get_data(self) -> list[KeyValuePair]:
        pairs = []
        for row in range(self.rowCount()):
            enabled_item = self.item(row, 0)
            key_item = self.item(row, 1)
            value_item = self.item(row, 2)
            
            enabled = enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True
            key = key_item.text() if key_item else ""
            value = value_item.text() if value_item else ""
            
            if key or value:
                pairs.append(KeyValuePair(enabled=enabled, key=key, value=value))
        
        return pairs
    
    def set_data(self, pairs: list[KeyValuePair]):
        self.setRowCount(0)
        for pair in pairs:
            self.add_row(pair.key, pair.value, pair.enabled)
    
    def remove_selected_rows(self):
        rows = sorted(set(item.row() for item in self.selectedItems()), reverse=True)
        for row in rows:
            self.removeRow(row)


class MainWindow(QMainWindow):
    
    def __init__(self, settings, environments: Dict[str, Environment], history_widget, collections_widget):
        super().__init__()
        self.settings = settings
        self.environments = environments
        self.history_widget = history_widget
        self.collections_widget = collections_widget
        self.current_request = RequestModel()
        self.current_response = None
        self.request_worker = None
        
        self.init_ui()
        self.setup_shortcuts()
        self.load_environments()
    
    def init_ui(self):
        self.setWindowTitle("cURLmONKEY – the best cURL client around")
        self.setMinimumSize(1200, 700)
        
        #set window icon

        from pathlib import Path
        icon_path = Path(__file__).parent.parent / "favicon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        #menu bar

        self.create_menu_bar()
        
        #central widget

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        #top toolbar

        toolbar_layout = QHBoxLayout()
        
        self.method_combo = QComboBox()
        self.method_combo.addItems([m.value for m in HttpMethod])
        toolbar_layout.addWidget(QLabel("Method:"))
        toolbar_layout.addWidget(self.method_combo)
        
        toolbar_layout.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://api.example.com/endpoint")
        toolbar_layout.addWidget(self.url_edit, stretch=1)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_request)
        toolbar_layout.addWidget(self.send_button)
        
        self.generate_curl_button = QPushButton("Generate cURL")
        self.generate_curl_button.clicked.connect(self.show_curl_export)
        toolbar_layout.addWidget(self.generate_curl_button)
        
        self.from_curl_button = QPushButton("From cURL…")
        self.from_curl_button.clicked.connect(self.show_curl_import)
        toolbar_layout.addWidget(self.from_curl_button)
        
        main_layout.addLayout(toolbar_layout)
        
        #main splitter

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        #left side: request builder

        request_widget = QWidget()
        request_layout = QVBoxLayout(request_widget)
        
        self.request_tabs = QTabWidget()
        
        #params tab

        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        self.params_table = KeyValueTable()
        params_layout.addWidget(self.params_table)
        params_buttons = QHBoxLayout()
        add_param_btn = QPushButton("Add")
        add_param_btn.clicked.connect(lambda: self.params_table.add_row())
        remove_param_btn = QPushButton("Remove")
        remove_param_btn.clicked.connect(self.params_table.remove_selected_rows)
        params_buttons.addWidget(add_param_btn)
        params_buttons.addWidget(remove_param_btn)
        params_buttons.addStretch()
        params_layout.addLayout(params_buttons)
        self.request_tabs.addTab(params_widget, "Params")
        
        #headers tab

        headers_widget = QWidget()
        headers_layout = QVBoxLayout(headers_widget)
        self.headers_table = KeyValueTable()
        headers_layout.addWidget(self.headers_table)
        headers_buttons = QHBoxLayout()
        add_header_btn = QPushButton("Add")
        add_header_btn.clicked.connect(lambda: self.headers_table.add_row())
        remove_header_btn = QPushButton("Remove")
        remove_header_btn.clicked.connect(self.headers_table.remove_selected_rows)
        headers_buttons.addWidget(add_header_btn)
        headers_buttons.addWidget(remove_header_btn)
        headers_buttons.addStretch()
        headers_layout.addLayout(headers_buttons)
        self.request_tabs.addTab(headers_widget, "Headers")
        
        #body tab

        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        
        body_type_group = QButtonGroup()
        self.body_none_radio = QRadioButton("None")
        self.body_raw_radio = QRadioButton("raw")
        self.body_form_radio = QRadioButton("x-www-form-urlencoded")
        self.body_multipart_radio = QRadioButton("multipart/form-data")
        
        body_type_group.addButton(self.body_none_radio, 0)
        body_type_group.addButton(self.body_raw_radio, 1)
        body_type_group.addButton(self.body_form_radio, 2)
        body_type_group.addButton(self.body_multipart_radio, 3)
        
        body_type_layout = QHBoxLayout()
        body_type_layout.addWidget(self.body_none_radio)
        body_type_layout.addWidget(self.body_raw_radio)
        body_type_layout.addWidget(self.body_form_radio)
        body_type_layout.addWidget(self.body_multipart_radio)
        body_type_layout.addStretch()
        body_layout.addLayout(body_type_layout)
        
        self.body_none_radio.setChecked(True)
        self.body_none_radio.toggled.connect(self.on_body_type_changed)
        self.body_raw_radio.toggled.connect(self.on_body_type_changed)
        self.body_form_radio.toggled.connect(self.on_body_type_changed)
        self.body_multipart_radio.toggled.connect(self.on_body_type_changed)
        
        #raw body

        self.raw_body_widget = QWidget()
        raw_body_layout = QVBoxLayout(self.raw_body_widget)
        raw_type_layout = QHBoxLayout()
        raw_type_layout.addWidget(QLabel("Type:"))
        self.raw_type_combo = QComboBox()
        self.raw_type_combo.addItems([t.value for t in RawBodyType])
        raw_type_layout.addWidget(self.raw_type_combo)
        raw_type_layout.addStretch()
        self.pretty_json_btn = QPushButton("Pretty Print JSON")
        self.pretty_json_btn.clicked.connect(self.pretty_print_json)
        raw_type_layout.addWidget(self.pretty_json_btn)
        raw_body_layout.addLayout(raw_type_layout)
        self.raw_body_edit = QPlainTextEdit()
        self.raw_body_edit.setPlaceholderText("Enter request body...")
        raw_body_layout.addWidget(self.raw_body_edit)
        body_layout.addWidget(self.raw_body_widget)
        self.raw_body_widget.setVisible(False)
        
        #form body

        self.form_body_widget = QWidget()
        form_body_layout = QVBoxLayout(self.form_body_widget)
        self.form_table = KeyValueTable()
        form_body_layout.addWidget(self.form_table)
        form_buttons = QHBoxLayout()
        add_form_btn = QPushButton("Add")
        add_form_btn.clicked.connect(lambda: self.form_table.add_row())
        remove_form_btn = QPushButton("Remove")
        remove_form_btn.clicked.connect(self.form_table.remove_selected_rows)
        form_buttons.addWidget(add_form_btn)
        form_buttons.addWidget(remove_form_btn)
        form_buttons.addStretch()
        form_body_layout.addLayout(form_buttons)
        body_layout.addWidget(self.form_body_widget)
        self.form_body_widget.setVisible(False)
        
        #multipart body

        self.multipart_body_widget = QWidget()
        multipart_body_layout = QVBoxLayout(self.multipart_body_widget)
        self.multipart_table = QTableWidget()
        self.multipart_table.setColumnCount(4)
        self.multipart_table.setHorizontalHeaderLabels(["Enabled", "Key", "Type", "Value"])
        self.multipart_table.horizontalHeader().setStretchLastSection(True)
        self.multipart_table.setColumnWidth(0, 70)
        self.multipart_table.setColumnWidth(2, 100)
        self.multipart_table.setShowGrid(True)
        self.multipart_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.multipart_table.setAlternatingRowColors(True)
        self.multipart_table.verticalHeader().setVisible(False)
        
        #make column dividers more visible

        self.multipart_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                border-right: 2px solid palette(mid);
                background-color: palette(alternateBase);
            }
            QHeaderView::section:first {
                border-right: 3px solid palette(dark);
            }
        """)
        multipart_body_layout.addWidget(self.multipart_table)
        multipart_buttons = QHBoxLayout()
        add_multipart_btn = QPushButton("Add")
        add_multipart_btn.clicked.connect(self.add_multipart_row)
        remove_multipart_btn = QPushButton("Remove")
        remove_multipart_btn.clicked.connect(self.remove_multipart_rows)
        multipart_buttons.addWidget(add_multipart_btn)
        multipart_buttons.addWidget(remove_multipart_btn)
        multipart_buttons.addStretch()
        multipart_body_layout.addLayout(multipart_buttons)
        body_layout.addWidget(self.multipart_body_widget)
        self.multipart_body_widget.setVisible(False)
        
        self.request_tabs.addTab(body_widget, "Body")
        
        #auth tab
        auth_widget = QWidget()
        auth_layout = QVBoxLayout(auth_widget)
        
        auth_type_group = QButtonGroup()
        self.auth_none_radio = QRadioButton("None")
        self.auth_basic_radio = QRadioButton("Basic Auth")
        self.auth_bearer_radio = QRadioButton("Bearer Token")
        
        auth_type_group.addButton(self.auth_none_radio, 0)
        auth_type_group.addButton(self.auth_basic_radio, 1)
        auth_type_group.addButton(self.auth_bearer_radio, 2)
        
        auth_type_layout = QHBoxLayout()
        auth_type_layout.addWidget(self.auth_none_radio)
        auth_type_layout.addWidget(self.auth_basic_radio)
        auth_type_layout.addWidget(self.auth_bearer_radio)
        auth_type_layout.addStretch()
        auth_layout.addLayout(auth_type_layout)
        
        self.auth_none_radio.setChecked(True)
        self.auth_none_radio.toggled.connect(self.on_auth_type_changed)
        self.auth_basic_radio.toggled.connect(self.on_auth_type_changed)
        self.auth_bearer_radio.toggled.connect(self.on_auth_type_changed)
        
        self.basic_auth_widget = QWidget()
        basic_auth_layout = QFormLayout(self.basic_auth_widget)
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        basic_auth_layout.addRow("Username:", self.username_edit)
        basic_auth_layout.addRow("Password:", self.password_edit)
        auth_layout.addWidget(self.basic_auth_widget)
        self.basic_auth_widget.setVisible(False)
        
        self.bearer_auth_widget = QWidget()
        bearer_auth_layout = QFormLayout(self.bearer_auth_widget)
        self.bearer_token_edit = QLineEdit()
        bearer_auth_layout.addRow("Token:", self.bearer_token_edit)
        auth_layout.addWidget(self.bearer_auth_widget)
        self.bearer_auth_widget.setVisible(False)
        
        self.request_tabs.addTab(auth_widget, "Auth")
        
        #environment tab

        env_widget = QWidget()
        env_layout = QVBoxLayout(env_widget)
        
        env_select_layout = QHBoxLayout()
        env_select_layout.addWidget(QLabel("Environment:"))
        self.env_combo = QComboBox()
        self.env_combo.currentTextChanged.connect(self.on_environment_changed)
        env_select_layout.addWidget(self.env_combo)
        env_select_layout.addStretch()
        env_layout.addLayout(env_select_layout)
        
        self.env_table = QTableWidget()
        self.env_table.setColumnCount(2)
        self.env_table.setHorizontalHeaderLabels(["Name", "Value"])
        self.env_table.horizontalHeader().setStretchLastSection(True)
        self.env_table.setShowGrid(True)
        self.env_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.env_table.setAlternatingRowColors(True)
        self.env_table.verticalHeader().setVisible(False)
        self.env_table.itemChanged.connect(self.on_env_table_changed)
        
        #make column dividers more visible

        self.env_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                border-right: 2px solid palette(mid);
                background-color: palette(alternateBase);
            }
        """)
        env_layout.addWidget(self.env_table)
        
        env_buttons = QHBoxLayout()
        add_env_btn = QPushButton("Add")
        add_env_btn.clicked.connect(self.add_env_var)
        remove_env_btn = QPushButton("Remove")
        remove_env_btn.clicked.connect(self.remove_env_var)
        env_buttons.addWidget(add_env_btn)
        env_buttons.addWidget(remove_env_btn)
        env_buttons.addStretch()
        env_layout.addLayout(env_buttons)
        
        self.request_tabs.addTab(env_widget, "Environment")
        
        request_layout.addWidget(self.request_tabs)
        splitter.addWidget(request_widget)
        
        #right side: response viewer

        response_widget = QWidget()
        response_layout = QVBoxLayout(response_widget)
        
        #response summary

        summary_layout = QHBoxLayout()
        self.status_label = QLabel("Status: -")
        self.time_label = QLabel("Time: -")
        self.size_label = QLabel("Size: -")
        summary_layout.addWidget(self.status_label)
        summary_layout.addWidget(self.time_label)
        summary_layout.addWidget(self.size_label)
        summary_layout.addStretch()
        response_layout.addLayout(summary_layout)
        
        #response tabs

        self.response_tabs = QTabWidget()
        
        #body tab

        body_response_widget = QWidget()
        body_response_layout = QVBoxLayout(body_response_widget)
        self.response_body_edit = QPlainTextEdit()
        self.response_body_edit.setReadOnly(True)
        self.json_highlighter = JsonHighlighter(self.response_body_edit.document())
        body_response_layout.addWidget(self.response_body_edit)
        body_response_buttons = QHBoxLayout()
        copy_body_btn = QPushButton("Copy Body")
        copy_body_btn.clicked.connect(self.copy_response_body)
        body_response_buttons.addWidget(copy_body_btn)
        body_response_buttons.addStretch()
        body_response_layout.addLayout(body_response_buttons)
        self.response_tabs.addTab(body_response_widget, "Body")
        
        #headers tab

        headers_response_widget = QWidget()
        headers_response_layout = QVBoxLayout(headers_response_widget)
        self.response_headers_table = QTableWidget()
        self.response_headers_table.setColumnCount(2)
        self.response_headers_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.response_headers_table.horizontalHeader().setStretchLastSection(True)
        self.response_headers_table.setShowGrid(True)
        self.response_headers_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.response_headers_table.setAlternatingRowColors(True)
        self.response_headers_table.verticalHeader().setVisible(False)
        
        #make column dividers more visible

        self.response_headers_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                border-right: 2px solid palette(mid);
                background-color: palette(alternateBase);
            }
        """)
        headers_response_layout.addWidget(self.response_headers_table)
        headers_response_buttons = QHBoxLayout()
        copy_headers_btn = QPushButton("Copy Headers")
        copy_headers_btn.clicked.connect(self.copy_response_headers)
        headers_response_buttons.addWidget(copy_headers_btn)
        headers_response_buttons.addStretch()
        headers_response_layout.addLayout(headers_response_buttons)
        self.response_tabs.addTab(headers_response_widget, "Headers")
        
        #raw tab
        raw_response_widget = QWidget()
        raw_response_layout = QVBoxLayout(raw_response_widget)
        self.response_raw_edit = QPlainTextEdit()
        self.response_raw_edit.setReadOnly(True)
        raw_response_layout.addWidget(self.response_raw_edit)
        self.response_tabs.addTab(raw_response_widget, "Raw")
        
        response_layout.addWidget(self.response_tabs)
        splitter.addWidget(response_widget)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        #status bar

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        #disable native menu bar on windows to ensure styling works

        try:
            menubar.setNativeMenuBar(False)
        except:
            pass
        
        #store menu style for reuse

        self.menu_style = """
            QMenu {
                background-color: #353535;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item {
                background-color: transparent;
                color: #ffffff;
                padding: 6px 32px 6px 8px;
            }
            QMenu::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #888888;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555555;
                margin: 4px 0px;
            }
        """
        
        #apply explicit styling to menu bar for dark theme

        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #353535;
                color: #ffffff;
                border-bottom: 1px solid #555555;
            }
            QMenuBar::item {
                background-color: transparent;
                color: #ffffff;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #454545;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background-color: #2a82da;
                color: #ffffff;
            }
        """)
        
        #file menu

        file_menu = menubar.addMenu("File")
        export_collections_action = file_menu.addAction("Export Collections…")
        export_collections_action.triggered.connect(self.export_collections)
        import_collections_action = file_menu.addAction("Import Collections…")
        import_collections_action.triggered.connect(self.import_collections)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        #edit menu

        edit_menu = menubar.addMenu("Edit")
        settings_action = edit_menu.addAction("Settings…")
        settings_action.triggered.connect(self.show_settings)
        
        self.history_dock = None
        self.collections_dock = None
        
        #tools menu

        tools_menu = menubar.addMenu("Tools")
        save_to_collection_action = tools_menu.addAction("Save to Collection…")
        save_to_collection_action.triggered.connect(self.save_to_collection)
        
        #help menu

        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About cURLmONKEY")
        about_action.triggered.connect(self.show_about)
        
        #store menu references

        self.file_menu = file_menu
        self.edit_menu = edit_menu
        self.tools_menu = tools_menu
        self.help_menu = help_menu
        
        #apply menu styling to each menu individually for dark theme

        file_menu.setStyleSheet(self.menu_style)
        edit_menu.setStyleSheet(self.menu_style)
        tools_menu.setStyleSheet(self.menu_style)
        help_menu.setStyleSheet(self.menu_style)
    
    def setup_shortcuts(self):
        #ctrl+enter to send
        send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        send_shortcut.activated.connect(self.send_request)
        
        #ctrl+l to focus url
        url_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        url_shortcut.activated.connect(self.url_edit.setFocus)
    
    def load_environments(self):
        self.env_combo.clear()
        for env_name in self.environments.keys():
            self.env_combo.addItem(env_name)
        if self.settings.default_environment in self.environments:
            self.env_combo.setCurrentText(self.settings.default_environment)
        self.update_env_table()
    
    def on_environment_changed(self, env_name: str):
        self.current_request.environment = env_name
        self.update_env_table()
    
    def update_env_table(self):
        env_name = self.env_combo.currentText()
        env = self.environments.get(env_name, None)
        if not env:
            self.env_table.setRowCount(0)
            return
        
        #temporarily disconnect signal to avoid recursion

        try:
            self.env_table.itemChanged.disconnect(self.on_env_table_changed)
        except:
            pass
        
        self.env_table.setRowCount(len(env.variables))
        for row, (key, value) in enumerate(env.variables.items()):
            self.env_table.setItem(row, 0, QTableWidgetItem(key))
            self.env_table.setItem(row, 1, QTableWidgetItem(value))
        
        #reconnect signal

        self.env_table.itemChanged.connect(self.on_env_table_changed)
    
    def on_env_table_changed(self, item: QTableWidgetItem):
        env_name = self.env_combo.currentText()
        env = self.environments.get(env_name)
        if not env:
            return
        
        row = item.row()
        key_item = self.env_table.item(row, 0)
        value_item = self.env_table.item(row, 1)
        
        if key_item and value_item:
            key = key_item.text()
            value = value_item.text()
            if key:
                env.variables[key] = value
        
        #save environments

        from .persistence import save_environments
        save_environments(self.environments)
    
    def add_env_var(self):
        env_name = self.env_combo.currentText()
        env = self.environments.get(env_name)
        if not env:
            return
        
        row = self.env_table.rowCount()
        self.env_table.insertRow(row)
        self.env_table.setItem(row, 0, QTableWidgetItem(""))
        self.env_table.setItem(row, 1, QTableWidgetItem(""))
    
    def remove_env_var(self):
        rows = sorted(set(item.row() for item in self.env_table.selectedItems()), reverse=True)
        env_name = self.env_combo.currentText()
        env = self.environments.get(env_name)
        if not env:
            return
        
        for row in rows:
            key_item = self.env_table.item(row, 0)
            if key_item:
                key = key_item.text()
                if key in env.variables:
                    del env.variables[key]
            self.env_table.removeRow(row)
        
        self.update_env_table()
        from .persistence import save_environments
        save_environments(self.environments)
    
    def on_body_type_changed(self):
        self.raw_body_widget.setVisible(self.body_raw_radio.isChecked())
        self.form_body_widget.setVisible(self.body_form_radio.isChecked())
        self.multipart_body_widget.setVisible(self.body_multipart_radio.isChecked())
    
    def on_auth_type_changed(self):
        self.basic_auth_widget.setVisible(self.auth_basic_radio.isChecked())
        self.bearer_auth_widget.setVisible(self.auth_bearer_radio.isChecked())
    
    def add_multipart_row(self):
        row = self.multipart_table.rowCount()
        self.multipart_table.insertRow(row)
        
        enabled_item = QTableWidgetItem()
        enabled_item.setCheckState(Qt.CheckState.Checked)
        #make enabled column non-editable (only checkbox can be toggled)
        enabled_item.setFlags(enabled_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.multipart_table.setItem(row, 0, enabled_item)
        
        self.multipart_table.setItem(row, 1, QTableWidgetItem(""))
        
        type_combo = QComboBox()
        type_combo.addItems(["text", "file"])
        self.multipart_table.setCellWidget(row, 2, type_combo)
        
        value_item = QTableWidgetItem("")
        self.multipart_table.setItem(row, 3, value_item)
    
    def remove_multipart_rows(self):
        rows = sorted(set(item.row() for item in self.multipart_table.selectedItems()), reverse=True)
        for row in rows:
            self.multipart_table.removeRow(row)
    
    def pretty_print_json(self):
        text = self.raw_body_edit.toPlainText()
        try:
            import json
            obj = json.loads(text)
            pretty = json.dumps(obj, indent=2)
            self.raw_body_edit.setPlainText(pretty)
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Invalid JSON", "The text is not valid JSON.")
    
    def get_request_model(self) -> RequestModel:
        request = RequestModel()
        
        #method and url

        request.method = HttpMethod(self.method_combo.currentText())
        #strip quotes from url if present
        url = self.url_edit.text().strip()
        #remove surrounding quotes (single or double)
        if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
            url = url[1:-1]
        request.url = url
        
        #query params

        request.query_params = self.params_table.get_data()
        
        #headers

        request.headers = self.headers_table.get_data()
        
        #body

        if self.body_none_radio.isChecked():
            request.body_type = BodyType.NONE
        elif self.body_raw_radio.isChecked():
            request.body_type = BodyType.RAW
            request.raw_body_type = RawBodyType(self.raw_type_combo.currentText())
            request.raw_body = self.raw_body_edit.toPlainText()
        elif self.body_form_radio.isChecked():
            request.body_type = BodyType.FORM_URLENCODED
            request.form_data = self.form_table.get_data()
        elif self.body_multipart_radio.isChecked():
            request.body_type = BodyType.MULTIPART
            request.multipart_data = []
            for row in range(self.multipart_table.rowCount()):
                enabled_item = self.multipart_table.item(row, 0)
                key_item = self.multipart_table.item(row, 1)
                type_widget = self.multipart_table.cellWidget(row, 2)
                value_item = self.multipart_table.item(row, 3)
                
                enabled = enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True
                key = key_item.text() if key_item else ""
                item_type = type_widget.currentText() if type_widget else "text"
                value = value_item.text() if value_item else ""
                
                if key or value:
                    request.multipart_data.append(
                        MultipartItem(enabled=enabled, key=key, type=item_type, value=value)
                    )
        
        #auth

        if self.auth_none_radio.isChecked():
            request.auth = AuthConfig(auth_type=AuthType.NONE)
        elif self.auth_basic_radio.isChecked():
            request.auth = AuthConfig(
                auth_type=AuthType.BASIC,
                username=self.username_edit.text(),
                password=self.password_edit.text()
            )
        elif self.auth_bearer_radio.isChecked():
            request.auth = AuthConfig(
                auth_type=AuthType.BEARER,
                bearer_token=self.bearer_token_edit.text()
            )
        
        #environment
        
        request.environment = self.env_combo.currentText()
        
        return request
    
    def set_request_model(self, request: RequestModel):
        if isinstance(request.method, HttpMethod):
            method_value = request.method.value
        else:
            method_value = str(request.method)
        self.method_combo.setCurrentText(method_value)
        self.url_edit.setText(request.url)
        
        #query params

        self.params_table.set_data(request.query_params)
        
        #headers

        self.headers_table.set_data(request.headers)
        
        #body

        if request.body_type == BodyType.NONE:
            self.body_none_radio.setChecked(True)
        elif request.body_type == BodyType.RAW:
            self.body_raw_radio.setChecked(True)
            self.raw_type_combo.setCurrentText(request.raw_body_type.value)
            self.raw_body_edit.setPlainText(request.raw_body)
        elif request.body_type == BodyType.FORM_URLENCODED:
            self.body_form_radio.setChecked(True)
            self.form_table.set_data(request.form_data)
        elif request.body_type == BodyType.MULTIPART:
            self.body_multipart_radio.setChecked(True)
            self.multipart_table.setRowCount(0)
            for item in request.multipart_data:
                row = self.multipart_table.rowCount()
                self.multipart_table.insertRow(row)
                
                enabled_item = QTableWidgetItem()
                enabled_item.setCheckState(Qt.CheckState.Checked if item.enabled else Qt.CheckState.Unchecked)
                #make enabled column non-editable (only checkbox can be toggled)
                enabled_item.setFlags(enabled_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.multipart_table.setItem(row, 0, enabled_item)
                
                self.multipart_table.setItem(row, 1, QTableWidgetItem(item.key))
                
                type_combo = QComboBox()
                type_combo.addItems(["text", "file"])
                type_combo.setCurrentText(item.type)
                self.multipart_table.setCellWidget(row, 2, type_combo)
                
                self.multipart_table.setItem(row, 3, QTableWidgetItem(item.value))
        
        #auth

        if request.auth.auth_type == AuthType.NONE:
            self.auth_none_radio.setChecked(True)
        elif request.auth.auth_type == AuthType.BASIC:
            self.auth_basic_radio.setChecked(True)
            self.username_edit.setText(request.auth.username)
            self.password_edit.setText(request.auth.password)
        elif request.auth.auth_type == AuthType.BEARER:
            self.auth_bearer_radio.setChecked(True)
            self.bearer_token_edit.setText(request.auth.bearer_token)
        
        #environment

        self.env_combo.setCurrentText(request.environment)
        
        self.current_request = request
    
    def send_request(self):
        request = self.get_request_model()
        
        if not request.url:
            QMessageBox.warning(self, "Error", "URL is required.")
            return
        
        if not self.settings.ssl_verify:
            reply = QMessageBox.warning(
                self, "SSL Verification Disabled",
                "SSL verification is disabled. This is not recommended for production use.",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
        
        #disable send button

        self.send_button.setEnabled(False)
        self.send_button.setText("Sending…")
        self.status_bar.showMessage("Sending request...")
        
        #clear previous response

        self.current_response = None
        self.response_body_edit.clear()
        self.response_headers_table.setRowCount(0)
        self.response_raw_edit.clear()
        self.status_label.setText("Status: -")
        self.time_label.setText("Time: -")
        self.size_label.setText("Size: -")
        
        #start worker thread

        if self.request_worker:
            self.request_worker.terminate()
            self.request_worker.wait()
        
        self.request_worker = RequestWorker(request, self.settings, self.environments)
        self.request_worker.finished.connect(self.on_request_finished)
        self.request_worker.error.connect(self.on_request_error)
        self.request_worker.start()
    
    def on_request_finished(self, response: ResponseModel):
        self.current_response = response
        
        #update status bar

        self.send_button.setEnabled(True)
        self.send_button.setText("Send")
        
        if response.error:
            self.status_bar.showMessage(f"Error: {response.error}")
            QMessageBox.critical(self, "Request Error", response.error)
            return
        
        #update summary

        self.status_label.setText(f"Status: {response.status_code} {response.reason}")
        self.time_label.setText(f"Time: {response.time_taken_ms:.2f} ms")
        size_bytes = len(response.body_bytes)
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.2f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        self.size_label.setText(f"Size: {size_str}")
        
        #update body

        body_text = response.body_text
        #try to pretty print json
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" in content_type:
            try:
                import json
                obj = json.loads(body_text)
                body_text = json.dumps(obj, indent=2)
            except:
                pass
        
        self.response_body_edit.setPlainText(body_text)
        
        #update headers

        self.response_headers_table.setRowCount(len(response.headers))
        for row, (key, value) in enumerate(response.headers.items()):
            self.response_headers_table.setItem(row, 0, QTableWidgetItem(key))
            self.response_headers_table.setItem(row, 1, QTableWidgetItem(value))
        
        #update raw

        raw_text = f"HTTP/1.1 {response.status_code} {response.reason}\n"
        for key, value in response.headers.items():
            raw_text += f"{key}: {value}\n"
        raw_text += "\n"
        raw_text += body_text
        self.response_raw_edit.setPlainText(raw_text)
        
        #save to history

        request = self.get_request_model()
        history_entry = HistoryEntry(
            timestamp=datetime.now(),
            method=request.method.value,
            url=request.url,
            status_code=response.status_code,
            request=request
        )
        self.history_widget.add_entry(history_entry)
        from .persistence import add_history_entry
        add_history_entry(history_entry)
        
        self.status_bar.showMessage(f"Request completed: {response.status_code} {response.reason}")
    
    def on_request_error(self, error_msg: str):
        self.send_button.setEnabled(True)
        self.send_button.setText("Send")
        self.status_bar.showMessage(f"Error: {error_msg}")
        QMessageBox.critical(self, "Request Error", error_msg)
    
    def show_curl_export(self):
        request = self.get_request_model()
        curl_command = generate_curl_command(
            request,
            include_proxy=False,
            proxy_http=self.settings.http_proxy,
            proxy_https=self.settings.https_proxy,
            ssl_verify=self.settings.ssl_verify
        )
        dialog = CurlExportDialog(curl_command, self)
        dialog.exec()
    
    def show_curl_import(self):
        dialog = CurlImportDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.request:
            self.set_request_model(dialog.request)
            self.status_bar.showMessage("cURL command imported successfully")
    
    def copy_response_body(self):
        clipboard = QClipboard()
        clipboard.setText(self.response_body_edit.toPlainText())
        self.status_bar.showMessage("Response body copied to clipboard")
    
    def copy_response_headers(self):
        headers_text = ""
        for row in range(self.response_headers_table.rowCount()):
            key = self.response_headers_table.item(row, 0)
            value = self.response_headers_table.item(row, 1)
            if key and value:
                headers_text += f"{key.text()}: {value.text()}\n"
        clipboard = QClipboard()
        clipboard.setText(headers_text)
        self.status_bar.showMessage("Response headers copied to clipboard")
    
    def show_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_settings:
            self.settings = dialog.result_settings
            from .persistence import save_settings
            save_settings(self.settings)
            self.status_bar.showMessage("Settings saved")
    
    def save_to_collection(self):
        request = self.get_request_model()
        if not request.url:
            QMessageBox.warning(self, "Error", "Please enter a URL first.")
            return
        
        collections = self.collections_widget.get_all_collections()
        if not collections:
            QMessageBox.information(self, "No Collections", "Please create a collection first.")
            return
        
        from PySide6.QtWidgets import QInputDialog
        collection_names = [c.name for c in collections]
        collection_name, ok = QInputDialog.getItem(
            self, "Save to Collection", "Select collection:", collection_names, 0, False
        )
        if ok and collection_name:
            request_name, ok = QInputDialog.getText(
                self, "Request Name", "Enter a name for this request:"
            )
            if ok:
                if not request_name:
                    request_name = f"{request.method.value} {request.url[:30]}"
                self.collections_widget.add_request_to_collection(collection_name, request, request_name)
                from .persistence import save_collections
                save_collections(self.collections_widget.get_all_collections())
                self.status_bar.showMessage(f"Request saved to '{collection_name}'")
    
    def export_collections(self):
        collections = self.collections_widget.get_all_collections()
        if not collections:
            QMessageBox.information(self, "No Collections", "No collections to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Collections", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                data = [coll.to_dict() for coll in collections]
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                self.status_bar.showMessage(f"Collections exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export collections:\n{str(e)}")
    
    def import_collections(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Collections", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                from .models import Collection
                collections = [Collection.from_dict(coll) for coll in data]
                #merge with existing
                existing = self.collections_widget.get_all_collections()
                existing_names = {c.name for c in existing}
                for coll in collections:
                    if coll.name not in existing_names:
                        existing.append(coll)
                self.collections_widget.load_collections(existing)
                from .persistence import save_collections
                save_collections(existing)
                self.status_bar.showMessage(f"Collections imported from {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import collections:\n{str(e)}")
    
    def show_about(self):
        QMessageBox.about(
            self, "About cURLmONKEY",
            "<h2>cURLmONKEY</h2>"
            "<p>Version 1.0.0</p>"
            "<p>a graphical cURL client</p>"
            "<p>made with love by tiramisu</p>"
            "<p>https://github.com/0dayWarlord/cURLmONKEY</p>"
        )

