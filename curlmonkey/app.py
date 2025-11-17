#application setup

import logging
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QDockWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPalette, QColor

from .logging_config import setup_logging
from .persistence import (
    load_settings, save_settings, load_history, load_collections,
    load_environments, save_environments
)
from .ui_main import MainWindow
from .ui_history import HistoryWidget, CollectionsWidget

logger = logging.getLogger(__name__)


def create_application() -> QApplication:
    #set windows app id for proper taskbar icon (must be done before creating QApplication)
    if sys.platform == "win32":
        try:
            import ctypes
            #set appusermodelid to make windows show our icon in taskbar
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("cURLmONKEY.HTTPClient.1.0")
        except:
            pass
    
    app = QApplication(sys.argv)
    app.setApplicationName("cURLmONKEY")
    app.setOrganizationName("cURLmONKEY")
    
    #set application icon
    
    icon_path = Path(__file__).parent.parent / "favicon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    #use fusion style
    from PySide6.QtWidgets import QStyleFactory
    fusion_style = QStyleFactory.create("Fusion")
    if fusion_style:
        app.setStyle(fusion_style)
    
    return app

#apply dark theme

def setup_application(app: QApplication, settings):
    #apply dark theme
    palette = QPalette()
    
    #window colors
    
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    
    #base colors (for input fields)
    
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    
    #text colors
    
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    
    #button colors
    
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    
    #highlight colors
    
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    
    #tooltip colors
    
    palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    
    #link colors
    
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.LinkVisited, QColor(130, 42, 218))
    
    #set palette for all color groups (active, inactive, disabled)
    
    for group in [QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled]:
        palette.setColor(group, QPalette.Window, QColor(53, 53, 53))
        palette.setColor(group, QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(group, QPalette.Button, QColor(53, 53, 53))
        palette.setColor(group, QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(group, QPalette.Text, QColor(255, 255, 255))
    
    app.setPalette(palette)
    
    #additional stylesheet for better dark theme
    
    app.setStyleSheet("""
        QMainWindow {
            background-color: #353535;
        }
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
        QMenu {
            background-color: #353535;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QMenu::item {
            background-color: transparent;
            color: #ffffff;
            padding: 4px 24px 4px 8px;
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
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #353535;
        }
        QTabBar::tab {
            background-color: #454545;
            color: #ffffff;
            padding: 8px 16px;
            border: 1px solid #555555;
        }
        QTabBar::tab:selected {
            background-color: #2a82da;
        }
        QTableWidget {
            background-color: #232323;
            color: #ffffff;
            gridline-color: #666666;
            border: 2px solid #555555;
            alternate-background-color: #2a2a2a;
        }
        QTableWidget::item {
            border-right: 1px solid #666666;
            border-bottom: 1px solid #666666;
            padding: 6px;
        }
        QHeaderView::section {
            background-color: #3a3a3a;
            color: #ffffff;
            padding: 8px;
            border: 1px solid #666666;
            border-right: 2px solid #888888;
            border-bottom: 2px solid #888888;
            font-weight: bold;
        }
        QHeaderView::section:first {
            border-right: 3px solid #555555;
        }
        QLineEdit, QPlainTextEdit, QTextEdit {
            background-color: #232323;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 4px;
        }
        QComboBox {
            background-color: #232323;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 4px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #232323;
            color: #ffffff;
            selection-background-color: #2a82da;
        }
        QPushButton {
            background-color: #454545;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 6px 12px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #555555;
        }
        QPushButton:pressed {
            background-color: #2a82da;
        }
        QStatusBar {
            background-color: #232323;
            color: #ffffff;
        }
    """)


def create_main_window(app: QApplication) -> MainWindow:
    #load data
    settings = load_settings()
    environments = load_environments()
    history_entries = load_history()
    collections = load_collections()
    
    #ensure default environment exists
    
    if "Default" not in environments:
        from .models import Environment
        default_env = Environment(name="Default", variables={})
        environments["Default"] = default_env
        save_environments(environments)
    
    #create widgets
    
    history_widget = HistoryWidget()
    history_widget.load_history(history_entries)
    
    collections_widget = CollectionsWidget()
    collections_widget.load_collections(collections)
    
    #create main window
    
    main_window = MainWindow(settings, environments, history_widget, collections_widget)
    
    #create docks for history and collections
    
    history_dock = QDockWidget("History", main_window)
    history_dock.setWidget(history_widget)
    history_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
    main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, history_dock)
    main_window.history_dock = history_dock
    
    collections_dock = QDockWidget("Collections", main_window)
    collections_dock.setWidget(collections_widget)
    collections_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
    main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, collections_dock)
    main_window.collections_dock = collections_dock
    
    #connect signals
    
    history_widget.request_selected.connect(main_window.set_request_model)
    collections_widget.request_selected.connect(main_window.set_request_model)
    
    #apply theme
    
    setup_application(app, settings)
    
    return main_window


def run_application():
    #setup logging
    setup_logging()
    logger.info("Starting cURLmONKEY")
    
    #create application
    
    app = create_application()
    
    #create main window
    main_window = create_main_window(app)
    main_window.show()
    
    #run event loop
    
    exit_code = app.exec()
    
    #save data on exit
    
    logger.info("Saving data on exit...")
    from .persistence import save_history, save_collections, save_environments
    
    history_widget = main_window.history_widget
    collections_widget = main_window.collections_widget
    
    save_history(history_widget.get_all_entries())
    save_collections(collections_widget.get_all_collections())
    
    #save environments
    environments = main_window.environments
    save_environments(environments)
    
    logger.info("Application exiting")
    return exit_code


if __name__ == "__main__":
    sys.exit(run_application())

