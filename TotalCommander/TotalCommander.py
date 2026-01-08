from faulthandler import is_enabled
import sys
from tkinter import Button
from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtWidgets import QApplication, QInputDialog, QLabel, QPushButton, QSpinBox, QFileIconProvider, QWidget, QTreeWidgetItem, QTreeWidget, QDialog, QMessageBox, QMenu, QLineEdit, QFontDialog
from PyQt6.uic import loadUi
from pathlib import Path
from PyQt6.QtCore import QFileInfo, QDir
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QHeaderView, QMenuBar, QMenu, QFrame
from PyQt6.QtGui import QFileSystemModel, QKeySequence, QShortcut, QAction, QPalette, QColor
import os
import ctypes
import shutil
import zipfile
import datetime
from PyQt6.QtCore import Qt
import PyQt6.QtCore as QtCore
import webbrowser
from SearchDialog import SearchDialog
from Settings import SettingsMenu
from Settings import SizeInputDialog
def list_directory_contents(directory_path: str) -> list[dict]:
    path = Path(directory_path)
    if not path.is_dir():
        return []

    contents = []
    for entry in path.iterdir():
        try:
            stats = entry.stat()
            contents.append({
                'name': entry.name,
                'is_dir': entry.is_dir(),
                'size': int(stats.st_size) if entry.is_file() else int(0),
                'is_file': entry.is_file(),
                'ext': entry.suffix,
                'path': str(entry),
                'modify_date': datetime.datetime.fromtimestamp(stats.st_mtime)
            })
        except Exception:
            continue
    return contents

class MyApp(QDialog):

    # obiecte de tipul respectiv

    LeftTree: QTreeWidget
    LeftPanelTree : QTreeWidget
    RightTree: QTreeWidget
    RightPanelTree : QTreeWidget

    AddButton: QPushButton
    BackButton: QPushButton
    NextButton: QPushButton
    DelButton: QPushButton

    butonLupa: QPushButton
    butonRefresh: QPushButton
    butonCreare: QPushButton
    butonArhivare: QPushButton
    butonDezarhivare: QPushButton

    LeftPathLine: QLineEdit
    LeftFindPathButton: QPushButton

    RightPathLine: QLineEdit
    RightFindPathButton: QPushButton

    PathHistoryBackLeft: list[Path]
    PathHistoryBackRight: list[Path]
    PathHistoryNextLeft: list[Path]
    PathHistoryNextRight: list[Path]

    frameTreesLeft : QFrame
    frameTreesRight : QFrame

    currentPathLeft: Path
    currentPathRight: Path
    panel_activated: str
    clipboard: Path

    def __init__(self):
        super().__init__()
        loadUi('Display.ui', self)
        self.all_panels = [self.LeftTree, self.RightTree, self.LeftPanelTree, self.RightPanelTree]
        self.setWindowState(QtCore.Qt.WindowState.WindowMaximized)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMinimizeButtonHint | QtCore.Qt.WindowType.WindowMaximizeButtonHint) # creaza butonul de full screen
        self.buttons = self.findChildren(QPushButton)
        for btn in self.buttons:
            btn.clicked.connect(self.shortCutButton)

        #Initializare drag and drop 

        # Pentru panoul stâng (LeftTree)
        self.LeftTree.setDragEnabled(True)
        self.LeftTree.setAcceptDrops(True)
        self.LeftTree.setDropIndicatorShown(True)
        self.LeftTree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.LeftTree.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

        # Pentru panoul drept (RightTree)
        self.RightTree.setDragEnabled(True)
        self.RightTree.setAcceptDrops(True)
        self.RightTree.setDropIndicatorShown(True)
        self.RightTree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.RightTree.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

        self.LeftTree.dropEvent = lambda event: self.handle_drop(event, self.getActivePanel(), self.LeftTree)
        self.RightTree.dropEvent = lambda event: self.handle_drop(event, self.getActivePanel(), self.RightTree)

        # Suprascriem dragEnterEvent pentru a accepta acțiunea
        self.LeftTree.dragEnterEvent = lambda event: event.accept()
        self.RightTree.dragEnterEvent = lambda event: event.accept()
        
        self.is_dark = False

        self.adjustSize() 
        self.update()

        # vectori care memoreaza adresa curenta si anterioara ptr fiecare din arbori
        self.PathHistoryBackLeft = []
        self.PathHistoryBackRight = []
        self.PathHistoryNextLeft = []
        self.PathHistoryNextRight = []

        #discul afisad (default)
        self.currentPathLeft = Path("C:/")
        self.currentPathRight = Path("D:/") if Path("D:/").exists() else Path("C:/")
        
        #pornim cu panelul stang default
        self.panel_activated = 'Left' 

        #configurare widgeturi
        self.ConfigWidgets()

        #path-ul curent e none (default)
        self.clipboard_path: Path | None = None
        self.clipboard_operation: str = '' # 'Copy' sau 'Cut'

        #Shortcuturi (F3, F4, del samd)
        # F3 - Proprietati
        QShortcut(QKeySequence("F3"), self).activated.connect(self.ShowProperties)
    
        # F4 - Redenumire
        QShortcut(QKeySequence("F4"), self).activated.connect(self.RenameSelected)
    
        # F5 - Arhivare (Zip)
        QShortcut(QKeySequence("F5"), self).activated.connect(self.ZipPath)

        # CTRL + F5 - Dezarhivare (UnZip)
        QShortcut(QKeySequence("Ctrl+F5"), self).activated.connect(self.UnzipPath)

        # F6 - Refresh (Reincarca directoarele)
        QShortcut(QKeySequence("F6"), self).activated.connect(self.RefreshPanels)

        # F7 - Folder Nou
        QShortcut(QKeySequence("F7"), self).activated.connect(self.AddFile)

        # Delete - Stergere
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self).activated.connect(self.DelFile)

        # Ctrl + X pentru Tăiere (Cut)
        QShortcut(QKeySequence.StandardKey.Cut, self).activated.connect(self.CutPath)

        # Săgeată Stânga (Back)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self).activated.connect(self.GoBack)

        # Săgeată Dreapta (Next)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self).activated.connect(self.GoNext)

        self.auto_detect_theme()

    def openSettings(self):
        font, ok = QFontDialog.getFont(self.font(), self, "Selectează Fontul")
    
        if ok:
            self.setFont(font)

            self.LeftTree.setFont(font)
            self.RightTree.setFont(font)
            self.LeftPanelTree.setFont(font)
            self.RightPanelTree.setFont(font)

            self.LeftTree.header().setFont(font)
            self.RightTree.header().setFont(font)
            self.LeftPanelTree.header().setFont(font)
            self.RightPanelTree.header().setFont(font)
    
            for btn in self.buttons:
                btn.setFont(font)

            self.LeftPathLabel.setFont(font)
            self.LeftPathLine.setFont(font)
            
            self.RightPathLabel.setFont(font)
            self.RightPathLine.setFont(font)

            for i in range(self.LeftTree.columnCount()):
                self.LeftTree.resizeColumnToContents(i)
                self.RightTree.resizeColumnToContents(i)

            print("Toate elementele de tip Tree au fost actualizate.")

    def toggle_theme(self):
        self.is_dark = not self.is_dark
    
        if self.is_dark:
            self.apply_dark_theme()
            self.themeAction.setText("Schimba in Mod Luminos")
        else:
            self.apply_light_theme()
            self.themeAction.setText("Schimba in Mod Intunecat")
        self.style_active_panel()

    def refresh_panel_styles(self):
        """Updates every single panel in the app at once."""
        for tree in self.all_panels:
            is_active = False
            if self.panel_activated == 'Left' and tree == self.LeftTree:
                is_active = True
            elif self.panel_activated == 'Right' and tree == self.RightTree:
                is_active = True
            elif self.panel_activated == 'LeftPanel' and tree == self.LeftPanelTree:
                is_active = True
            elif self.panel_activated == 'RightPanel' and tree == self.RightPanelTree:
                is_active = True

            self.apply_single_panel_style(tree, is_active)

    def apply_single_panel_style(self, tree, is_active):
        # 1. Pick colors based on Theme
        if self.is_dark:
            bg = "#1E1E1E"
            text = "white"
            active_border = "#00A2FF"
            inactive_border = "#444"
        else:
            bg = "white"
            text = "black"
            active_border = "#0078D7"
            inactive_border = "#ababab"

        # 2. Pick border thickness based on Focus
        border_width = "2px" if is_active else "1px"
        border_color = active_border if is_active else inactive_border

        # 3. Apply it
        tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {bg};
                color: {text};
                border: {border_width} solid {border_color};
            }}
        """)

    def SetupMenu(self):
        # Create the Menu Bar
        self.menuBar = QMenuBar(self)
    
        # 1. File Menu
        fileMenu = self.menuBar.addMenu("&Fisier")
    
        exitAction = QAction("Iesire", self)
        exitAction.setShortcut("Ctrl+Q")
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)

        searchAction = QAction("Cautare", self)
        searchAction.setShortcut("Ctrl+F")
        searchAction.triggered.connect(self.OpenSearch)
        fileMenu.addAction(searchAction)

        # 2. Edit Menu
        editMenu = self.menuBar.addMenu("&Editare")
    
        copyAction = QAction("Copiere", self)
        copyAction.setShortcut("Ctrl+C")
        copyAction.triggered.connect(self.CopyPath)
        editMenu.addAction(copyAction)
    
        pasteAction = QAction("Lipire", self)
        pasteAction.setShortcut("Ctrl+V")
        pasteAction.triggered.connect(self.PastePath)
        editMenu.addAction(pasteAction)

        # 3. Options Menu (Theme & Settings)
        optionsMenu = self.menuBar.addMenu("&Optiuni")

        self.themeAction = QAction("Schimba in Mod Luminnos", self)
        self.themeAction.triggered.connect(self.toggle_theme)
        optionsMenu.addAction(self.themeAction)
    
        self.settingsAction = QAction("Setari Font", self)
        self.settingsAction.triggered.connect(self.openSettings)
        optionsMenu.addAction(self.settingsAction)

        self.changeAction = QAction("Shimba Dimnesiunea Panel-urilor", self)
        self.changeAction.triggered.connect(self.ChangeSize)
        optionsMenu.addAction(self.changeAction)

        # Add the menu bar to your main layout
        # Assuming your .ui file has a main QVBoxLayout named 'verticalLayout'
        self.layout().setMenuBar(self.menuBar)

    def ChangeSize(self):
        dialog = SizeInputDialog(self)
    
        if dialog.exec() == QDialog.DialogCode.Accepted:
            val_stretch, val_fixed = dialog.get_data()
        
            try:
                for frame in [self.frameTreesLeft, self.frameTreesRight]:
                    frame.setMinimumWidth(0)
                    frame.setMaximumWidth(16777215)
                    # Schimbăm policy-ul din 'Preferred' în 'Expanding'
                    frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

                # --- PASUL 2: APLICARE STRETCH (Proporții) ---
                p_parts = val_stretch.split()
                s_parts = val_fixed.split()
                if len(s_parts) >= 2:
                    s_left = int(s_parts[0])
                    s_right = int(s_parts[1])
                    self.horizontalLayout_4.setStretch(0, s_left)
                    self.horizontalLayout_4.setStretch(1, s_right)

                if len(p_parts) >= 2:
                    p_left = int(p_parts[0])
                    p_right = int(p_parts[1])
                    self.horizontalLayout_2.setStretch(0, p_left)
                    self.horizontalLayout_2.setStretch(1, p_right)
            except Exception as e:
                print(f"Eroare: {e}")

    def RefreshPanels(self):
        """Reincarca listele de fisiere pentru ambele panouri."""
        self.setupTree(self.LeftTree, self.currentPathLeft)
        self.setupTree(self.RightTree, self.currentPathRight)
        print("Panouri actualizate.")

    def ConfigWidgets(self): 

        self.LeftTree.installEventFilter(self)
        self.RightTree.installEventFilter(self)
        self.LeftPathLine.installEventFilter(self)
        self.RightPathLine.installEventFilter(self)

        self.LeftTree.viewport().installEventFilter(self)
        self.RightTree.viewport().installEventFilter(self)

        self.SortColumns()

        self.SetupMenu()

        self.LeftTree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.RightTree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        
        self.LeftTree.customContextMenuRequested.connect(self.showContextMenu)
        self.RightTree.customContextMenuRequested.connect(self.showContextMenu)

        self.LeftTree.itemDoubleClicked.connect(self.OpenItem)
        self.RightTree.itemDoubleClicked.connect(self.OpenItem)

        self.LeftTree.setHeaderLabels(["Name", "Size", "Ext", "DateMod"])
        self.RightTree.setHeaderLabels(["Name", "Size", "Ext", "DateMod"])

        self.RefreshPanels()

        self.BackButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.NextButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.BackButton.clicked.connect(self.GoBack)
        self.NextButton.clicked.connect(self.GoNext)
        self.butonLupa.clicked.connect(self.OpenSearch)
        self.butonRefresh.clicked.connect(self.RefreshPanels)
        self.butonCreare.clicked.connect(self.AddFile)
        self.butonArhivare.clicked.connect(self.ZipPath)
        self.butonDezarhivare.clicked.connect(self.UnzipPath)

        self.style_active_panel(self.LeftTree)

        self.LeftPathLine.returnPressed.connect(self.NavigateToPathLeft)
        self.LeftFindPathButton.clicked.connect(self.NavigateToPathLeft)
        self.RightPathLine.returnPressed.connect(self.NavigateToPathRight)
        self.RightFindPathButton.clicked.connect(self.NavigateToPathRight)
        
        self.LeftPathLine.setText(str(self.currentPathLeft)) 
        self.RightPathLine.setText(str(self.currentPathRight)) 

        self.setupPanel()

    def shortCutButton(self):
        button = self.sender()

        if not button:
            return ;

        text = button.text()
        if 'F3 - Proprietati' in text: self.ShowProperties()
        if 'F4 - Redenumire'in text: self.RenameSelected()
        if 'F5 - Arhivare' in text: self.ZipPath()
        if 'F6 - Refresh' in text: self.RefreshPanels()
        if 'F7 - Folder Nou'in text: self.AddFile()
        if 'Del - Stergere' in text: self.DelFile()
        if 'CTRL + C - Copiere' in text: self.CopyPath()
        if 'CTRL + V - Lipire' in text: self.PastePath()
        if 'CTRL + X - Taiere' in text: self.CutPath()
        if 'CTRL + F5 - Dezarhivare' in text: self.UnzipPath()
        if 'Setari' in text: self.openSettings()
    
    def eventFilter(self, source, event):
        # Detectare focus 
        if event.type() == QtCore.QEvent.Type.FocusIn: #pentru tree uri
            if source == self.LeftTree:
                self.panel_activated = 'Left'
                self.style_active_panel(self.LeftTree)
            elif source == self.RightTree:
                self.panel_activated = 'Right'
                self.style_active_panel(self.RightTree)
            elif source == self.LeftPanelTree:
                self.panel_activated = 'LeftPanel'
                self.style_active_panel(self.LeftPanelTree)
            elif source == self.RightPanelTree:
                self.panel_activated = 'RightPanel'
                self.style_active_panel(self.RightPanelTree)

        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if source in [self.LeftTree, self.LeftTree.viewport(), self.RightTree, self.RightTree.viewport(), self.LeftPanelTree, self.LeftPanelTree.viewport(), self.RightPanelTree, self.RightPanelTree.viewport()]:
            
                if source in [self.LeftTree, self.LeftTree.viewport()]:
                    self.panel_activated = 'Left'
                    self.style_active_panel(self.LeftTree)
                if source in [self.RightTree, self.RightTree.viewport()]:
                    self.panel_activated = 'Right'
                    self.style_active_panel(self.RightTree)
                if source in [self.LeftPanelTree, self.LeftPanelTree.viewport()]:
                    self.panel_activated = 'LeftPanel'
                    self.style_active_panel(self.LeftPanelTree)
                if source in [self.RightPanelTree, self.RightPanelTree.viewport()]:
                    self.panel_activated = 'RightPanel'
                    self.style_active_panel(self.RightPanelTree)

                # pentru mouse
                if event.button() == Qt.MouseButton.XButton1:
                    self.GoBack()
                    return True 
                elif event.button() == Qt.MouseButton.XButton2:
                    self.GoNext()
                    return True
        return super().eventFilter(source, event) # se termina de verificat eventul, si se intra in functia lui pentru a continua exectutia
    
    def style_active_panel(self, active_tree=None):
        # If no tree is passed (like during a theme switch), find the current one
        if active_tree is None:
            if self.panel_activated == 'Left': 
                active_tree = self.LeftTree
            elif self.panel_activated == 'Right': 
                active_tree = self.RightTree
            elif self.panel_activated == 'LeftPanel': 
                active_tree = self.LeftPanelTree
            else: 
                active_tree = self.RightPanelTree

        all_panels = [self.LeftTree, self.RightTree, self.LeftPanelTree, self.RightPanelTree]

        for tree in all_panels:
            is_active = (tree == active_tree)
        
            if getattr(self, 'is_dark', False):
                bg, text = "#1E1E1E", "#DCDCDC"
                border = "#00A2FF" if is_active else "#444444"
            else:
                bg, text = "#FFFFFF", "#000000"
                border = "#0078D7" if is_active else "#ABABAB"

            width = "2px" if is_active else "1px"
        
            tree.setStyleSheet(f"QTreeWidget, QTreeView {{ background-color: {bg}; color: {text}; border: {width} solid {border}; }}")

    def getActivePanel(self):
        prefix = self.panel_activated
        if prefix == 'Left': 
            active_tree = self.LeftTree
        elif prefix == 'Right': 
            active_tree = self.RightTree
        elif prefix == 'LeftPanel': 
            active_tree = self.LeftPanelTree
        else:
           active_tree = self.RightPanelTree
        return active_tree, prefix

    def showContextMenu(self, position):

        #meniul cand dau click dreapta

        active_tree, prefix = self.getActivePanel()
        selected_item = active_tree.currentItem()

        if selected_item is None:
            return

        menu = QMenu(self)
        
        delete_action = menu.addAction("Sterge")
        delete_action.triggered.connect(self.DelFile)
        
        rename_action = menu.addAction("Redenumire")
        rename_action.triggered.connect(self.RenameSelected)
        
        properties_action = menu.addAction("Proprietati")
        properties_action.triggered.connect(self.ShowProperties)
        
        cut_action = menu.addAction("Taiere")
        cut_action.triggered.connect(self.CutPath)
        
        copy_action = menu.addAction("Copiere")
        copy_action.triggered.connect(self.CopyPath)

        paste_action = menu.addAction("Lipire")
        paste_action.triggered.connect(self.PastePath)
        
        zio_action = menu.addAction("Adauga in folder zip")
        zio_action.triggered.connect(self.ZipPath)

        unzip_action = menu.addAction("Extrage din folder zip")
        unzip_action.triggered.connect(self.UnzipPath)
        
        menu.exec(active_tree.mapToGlobal(position))

    def apply_dark_theme(self):
        self.is_dark = True
        # Fix the Window Panes and Menus
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(45, 45, 45))
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.white)
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(30, 30, 30))
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.white)
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(45, 45, 45))
        palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.white)
        QApplication.setPalette(palette)

        # Fix Buttons (Blue background on hover)
        self.setStyleSheet("""
            QPushButton { background-color: #3D3D3D; color: white; border: 1px solid #555; padding: 5px; }
            QPushButton:hover { background-color: #0078D7; color: white; }
            QLineEdit { background-color: #1E1E1E; color: white; border: 1px solid #555; }
            QMenuBar::item:selected { background-color: #0078D7; color: white; }
            QMenu::item:selected { background-color: #0078D7; color: white; }
        """)
        self.style_active_panel()

    def apply_light_theme(self):
        self.is_dark = False
    
        QApplication.setPalette(QApplication.style().standardPalette())

        # 2. 
        self.setStyleSheet("""
            QDialog, QWidget { 
                background-color: #f0f0f0; 
                color: black; 
            }
            QPushButton { 
                background-color: #e1e1e1; 
                color: black; 
                border: 1px solid #adadad; 
                padding: 6px; 
                border-radius: 2px;
            }
            QPushButton:hover { 
                background-color: #e5f1fb; 
                border: 1px solid #0078d7; 
            }
            QLineEdit { 
                background-color: white; 
                color: black; 
                border: 1px solid #adadad; 
            }
            QMenuBar::item:selected { background-color: #e5f1fb; color: black; }
            QMenu::item:selected { background-color: #0078D7; color: white; }
        """)
    
        # 3. IMMEDIATELY update the interior panels (The Trees)
        self.style_active_panel()

    def auto_detect_theme(self):
        try:
            # Windows detection via registry (most reliable on Windows 10/11)
            if sys.platform.startswith("win"):
                try:
                    import winreg
                    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                        # 0 => dark, 1 => light
                        is_dark = (val == 0)
                except Exception:
                    # registry read failed -> fallback to palette
                    print("Registry read failed")
                    pal = QApplication.instance().palette()
                    is_dark = pal.window().color().lightness() < 128

            # macOS detection via `defaults` command
            elif sys.platform == "darwin":
                try:
                    import subprocess
                    p = subprocess.run(
                        ["defaults", "read", "-g", "AppleInterfaceStyle"],
                        capture_output=True, text=True, check=False
                    )
                    is_dark = "Dark" in p.stdout
                except Exception:
                    pal = QApplication.instance().palette()
                    is_dark = pal.window().color().lightness() < 128

            # Other (Linux/Wayland/other): use Qt palette as best-effort
            else:
                print("Fallback to pallete")
                pal = QApplication.instance().palette()
                is_dark = pal.window().color().lightness() < 128

        except Exception as e:
            print(f"auto_detect_theme: detection failed ({e}), falling back to light")
            is_dark = False

        if is_dark:
            print("Applying dark theme")
            self.apply_dark_theme()
        else:
            print("Applying light theme")
            self.apply_light_theme()

    def NavigateToPathLeft(self):
        address = self.LeftPathLine.text()
        if not address:
            QMessageBox.warning(self, "Atentie", "Va rugam introduceti o cale sau o adresa.")
            return

        #active_tree, prefix = self.getActivePanel()
        active_tree = self.LeftTree
        prefix = "Left"
        current_path_attr = 'currentPath' + prefix

        try:
            target_path = Path(address).resolve()

            if target_path.is_dir():
                
                history_back = getattr(self, f'PathHistoryBack{prefix}')
                history_next = getattr(self, f'PathHistoryNext{prefix}')
                
                history_back.append(getattr(self, current_path_attr))
                history_next.clear()
                
                setattr(self, current_path_attr, target_path)
                
                self.setupTree(active_tree, target_path)
                self.LeftPathLine.setText(str(target_path))
                
                # FIX FINAL: Forteaza focusul inapoi pe Tree Widget-ul activ
                active_tree.setFocus() 
                print(f"Navigare la director: {target_path}")

            elif target_path.is_file():
                os.startfile(str(target_path))
                print(f"Fisier deschis: {target_path}")
                
                # FIX FINAL: Forteaza focusul inapoi pe Tree Widget-ul activ
                active_tree.setFocus()
                
            else:
                QMessageBox.warning(self, "Eroare", f"Calea specificata nu este un director sau fisier valid.")

        except FileNotFoundError:
            QMessageBox.warning(self, "Eroare", f"Calea '{address}' nu a fost gasita.")
        except PermissionError:
            QMessageBox.critical(self, "Eroare de Permisiune", f"Acces interzis la calea '{address}'.")
        except Exception as e:
            if address.startswith(('http://', 'https://')):
                webbrowser.open(address)
            else:
                 QMessageBox.critical(self, "Eroare", f"Eroare la procesarea caii: {e}")

    def NavigateToPathRight(self):
        address = self.RightPathLine.text()
        if not address:
            QMessageBox.warning(self, "Atentie", "Va rugam introduceti o cale sau o adresa.")
            return

        #active_tree, prefix = self.getActivePanel()
        active_tree = self.RightTree
        prefix = "Right"
        current_path_attr = 'currentPath' + prefix

        try:
            target_path = Path(address).resolve()

            if target_path.is_dir():
                
                history_back = getattr(self, f'PathHistoryBack{prefix}')
                history_next = getattr(self, f'PathHistoryNext{prefix}')
                
                history_back.append(getattr(self, current_path_attr))
                history_next.clear()
                
                setattr(self, current_path_attr, target_path)
                
                self.setupTree(active_tree, target_path)
                self.RightPathLine.setText(str(target_path))
                
                # FIX FINAL: Forteaza focusul inapoi pe Tree Widget-ul activ
                active_tree.setFocus() 
                print(f"Navigare la director: {target_path}")

            elif target_path.is_file():
                os.startfile(str(target_path))
                print(f"Fisier deschis: {target_path}")
                
                # FIX FINAL: Forteaza focusul inapoi pe Tree Widget-ul activ
                active_tree.setFocus()
                
            else:
                QMessageBox.warning(self, "Eroare", f"Calea specificata nu este un director sau fisier valid.")

        except FileNotFoundError:
            QMessageBox.warning(self, "Eroare", f"Calea '{address}' nu a fost gasita.")
        except PermissionError:
            QMessageBox.critical(self, "Eroare de Permisiune", f"Acces interzis la calea '{address}'.")
        except Exception as e:
            if address.startswith(('http://', 'https://')):
                webbrowser.open(address)
            else:
                 QMessageBox.critical(self, "Eroare", f"Eroare la procesarea caii: {e}")

    def RenameSelected(self):
        active_tree, prefix = self.getActivePanel()
        selected_item = active_tree.currentItem()
        current_path_attr = 'currentPath' + prefix
        current_dir = getattr(self, current_path_attr)
        
        if not selected_item:
            return

        old_path_str = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        old_name = selected_item.text(0)
        
        if old_name == "..":
            QMessageBox.warning(self, "Eroare", "Nu puteti redenumi directorul parinte (..).")
            return

        new_name, ok = QInputDialog.getText(self, 'Redenumire', 'Introduceti noul nume:', QLineEdit.EchoMode.Normal, old_name)
        
        if ok and new_name and new_name != old_name:
            old_path = Path(old_path_str)
            new_path = old_path.parent / new_name

            try:
                os.rename(old_path, new_path)
                
                self.setupTree(active_tree, current_dir)
            except Exception as e:
                QMessageBox.critical(self, "Eroare", f"Redenumirea a esuat: {e}")

    def CopyPath(self):
        active_tree, prefix = self.getActivePanel()
        selected_item = active_tree.currentItem()

        if selected_item is None:
            QMessageBox.warning(self, "Atentie", "Va rugam selectati un element.")
            return

        path_str = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        
        if not path_str:
            QMessageBox.warning(self, "Eroare", "Calea elementului nu a putut fi citita.")
            return

        try:
            self.clipboard_path = Path(path_str)
            self.clipboard_operation = 'Copy'
            
            # Copiaza calea in clipboard-ul de sistem (optional, pentru compatibilitate)
            clipboard_sys = QApplication.clipboard()
            clipboard_sys.setText(path_str)
            
            QMessageBox.information(self, "Succes", f"Elementul '{self.clipboard_path.name}' a fost copiat.")
            
        except Exception as e:
            QMessageBox.critical(self, "Eroare", f"Copierea caii a esuat: {e}")
    def CutPath(self):
        active_tree, prefix = self.getActivePanel()
        selected_item = active_tree.currentItem()

        if selected_item is None or selected_item.text(0) == "..":
            QMessageBox.warning(self, "Atentie", "Va rugam selectati un element valid.")
            return

        path_str = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        
        if not path_str:
            QMessageBox.warning(self, "Eroare", "Calea elementului nu a putut fi citita.")
            return

        try:
            self.clipboard_path = Path(path_str)
            self.clipboard_operation = 'Cut'
            
            # Copiaza calea în clipboard-ul de sistem (optional, pentru compatibilitate)
            clipboard_sys = QApplication.clipboard()
            clipboard_sys.setText(path_str)
            
            QMessageBox.information(self, "Succes", f"Elementul '{self.clipboard_path.name}' a fost taiat.")
            
        except Exception as e:
            QMessageBox.critical(self, "Eroare", f"Taierea caii a esuat: {e}")
    def PastePath(self):
        source_path = self.clipboard_path
        operation = self.clipboard_operation

        active_tree, prefix = self.getActivePanel()
        current_path_attr = 'currentPath' + prefix
        destination_dir = getattr(self, current_path_attr)
        
        # Verifica daca exista ceva in clipboard
        if source_path is None:
            QMessageBox.warning(self, "Atentie", "Nu este niciun element copiat/taiat.")
            return
        
        # Nu poti muta/copia un director in el insusi sau in subdirectorul sau
        if destination_dir.is_relative_to(source_path):
             QMessageBox.critical(self, "Eroare", "Directorul destinatie nu poate fi sursa sau un subdirector al sursei.")
             return
             
        # Construieste calea destinatie completa
        destination_path = destination_dir / source_path.name
        
        # Verifica daca elementul exista deja la destinatie (pentru a evita suprascrierea accidentala)
        if destination_path.exists():
            reply = QMessageBox.question(self, 'Confirmare Suprascriere',
                                         f"Elementul '{source_path.name}' exista deja. Doriti sa il suprascrieti?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            if operation == 'Copy':
                # Folosim copy2 pentru a pastra metadatele fisierului
                if source_path.is_dir():
                    shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_path, destination_path)
                message = f"Elementul '{source_path.name}' a fost copiat in:\n{destination_dir}"
                
            elif operation == 'Cut':
                # Folosim move (redenumire/mutare)
                shutil.move(str(source_path), str(destination_path))
                message = f"Elementul '{source_path.name}' a fost mutat in:\n{destination_dir}"
                
                # Dupa mutare, sterge starea clipboard-ului
                self.clipboard_path = None
                self.clipboard_operation = ''
                
            else:
                QMessageBox.critical(self, "Eroare", "Operatie clipboard necunoscuta.")
                return

            QMessageBox.information(self, "Succes", message)
            
            # Reimprospateaza ambele panouri dupa o operatie reusita (sursa si destinatia)
            self.setupTree(self.LeftTree, self.currentPathLeft)
            self.setupTree(self.RightTree, self.currentPathRight)
            
        except PermissionError:
            QMessageBox.critical(self, "Eroare de Permisiune", 
                                 f"Acces interzis pentru {operation} in directorul: {destination_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Eroare", f"Lipirea a esuat. Eroare: {e}")
    def UnzipPath(self):
        active_tree, prefix = self.getActivePanel()
        selected_item = active_tree.currentItem()

        if not selected_item:
            QMessageBox.warning(self, "Atentie", "Selectati un element pentru dezarhivare.")
            return

        path_str = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        source_path = Path(path_str)

        # Verificam ca este un zip
        if source_path.suffix.lower() != '.zip':
            QMessageBox.warning(self, "Atentie", "Elementul selectat nu este o arhiva ZIP.")
            return
    
        # Numele viitoarei arhive (ex: document.zip -> document)
        dest_dir = source_path.parent / (source_path.stem)

        try:
            dest_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(source_path, 'r') as zip_ref:
                # Extragem tot conținutul
                zip_ref.extractall(dest_dir)
        
            # Refresh panou pentru a vedea noul folder extras
            self.setupTree(active_tree, getattr(self, f'currentPath{prefix}'))
        
            QMessageBox.information(self, "Succes", f"Arhiva a fost extrasa in:\n{dest_dir.name}")

        except Exception as e:
            QMessageBox.critical(self, "Eroare", f"Extractia a esuat: {e}")
    def ZipPath(self):
        active_tree, prefix = self.getActivePanel()
        selected_item = active_tree.currentItem()

        if not selected_item:
            QMessageBox.warning(self, "Atentie", "Selectati un element pentru arhivare.")
            return

        path_str = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        source_path = Path(path_str)
    
        # Numele viitoarei arhive (ex: document.txt -> document.zip)
        zip_name = source_path.parent / (source_path.stem + ".zip")

        try:
            if source_path.is_dir():
                # Pentru foldere, shutil.make_archive este cel mai simplu
                # Acesta creeaza arhiva si returneaza calea
                shutil.make_archive(str(source_path), 'zip', source_path.parent, source_path.name)
            else:
                # Pentru un singur fisier, folosim zipfile
                with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(source_path, source_path.name)
        
            print(f"Arhiva creata: {zip_name}")
        
            # Refresh la panelul curent pentru a vedea noul fisier .zip
            current_path = getattr(self, f'currentPath{prefix}')
            self.setupTree(active_tree, current_path)
        
            QMessageBox.information(self, "Succes", f"Arhiva a fost creata:\n{zip_name.name}")

        except Exception as e:
            QMessageBox.critical(self, "Eroare", f"Arhivarea a esuat: {e}")

    def ShowProperties(self):
        active_tree, prefix = self.getActivePanel()
        selected_item = active_tree.currentItem()
        
        if not selected_item:
            return
            
        path_str = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        name = selected_item.text(0)
        ext = selected_item.text(2)
        
        try:
            stats = Path(path_str).stat()
            size_bytes = stats.st_size
            creation_time = datetime.datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            
            details = (f"Proprietati pentru: {name}\n"
                       f"Tip: {'Director' if ext == 'DIR' else 'Fisier'}\n"
                       f"Cale completa: {path_str}\n"
                       f"Marime (octeti): {size_bytes:,}\n"
                       f"Creat la: {creation_time}\n"
                       f"Ultima modificare: {selected_item.text(3)}")                       

            QMessageBox.information(self, f"Proprietati: {name}", details)
            
        except Exception as e:
            QMessageBox.critical(self, "Eroare", f"Nu s-au putut obtine proprietatile: {e}")
    def MouseButtonPress(self, event):
        if event.button() == Qt.MouseButton.XButton1:
            self.GoBack()
        elif event.button() == Qt.MouseButton.XButton2:
            self.GoNext()
        else:
            super().mousePressEvent(event)
           
    def OpenItem(self, item, column):
        sender_widget = self.sender()
        selected_item = item

        if not selected_item:
            return

        selected_path_str = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        item_ext = selected_item.text(2)

        if not selected_path_str:
            return

        selected_path = Path(selected_path_str)

        if item_ext == "DIR":
            if selected_path.is_dir():
                
                if sender_widget == self.LeftTree:
                    self.PathHistoryBackLeft.append(self.currentPathLeft)
                    self.PathHistoryNextLeft = []
                    self.currentPathLeft = selected_path
                    self.setupTree(self.LeftTree, selected_path)
                    self.panel_activated = 'Left'
                    self.LeftPathLine.setText(str(selected_path))
                else:
                    self.PathHistoryBackRight.append(self.currentPathRight)
                    self.PathHistoryNextRight = []
                    self.currentPathRight = selected_path
                    self.setupTree(self.RightTree, selected_path)
                    self.panel_activated = 'Right'
                    self.RightPathLine.setText(str(selected_path))
                
                self.style_active_panel(sender_widget)

        else:
            try:
                os.startfile(selected_path_str)
                print(f"Fisier deschis pentru editare/vizualizare: {selected_path_str}")
            except Exception as e:
                QMessageBox.warning(self, "Eroare la deschidere", 
                                    f"Nu s-a putut deschide fisierul. Eroare: {e}")
    def AddFile(self):
        
        ActiveTree, prefix = self.getActivePanel()
        CurrentPath = getattr(self, f'currentPath{prefix}')
        
        self.style_active_panel(ActiveTree)

        name, ok = QInputDialog.getText(self, 'Creare director nou', 'Introduceti numele directorului:')

        if ok and name:
            newFilePath = CurrentPath / name
            try:
                newFilePath.mkdir(parents=True, exist_ok=False)
                print(f"Director nou creat: {newFilePath}")
                
                self.setupTree(ActiveTree, CurrentPath) 
                
            except PermissionError:
                QMessageBox.critical(self, "Eroare de Permisiune", 
                    f"Nu aveti permisiunea de a scrie in directorul: {CurrentPath}")
            except FileExistsError:
                 QMessageBox.warning(self, "Eroare", f"Directorul '{name}' exista deja.")
            except Exception as e:
                QMessageBox.warning(self, "Eroare", f"Crearea directorului a esuat din cauza: {e}")     
    def GoBack(self):
        active_tree, prefix = self.getActivePanel()
        current_path_attr = 'currentPath' + prefix
        
        history_back = getattr(self, f'PathHistoryBack{prefix}')
        history_next = getattr(self, f'PathHistoryNext{prefix}')
        
        self.style_active_panel(active_tree)

        if history_back:
            history_next.append(getattr(self, current_path_attr))
            new_path = history_back.pop()

            setattr(self, current_path_attr, new_path)
            self.setupTree(active_tree, new_path)
            self.LeftPathLine.setText(str(new_path))
            print(f"Inapoi la: {new_path}")
        else:
            print("Nu exista istoric anterior.")
    def GoNext(self):
        active_tree, prefix = self.getActivePanel()
        current_path_attr = 'currentPath' + prefix
        
        history_back = getattr(self, f'PathHistoryBack{prefix}')
        history_next = getattr(self, f'PathHistoryNext{prefix}')
        
        self.style_active_panel(active_tree)

        if history_next:
            history_back.append(getattr(self, current_path_attr))
            new_path = history_next.pop()
            
            setattr(self, current_path_attr, new_path)
            self.setupTree(active_tree, new_path)
            self.LeftPathLine.setText(str(new_path))
            print(f"Inainte la: {new_path}")
        else:
            print("Nu exista istoric ulterior.")

    def DelFile(self):
        
        active_tree, prefix = self.getActivePanel()
        selected_item = active_tree.currentItem()
        current_path = getattr(self, f'currentPath{prefix}')
        
        self.style_active_panel(active_tree)

        if not selected_item:
            QMessageBox.warning(self, "Atentie", "Va rugam selectati un fisier sau director de sters.")
            return

        selected_path_str = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        item_name = selected_item.text(0)
        item_ext = selected_item.text(2)
        
        if item_name == "..":
            QMessageBox.warning(self, "Eroare", "Nu puteti sterge directorul parinte (..).")
            return

        is_dir = (item_ext == "DIR")
        confirm_text = "Directorul" if is_dir else "Fisierul"
        
        reply = QMessageBox.question(self, 'Confirmare Stergere',
                                     f"Sunteti sigur ca doriti sa stergeti {confirm_text}:\n{item_name}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if is_dir:
                    shutil.rmtree(selected_path_str)
                else:
                    os.remove(selected_path_str)
                
                print(f"Sters cu succes: {selected_path_str}")
                
                self.setupTree(active_tree, current_path) 
                
            except PermissionError:
                QMessageBox.critical(self, "Eroare de Permisiune", 
                                     f"Nu aveti permisiunea de a sterge elementul: {item_name}.")
            except Exception as e:
                QMessageBox.critical(self, "Eroare de I/O", 
                                     f"Stergerea a esuat. Eroare: {e}")
    def SortColumns(self):
        self.LeftTree.setSortingEnabled(True)
        self.RightTree.setSortingEnabled(True)
        
        self.LeftTree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        self.RightTree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
    
    def setupTree(self, tree_widget: QTreeWidget, path: Path):
        tree_widget.clear()
        parent_path = path.parent.resolve()

        icon_provider = QFileIconProvider()

        if parent_path != path:
            item_parent = QTreeWidgetItem(tree_widget, ["..", "", "DIR", ""])
            item_parent.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(parent_path))
            item_parent.setIcon(0, icon_provider.icon(QFileIconProvider.IconType.Folder))

        try:
            contents = list_directory_contents(str(path))
        except Exception as e:
            print(f"Eroare la citirea directorului {path}: {e}")
            return

        for item in contents:
            name_str = item['name']
            size_str = f"{item['size']:,}" if item['is_file'] else ''
            ext = str(item['ext']) if item['is_file'] else 'DIR'
            date_mod = str(item['modify_date'])[:16]

            tree_item = QTreeWidgetItem(tree_widget, [name_str, size_str, ext, date_mod])
            tree_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, item['path']) 

            file_info = QFileInfo(item['path'])
            icon = icon_provider.icon(file_info)
            tree_item.setIcon(0, icon)

    def setupPanel(self):
        self.model = QFileSystemModel()
        self.model.setRootPath("") 
        self.model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden | QDir.Filter.System)

        self.LeftPanelTree.setModel(self.model)
        self.RightPanelTree.setModel(self.model)

        for i in range(1, self.model.columnCount()):
            self.LeftPanelTree.setColumnHidden(i, True)
            self.RightPanelTree.setColumnHidden(i, True)
    
        self.LeftPanelTree.header().hide()
        self.LeftPanelTree.setAnimated(True)
        self.LeftPanelTree.setIndentation(10)
        self.RightPanelTree.header().hide()
        self.RightPanelTree.setAnimated(True)
        self.RightPanelTree.setIndentation(10)

        root_index = self.model.index("")
        self.LeftPanelTree.expand(root_index)
        self.RightPanelTree.expand(root_index)

        self.LeftPanelTree.clicked.connect(self.LeftPanelClick)
        self.RightPanelTree.clicked.connect(self.RightPanelClick)
        # Obținem obiectul header al TreeView-ului
        header = self.LeftPanelTree.header()

        # 1. Permitem coloanelor să iasă din cadrul vizibil (activează scroll-ul)
        header.setStretchLastSection(False)

        # 2. Setăm prima coloană (cea cu numele) să se auto-dimensioneze
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        
        header = self.RightPanelTree.header()

        # 1. Permitem coloanelor să iasă din cadrul vizibil (activează scroll-ul)
        header.setStretchLastSection(False)

        # 2. Setăm prima coloană (cea cu numele) să se auto-dimensioneze
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)


    def LeftPanelClick(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            active_tree = self.LeftTree
            prefix = "Left"
            setattr(self, f'currentPath{prefix}', Path(path))
            self.setupTree(active_tree, Path(path))
            self.LeftPathLine.setText(path)

    def RightPanelClick(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            active_tree = self.RightTree
            prefix = "Right"
            setattr(self, f'currentPath{prefix}', Path(path))
            self.setupTree(active_tree, Path(path))
            self.RightPathLine.setText(path)

    def OpenSearch(self):
        active_tree = self.getActivePanel()
        if "Left" in str(active_tree):
            prefix = "Left"
        else:
            prefix = "Right"
        current_path = getattr(self, f'currentPath{prefix}')
    
        dialog = SearchDialog(current_path, self)
        # Connect signal to search class:
        dialog.location_selected.connect(self.JumpToLocation)
        dialog.exec()

    def JumpToLocation(self, folder_path, file_name):
        # This function receives the data from the search window
        active_tree, prefix = self.getActivePanel()
    
        # 1. Update the internal current path variable
        setattr(self, f'currentPath{prefix}', Path(folder_path))
    
        # 2. Update the Path input bar (Changed 'Path' to 'Find')
        path_line_edit = getattr(self, f'{prefix}FindPathButton') 
        path_line_edit.setText(folder_path)
    
        # 3. Refresh the tree widget
        self.RefreshPanels()
    
        # 4. Find and select the specific file
        # We wait a tiny bit for the tree to populate
        QtCore.QTimer.singleShot(100, lambda: self.select_file_in_tree(active_tree, file_name))

    def select_file_in_tree(self, tree, file_name):
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if item.text(0) == file_name:
                tree.setCurrentItem(item)
                tree.scrollToItem(item)
                break

    def handle_drop(self, event, source_tree, target_tree):
        # Verify mime format
        if not event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            return

        # Get the actual source widget that started the drag
        source_tree = event.source()
        if source_tree is None:
            return

        selected_items = source_tree.selectedItems()
        if not selected_items:
            return

        # Resolve the item under the mouse in the target tree (exact drop target)
        try:
            # PyQt6: position() -> QPointF
            pos = event.position().toPoint()
        except Exception:
            # fallback for other versions
            pos = event.pos()

        target_item = target_tree.itemAt(pos)

        # Determine destination directory from the item under cursor (or from currentPath if none)
        if target_item:
            target_item_path_str = target_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            try:
                if target_item_path_str:
                    targ_path = Path(target_item_path_str)
                    # If the target item is a directory, drop into it; otherwise drop into its parent
                    drop_dir = targ_path if targ_path.is_dir() else targ_path.parent
                else:
                    # no stored path -> fallback to panel current path
                    prefix_target = "Left" if target_tree is self.LeftTree else "Right"
                    drop_dir = getattr(self, f'currentPath{prefix_target}')
            except Exception:
                prefix_target = "Left" if target_tree is self.LeftTree else "Right"
                drop_dir = getattr(self, f'currentPath{prefix_target}')
        else:
            # No item under cursor -> drop into the panel's current directory
            prefix_target = "Left" if target_tree is self.LeftTree else "Right"
            drop_dir = getattr(self, f'currentPath{prefix_target}')

        # Determine source directory / paths using the selected items' stored UserRole (full paths)
        prefix_source = "Left" if source_tree is self.LeftTree else "Right"
        # Note: we still keep the panel currentPath for any needed comparisons, but use the item's stored path as source.
        for item in selected_items:
            file_path_str = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if not file_path_str:
                continue
            src_path = Path(file_path_str)
            dst_path = drop_dir / src_path.name

            # Prevent dropping a folder into itself or its children
            try:
                if src_path == dst_path or dst_path.is_relative_to(src_path):
                    QMessageBox.warning(self, "Eroare", "Nu puteti muta/copiere un director in el insusi sau intr-un subdirector al sau.")
                    event.ignore()
                    return
            except Exception:
                # is_relative_to might raise on unusual paths; ignore and continue but be conservative
                pass

            # Check overwrite and perform copy/move
            try:
                is_ctrl_pressed = bool(event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier)

                if is_ctrl_pressed:
                    # Copy
                    if src_path.is_dir():
                        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src_path, dst_path)
                    print(f"Copiat: {src_path} -> {dst_path}")
                else:
                    # Move
                    shutil.move(str(src_path), str(dst_path))
                    print(f"Mutat: {src_path} -> {dst_path}")

            except Exception as e:
                print(f"Eroare la procesarea elementului {src_path}: {e}")
                QMessageBox.warning(self, "Eroare", f"Nu s-a putut procesa {src_path.name}: {e}")

        # Refresh both panels and accept the event
        self.RefreshPanels()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    myapp = MyApp()
    myapp.show()
    sys.exit(app.exec())
    