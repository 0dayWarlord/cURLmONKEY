#history and collections UI

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QTabWidget,
    QMenu, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from datetime import datetime

from .models import RequestModel, HistoryEntry, Collection, CollectionItem


class HistoryWidget(QWidget):
    """History sidebar widget."""
    
    request_selected = Signal(RequestModel)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history_entries = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        #header
        header_layout = QHBoxLayout()
        header_label = QLabel("History")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_history)
        header_layout.addWidget(self.clear_button)
        
        layout.addLayout(header_layout)
        #history list
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_context_menu)
        self.history_list.setAlternatingRowColors(True)
        layout.addWidget(self.history_list)
    
    def load_history(self, entries: list[HistoryEntry]):
        self.history_entries = entries
        self.history_list.clear()
        
        for entry in entries:
            item = QListWidgetItem(entry.name)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            #add timestamp as tooltip
            timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status_info = f" ({entry.status_code})" if entry.status_code else ""
            item.setToolTip(f"{timestamp_str}{status_info}\n{entry.url}")
            self.history_list.addItem(item)
    
    def add_entry(self, entry: HistoryEntry):
        self.history_entries.insert(0, entry)
        item = QListWidgetItem(entry.name)
        item.setData(Qt.ItemDataRole.UserRole, entry)
        timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        status_info = f" ({entry.status_code})" if entry.status_code else ""
        item.setToolTip(f"{timestamp_str}{status_info}\n{entry.url}")
        self.history_list.insertItem(0, item)
        #keep only last 1000 visible
        if self.history_list.count() > 1000:
            self.history_list.takeItem(self.history_list.count() - 1)
    
    def on_item_double_clicked(self, item: QListWidgetItem):
        entry = item.data(Qt.ItemDataRole.UserRole)
        if entry:
            #use stored full request if available, otherwise create minimal request
            if entry.request:
                self.request_selected.emit(entry.request)
            else:
                from .models import HttpMethod
                request = RequestModel()
                try:
                    request.method = HttpMethod(entry.method)
                except (ValueError, AttributeError):
                    request.method = HttpMethod.GET
                request.url = entry.url
                self.request_selected.emit(request)
    
    def show_context_menu(self, position):
        item = self.history_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_item(item))
        menu.exec(self.history_list.mapToGlobal(position))
    
    def delete_item(self, item: QListWidgetItem):
        row = self.history_list.row(item)
        if row >= 0:
            self.history_list.takeItem(row)
            entry = item.data(Qt.ItemDataRole.UserRole)
            if entry in self.history_entries:
                self.history_entries.remove(entry)
    
    def clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to clear all history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_list.clear()
            self.history_entries.clear()
    
    def get_all_entries(self) -> list[HistoryEntry]:
        return self.history_entries


class CollectionsWidget(QWidget):
    """Collections sidebar widget."""
    
    request_selected = Signal(RequestModel)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.collections = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        #header
        header_layout = QHBoxLayout()
        header_label = QLabel("Collections")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self.add_collection_button = QPushButton("+ Collection")
        self.add_collection_button.clicked.connect(self.add_collection)
        header_layout.addWidget(self.add_collection_button)
        
        layout.addLayout(header_layout)

        #collections tree

        self.collections_tree = QTreeWidget()
        self.collections_tree.setHeaderLabel("Collections")
        self.collections_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.collections_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.collections_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.collections_tree.setAlternatingRowColors(True)
        
        #make tree styling consistent with tables

        self.collections_tree.header().setStyleSheet("""
            QHeaderView::section {
                border-right: 2px solid palette(mid);
                background-color: palette(alternateBase);
            }
        """)
        layout.addWidget(self.collections_tree)
    
    def load_collections(self, collections: list[Collection]):
        self.collections = collections
        self.collections_tree.clear()
        
        for collection in collections:
            collection_item = QTreeWidgetItem(self.collections_tree)
            collection_item.setText(0, collection.name)
            collection_item.setData(0, Qt.ItemDataRole.UserRole, collection)
            
            for item in collection.items:
                request_item = QTreeWidgetItem(collection_item)
                request_item.setText(0, item.name)
                request_item.setData(0, Qt.ItemDataRole.UserRole, item)
    
    def add_collection(self):
        name, ok = QInputDialog.getText(self, "New Collection", "Collection name:")
        if ok and name:
            collection = Collection(name=name, items=[])
            self.collections.append(collection)
            self.refresh_tree()
    
    def add_request_to_collection(self, collection_name: str, request: RequestModel, request_name: str = ""):
        collection = next((c for c in self.collections if c.name == collection_name), None)
        if not collection:
            collection = Collection(name=collection_name, items=[])
            self.collections.append(collection)
        
        if not request_name:
            request_name = f"{request.method.value} {request.url[:30]}"
        
        item = CollectionItem(name=request_name, request=request)
        collection.items.append(item)
        self.refresh_tree()
    
    def refresh_tree(self):
        self.load_collections(self.collections)
    
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, CollectionItem):
            self.request_selected.emit(data.request)
    
    def show_context_menu(self, position):
        item = self.collections_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if isinstance(data, Collection):
            add_request_action = menu.addAction("Add Request")
            add_request_action.triggered.connect(lambda: self.add_request_dialog(data))
            menu.addSeparator()
            delete_action = menu.addAction("Delete Collection")
            delete_action.triggered.connect(lambda: self.delete_collection(data))
        elif isinstance(data, CollectionItem):
            delete_action = menu.addAction("Delete Request")
            delete_action.triggered.connect(lambda: self.delete_request(item, data))
        
        menu.exec(self.collections_tree.mapToGlobal(position))
    
    def add_request_dialog(self, collection: Collection):
        pass
    
    def delete_collection(self, collection: Collection):
        reply = QMessageBox.question(
            self, "Delete Collection",
            f"Are you sure you want to delete '{collection.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if collection in self.collections:
                self.collections.remove(collection)
            self.refresh_tree()
    
    def delete_request(self, item: QTreeWidgetItem, collection_item: CollectionItem):
        parent = item.parent()
        if parent:
            collection = parent.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(collection, Collection):
                if collection_item in collection.items:
                    collection.items.remove(collection_item)
                self.refresh_tree()
    
    def get_all_collections(self) -> list[Collection]:
        return self.collections

