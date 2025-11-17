#settings dialog UI

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSpinBox, QCheckBox, QLineEdit, QPushButton,
    QGroupBox, QLabel
)
from PySide6.QtCore import Qt

from .models import Settings


class SettingsDialog(QDialog):
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.result_settings = None
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        #network settings
        
        network_group = QGroupBox("Network")
        network_layout = QFormLayout()
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setSuffix(" seconds")
        network_layout.addRow("Default Timeout:", self.timeout_spin)
        
        self.ssl_verify_check = QCheckBox("Verify SSL certificates")
        network_layout.addRow("", self.ssl_verify_check)
        
        self.http_proxy_edit = QLineEdit()
        self.http_proxy_edit.setPlaceholderText("http://proxy.example.com:8080")
        network_layout.addRow("HTTP Proxy:", self.http_proxy_edit)
        
        self.https_proxy_edit = QLineEdit()
        self.https_proxy_edit.setPlaceholderText("https://proxy.example.com:8080")
        network_layout.addRow("HTTPS Proxy:", self.https_proxy_edit)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        #environment settings
        
        env_group = QGroupBox("Environment")
        env_layout = QFormLayout()
        
        self.default_env_edit = QLineEdit()
        env_layout.addRow("Default Environment:", self.default_env_edit)
        
        env_group.setLayout(env_layout)
        layout.addWidget(env_group)
        
        #buttons
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        self.timeout_spin.setValue(self.settings.default_timeout)
        self.ssl_verify_check.setChecked(self.settings.ssl_verify)
        self.http_proxy_edit.setText(self.settings.http_proxy)
        self.https_proxy_edit.setText(self.settings.https_proxy)
        self.default_env_edit.setText(self.settings.default_environment)
    
    def get_settings(self) -> Settings:
        return Settings(
            default_timeout=self.timeout_spin.value(),
            ssl_verify=self.ssl_verify_check.isChecked(),
            default_environment=self.default_env_edit.text() or "Default",
            http_proxy=self.http_proxy_edit.text(),
            https_proxy=self.https_proxy_edit.text(),
            theme="dark"
        )
    
    def accept(self):
        self.result_settings = self.get_settings()
        super().accept()

