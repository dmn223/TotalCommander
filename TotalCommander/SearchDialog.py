from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtWidgets import QApplication, QInputDialog, QLabel, QPushButton, QSpinBox, QFileIconProvider, QWidget, QTreeWidgetItem, QTreeWidget, QDialog, QMessageBox, QMenu, QLineEdit, QFontDialog
from PyQt6.uic import loadUi
from pathlib import Path
from PyQt6.QtCore import QFileInfo, QDir, QThread, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QLabel, QPushButton, QSpinBox, QListWidgetItem, 
                             QFileDialog, QMessageBox, QComboBox, QGridLayout,
                             QRadioButton, QCheckBox)
from PyQt6.QtGui import QFileSystemModel, QKeySequence, QShortcut, QAction, QPalette, QColor
import os
import ctypes
import shutil

class SearchWorker(QThread):
    # Signals to send data back to the UI safely
    match_found = pyqtSignal(str)
    status_update = pyqtSignal(str) # New signal for the "Live" path
    finished = pyqtSignal()

    def __init__(self, start_path, query, match_case, max_depth, filters, size_limit, size_mode):
        super().__init__()
        self.start_path = start_path
        self.query = query
        self.match_case = match_case
        self.max_depth = max_depth
        self.filters = filters # (both, files_only, folders_only)
        self.size_limit = size_limit # Value in MB
        self.size_mode = size_mode   # "Mai mare de", "Mai mic de", "Oricât"
        self._is_running = True

    def run(self):
        self.recursive_search(self.start_path, 0)
        self.finished.emit()

    def stop(self):
        self._is_running = False

    def recursive_search(self, path, current_depth):
        if current_depth > self.max_depth or not self._is_running:
            return

        # Emit the current directory we are scanning
        self.status_update.emit(f"Se cauta in: {str(path)}")

        try:
            for entry in path.iterdir():
                if not self._is_running: break
                
                name = entry.name if self.match_case else entry.name.lower()
                search_q = self.query if self.match_case else self.query.lower()

                if search_q in name:
                    # 1. Type Filter
                    type_ok = self.filters['both'] or \
                             (self.filters['files'] and entry.is_file()) or \
                             (self.filters['folders'] and entry.is_dir())
                    
                    # 2. Size Filter (only applies to files)
                    size_ok = True
                    if entry.is_file() and self.size_limit is not None:
                        file_mb = entry.stat().st_size / (1024 * 1024)
                        if self.size_mode == "Mai mare de":
                            size_ok = file_mb > self.size_limit
                        elif self.size_mode == "Mai mic de":
                            size_ok = file_mb < self.size_limit

                    if type_ok and size_ok:
                        self.match_found.emit(str(entry))

                if entry.is_dir():
                    self.recursive_search(entry, current_depth + 1)
        except Exception:
            pass

class SearchDialog(QDialog):
    # Create a custom signal that sends the directory path and the filename
    location_selected = pyqtSignal(str, str)

    def __init__(self, start_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Căutare Avansată")
        self.start_path = start_path # The path passed from main window
        self.setMinimumSize(500, 500)
        
        layout = QVBoxLayout(self)

        # 1. Starting Directory Selection
        layout.addWidget(QLabel("Caută în:"))
        path_layout = QHBoxLayout()
        
        self.path_input = QLineEdit(str(self.start_path))
        self.browse_btn = QPushButton("...") # Small button for browsing
        self.browse_btn.setFixedWidth(30)
        self.browse_btn.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)

        # Search Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Introduceți numele căutat...")
        layout.addWidget(QLabel("Nume fișier:"))
        layout.addWidget(self.search_input)

        # Size Filter Row
        size_layout = QHBoxLayout()
        layout.addWidget(QLabel("Mărime fișier (MB):"))
        self.size_mode_combo = QComboBox()
        self.size_mode_combo.addItems(["Oricât", "Mai mare de", "Mai mic de"])
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 1000000000)
        
        size_layout.addWidget(self.size_mode_combo)
        size_layout.addWidget(self.size_spin)
        layout.addLayout(size_layout)
        
        # Options Group
        options_layout = QtWidgets.QGridLayout()
        self.case_checkbox = QtWidgets.QCheckBox("Match Case")
        self.files_only = QtWidgets.QRadioButton("Doar Fișiere")
        self.folders_only = QtWidgets.QRadioButton("Doar Foldere")
        self.both_types = QtWidgets.QRadioButton("Ambele")
        self.both_types.setChecked(True)
        
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 100)
        self.depth_spin.setValue(10)
        
        options_layout.addWidget(self.case_checkbox, 0, 0)
        options_layout.addWidget(QLabel("Adâncime maximă:"), 0, 1)
        options_layout.addWidget(self.depth_spin, 0, 2)
        options_layout.addWidget(self.files_only, 1, 0)
        options_layout.addWidget(self.folders_only, 1, 1)
        options_layout.addWidget(self.both_types, 1, 2)
        layout.addLayout(options_layout)

        # Results List
        self.results_list = QtWidgets.QListWidget()
        layout.addWidget(QLabel("Rezultate:"))
        layout.addWidget(self.results_list)

        # Add Status Label above the button
        self.status_label = QLabel("Gata de căutare")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_label)

        self.search_btn = QPushButton("Caută")
        self.search_btn.clicked.connect(self.run_search)
        layout.addWidget(self.search_btn)
        
        # Change the double-click connection
        self.results_list.itemDoubleClicked.connect(self.navigate_to_result)
    
    def clear_inputs(self):
        self.search_input.clear()
        self.results_list.clear()
        self.size_spin.setValue(0)
        self.size_mode_combo.setCurrentIndex(0)
        self.status_label.setText("Gata de căutare")

    def browse_folder(self):
        # This opens a standard system folder picker
        new_dir = QFileDialog.getExistingDirectory(self, "Selectează Folderul de Căutare", self.path_input.text())
        if new_dir:
            self.path_input.setText(new_dir)

    def run_search(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.search_btn.setText("Caută")
            return

        self.status_label.setStyleSheet("color: gray; font-style: italic; font-weight: normal;")
        search_path_str = self.path_input.text()
        start_path = Path(search_path_str)

        # Check valid start path
        if not start_path.exists():
            QMessageBox.critical(self, "Eroare Cale", f"Calea specificată nu există:\n{search_path_str}")
            return
        
        if not start_path.is_dir():
            QMessageBox.warning(self, "Eroare Cale", "Calea de pornire trebuie să fie un folder, nu un fișier!")
            return

        self.results_list.clear()
        query = self.search_input.text()
        
        if not query: return

        # Bundle filters for the worker
        filters = {
            'both': self.both_types.isChecked(),
            'files': self.files_only.isChecked(),
            'folders': self.folders_only.isChecked()
        }

        # Setup the worker
        size_val = self.size_spin.value()
        size_mode = self.size_mode_combo.currentText()

        self.worker = SearchWorker(
            Path(self.path_input.text()), 
            query, 
            self.case_checkbox.isChecked(), 
            self.depth_spin.value(),
            filters,
            size_limit=size_val if size_mode != "Oricât" else None,
            size_mode=size_mode
        )

        # Connect signals
        self.worker.status_update.connect(self.update_live_status)
        self.worker.match_found.connect(self.add_result_to_list)
        self.worker.finished.connect(self.search_finished)
        
        # Start the background thread
        self.worker.start()
        self.search_btn.setText("Stop")

    def update_live_status(self, folder_name):
        # Shows the folder currently being scanned
        self.status_label.setText(folder_name)

    def add_result_to_list(self, file_path):
        self.results_list.addItem(file_path)
        # Update status label with count
        count = self.results_list.count()
        self.setWindowTitle(f"Căutare Avansată - {count} rezultate")

    def search_finished(self):
        self.search_btn.setText("Caută")
        if self.results_list.count() == 0:
            self.results_list.addItem("Niciun rezultat găsit.")
            return

        self.status_label.setText(f"Căutare finalizată! Găsite: {self.results_list.count()} elemente.")
        self.status_label.setStyleSheet("color: green; font-weight: bold;") # Optional: make it green

    def navigate_to_result(self, item):
        full_path = Path(item.text())
        # If it's a file, we want the folder it's in. If folder, use it directly.
        folder_to_open = str(full_path.parent) if full_path.is_file() else str(full_path)
        file_to_highlight = full_path.name
        
        # Emit the signal (send data to TotalCommander.py)
        self.location_selected.emit(folder_to_open, file_to_highlight)
        self.close() # Close search after navigating

    def recursive_search(self, path, query, match_case, max_depth, current_depth):
        results = []
        if current_depth > max_depth:
            return results

        try:
            for entry in path.iterdir():
                name = entry.name if match_case else entry.name.lower()
                search_q = query if match_case else query.lower()

                # Filter by type
                is_match = False
                if search_q in name:
                    if self.both_types.isChecked(): is_match = True
                    elif self.files_only.isChecked() and entry.is_file(): is_match = True
                    elif self.folders_only.isChecked() and entry.is_dir(): is_match = True

                if is_match:
                    results.append(entry)

                # Continue recursion if it's a directory
                if entry.is_dir():
                    results.extend(self.recursive_search(entry, query, match_case, max_depth, current_depth + 1))
        except PermissionError:
            pass # Skip folders we can't access
        return results

    def open_result(self, item):
        path = item.text()
        if os.path.exists(path):
            os.startfile(path)


