from CommonImports import *

class SettingsMenu(QDialog):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
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
            
            QLabel { font-size: 16px; font-weight: bold; min-width: 100px; }
            QLineEdit { font-size: 16px; padding: 5px; border: 1px solid #555; }
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

class DefaultPathDialog(QDialog):
    def __init__(self, current_left, current_right, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Setări Directoare Default")
        self.setFixedWidth(500)
        layout = QVBoxLayout(self)

        # UI pentru Panel Stânga
        layout.addWidget(QLabel("Cale Default Panel Stânga:"))
        self.left_edit = QLineEdit(current_left)
        layout.addWidget(self.left_edit)
        self.btn_set_left = QPushButton("Setează cu calea curentă (Stânga)")
        layout.addWidget(self.btn_set_left)

        layout.addWidget(QFrame()) # Separator

        # UI pentru Panel Dreapta
        layout.addWidget(QLabel("Cale Default Panel Dreapta:"))
        self.right_edit = QLineEdit(current_right)
        layout.addWidget(self.right_edit)
        self.btn_set_right = QPushButton("Setează cu calea curentă (Dreapta)")
        layout.addWidget(self.btn_set_right)

        # Butoane Salvare/Anulare
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        # Logica pentru butoanele de "Set current"
        self.btn_set_left.clicked.connect(lambda: self.left_edit.setText(str(parent.currentPathLeft)))
        self.btn_set_right.clicked.connect(lambda: self.right_edit.setText(str(parent.currentPathRight)))

    def validate_and_accept(self):
        lp = Path(self.left_edit.text())
        rp = Path(self.right_edit.text())

        if lp.is_dir() and rp.is_dir():
            save_settings(lp, rp)
            self.accept()
        else:
            QMessageBox.warning(self, "Eroare", "Una dintre căi nu este validă sau nu este un director!")
