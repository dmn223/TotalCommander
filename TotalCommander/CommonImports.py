import sys
import os
import shutil
import json
import datetime
import zipfile
import webbrowser
import psutil
import send2trash
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QFileInfo, QDir, QTimer
from PyQt6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QPushButton, QLabel, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout, QMessageBox,
    QFileDialog, QComboBox, QSpinBox, QHeaderView, QMenuBar, QMenu,
    QFrame, QRadioButton, QCheckBox, QFontDialog, QFileIconProvider, 
    QListWidgetItem, QInputDialog
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

# Clasa care ruleaza operatii pe fisiere intr-un thread separat ca sa nu inghete programul
# În CommonImports.py
class FileOperationWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, sources, destination_dir, operation):
        super().__init__()
        self.sources = sources if isinstance(sources, list) else [sources]
        self.destination_dir = Path(destination_dir)
        self.operation = operation
        self._is_running = True # Flag pentru controlul execuției

    def stop(self):
        """Metodă apelată când utilizatorul apasă Anulează."""
        self._is_running = False

    def run(self):
        try:
            count = 0
            for src_path in self.sources:
                # VERIFICARE: Dacă utilizatorul a anulat, ieșim din buclă imediat
                if not self._is_running:
                    self.finished.emit("Operațiune anulată de utilizator.")
                    return

                src = Path(src_path)
                self.progress.emit(count, src.name)
                
                dest = self.destination_dir / src.name

                # Logica de redenumire/copiere ...
                if src == dest:
                    if self.operation == 'Copy':
                        new_name = f"{src.stem} - Copy{src.suffix}"
                        dest = self.destination_dir / new_name
                        counter = 1
                        while dest.exists():
                            dest = self.destination_dir / f"{src.stem} - Copy ({counter}){src.suffix}"
                            counter += 1
                    else:
                        count += 1
                        continue

                if self.operation == 'Copy':
                    if src.is_dir():
                        shutil.copytree(src, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dest)
                elif self.operation == 'Cut':
                    shutil.move(str(src), str(dest))
                
                count += 1
            
            procesate = "element procesat" if count == 1 else "elemente procesate"
            self.finished.emit(f"Succes: {count} {procesate}.")
        except Exception as e:
            self.error.emit(str(e))