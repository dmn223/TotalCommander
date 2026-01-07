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
        self.parent_window = parent_window
        self.setWindowTitle("Setări Font")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout()

        self.label = QLabel("Marime Font:")
        layout.addWidget(self.label)
        
        self.fontSizeSpinBox = QSpinBox()
        self.fontSizeSpinBox.setRange(8, 72)
        current_size = self.parent_window.font().pointSize()
        self.fontSizeSpinBox.setValue(current_size)
        layout.addWidget(self.fontSizeSpinBox)

        self.fontBtn = QPushButton("Schimba Familia Fontului")
        self.fontBtn.clicked.connect(self.chooseFont)
        layout.addWidget(self.fontBtn)

        self.fontSizeSpinBox.valueChanged.connect(self.applySettings)

        self.themeBtn = QPushButton("Schimba Modul (Dark/Light)")
        self.themeBtn.clicked.connect(self.toggle_theme)

        layout.addWidget(self.themeBtn)
        
        self.setLayout(layout)

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

