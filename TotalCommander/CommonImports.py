import sys
import os
import shutil
import json
import datetime
import zipfile
import webbrowser
import psutil
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QFileInfo, QDir, QTimer
from PyQt6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QPushButton, QLabel, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout, QMessageBox,
    QFileDialog, QComboBox, QSpinBox, QHeaderView, QMenuBar, QMenu,
    QFrame, QRadioButton, QCheckBox, QFontDialog, QFileIconProvider, QListWidgetItem
)
from PyQt6.QtGui import QFileSystemModel, QKeySequence, QShortcut, QAction, QPalette, QColor
from PyQt6.uic import loadUi

# Configurații Globale
CONFIG_FILE = "settings.json"

def load_settings():
    default_right = "D:/" if Path("D:/").exists() else "C:/"
    defaults = {"left_path": "C:/", "right_path": default_right}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return defaults
    return defaults

def save_settings(left, right):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"left_path": str(left), "right_path": str(right)}, f)

# Item special care permite ca iesirea din folder ".." sa ramana in primul loc intotdeauna
class PersistentTopItem(QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        if self.text(0) == "..":
            return True if self.treeWidget().header().sortIndicatorOrder() == Qt.SortOrder.AscendingOrder else False
        if other.text(0) == "..":
            return False if self.treeWidget().header().sortIndicatorOrder() == Qt.SortOrder.AscendingOrder else True  

        if column == 1:
            data1 = self.data(1, Qt.ItemDataRole.UserRole)
            data2 = other.data(1, Qt.ItemDataRole.UserRole)
            def clean_size(val):
                if val is None or val == "": return -1
                if isinstance(val, str): return int(val.replace(",", "").replace(".", ""))
                return int(val)
            return clean_size(data1) < clean_size(data2)
        return self.text(column).lower() < other.text(column).lower()
