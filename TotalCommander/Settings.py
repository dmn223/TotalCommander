from faulthandler import is_enabled
import sys
from tkinter import Button
from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtWidgets import QApplication, QInputDialog, QLabel, QPushButton, QSpinBox, QFileIconProvider, QWidget, QTreeWidgetItem, QTreeWidget, QDialog, QMessageBox, QMenu, QLineEdit, QFontDialog
from PyQt6.uic import loadUi
from pathlib import Path
from PyQt6.QtCore import QFileInfo, QDir
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QHeaderView, QMenuBar, QMenu
from PyQt6.QtGui import QFileSystemModel, QKeySequence, QShortcut, QAction, QPalette, QColor
import os
import ctypes
import shutil
import zipfile
import datetime
from PyQt6.QtCore import Qt
import PyQt6.QtCore as QtCore
import webbrowser

class SettingsMenu(QDialog):
    def __init__(self, parent_window):
        super().__init__(parent_window)

    def chooseFont(self):
        font, ok = QFontDialog.getFont(self.parent_window.font(), self)
        if ok:
            self.parent_window.setFont(font)
            self.fontSizeSpinBox.setValue(font.pointSize())

    def toggle_theme(self):
        if self.parent_window.is_dark:
            self.parent_window.apply_light_theme()
            self.parent_window.is_dark = False
        else:
            self.parent_window.apply_dark_theme()
            self.parent_window.is_dark = True

    def applySettings(self):
        new_size = self.fontSizeSpinBox.value()
        current_font = self.parent_window.font()
        current_font.setPointSize(new_size)
        
        self.parent_window.setFont(current_font)
        self.parent_window.update()

class SizeInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schimbă Dimensiuni")
        self.setFixedSize(400, 180)
        
        # Mărim textul pentru tot dialogul
        self.setStyleSheet("""
            QDialog { background-color: #2d2d2d; color: white; }
            QLabel { font-size: 16px; font-weight: bold; min-width: 100px; }
            QLineEdit { font-size: 16px; padding: 5px; background-color: #1e1e1e; color: white; border: 1px solid #555; }
            QPushButton { font-size: 14px; padding: 5px; }
        """)
        
        layout = QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()

        self.input_stretch = QLineEdit(self)
        self.input_stretch.setPlaceholderText("Default: 2 3")
        
        self.input_fixed = QLineEdit(self)
        self.input_fixed.setPlaceholderText("Default: 2 3")

        # Row-urile create automat vor prelua font-ul de 18px din QSS
        form_layout.addRow("Marime Frame Stang", self.input_stretch)
        form_layout.addRow("Marime Frame Drept", self.input_fixed)
        
        layout.addLayout(form_layout)

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def get_data(self):
        return self.input_stretch.text(), self.input_fixed.text()
