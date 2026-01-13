from CommonImports import *
from SearchDialog import SearchDialog
from Settings import SettingsMenu, SizeInputDialog, DefaultPathDialog

CONFIG_FILE = "settings.json"
SHOW_EXTRA_MESSAGES = True

def load_settings():
    # Verificăm dacă există discul D, altfel punem C ca default pentru panoul drept
    default_right = "D:/" if Path("D:/").exists() else "C:/"
    
    defaults = {
        "left_path": "C:/", 
        "right_path": default_right,
        "show_extra_messages": True
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                # Use .get() to avoid errors if the key is missing from an old file
                defaults.update(loaded)
                return defaults
        except Exception as e:
            print(f"Eroare la citirea setărilor: {e}")
            return defaults
    return defaults

def save_settings(left, right, show_messages):
    with open(CONFIG_FILE, "w") as f:
        # Save all three parameters to the JSON file
        json.dump({
            "left_path": str(left), 
            "right_path": str(right),
            "show_extra_messages": show_messages
        }, f)

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

    LeftLabel : QLabel
    RightLabel : QLabel

    currentPathLeft: Path
    currentPathRight: Path
    panel_activated: str
    clipboard: Path

    def __init__(self):
        super().__init__()
        loadUi('Display.ui', self)

        self.setMinimumWidth(400) 
        self.frameTreesLeft.setMinimumWidth(50)
        self.frameTreesRight.setMinimumWidth(50)
        self.LeftTree.setMinimumWidth(0)
        self.RightTree.setMinimumWidth(0)
        self.setWindowTitle("My Commander")
        global SHOW_EXTRA_MESSAGES
        
        self.all_buttons = self.findChildren(QtWidgets.QAbstractButton)
        self.all_panels = [self.LeftTree, self.RightTree, self.LeftPanelTree, self.RightPanelTree]
        self.setWindowState(QtCore.Qt.WindowState.WindowMaximized)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMinimizeButtonHint | QtCore.Qt.WindowType.WindowMaximizeButtonHint) # creaza butonul de full screen
        self.buttons = self.findChildren(QPushButton)
        for btn in self.buttons:
            btn.clicked.connect(self.shortCutButton)
            btn.setAutoDefault(False)
            btn.setDefault(False)

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

        # Înlocuiește lambda-urile vechi cu acestea:
        self.LeftTree.dragEnterEvent = self.custom_drag_enter
        self.LeftTree.dragMoveEvent = self.custom_drag_enter # Folosim aceeași logică
        self.LeftTree.dropEvent = lambda event: self.handle_drop(event, self.LeftTree)

        self.RightTree.dragEnterEvent = self.custom_drag_enter
        self.RightTree.dragMoveEvent = self.custom_drag_enter
        self.RightTree.dropEvent = lambda event: self.handle_drop(event, self.RightTree)
        
        self.is_dark = False

        self.adjustSize() 
        self.update()

        # vectori care memoreaza adresa curenta si anterioara ptr fiecare din arbori
        self.PathHistoryBackLeft = []
        self.PathHistoryBackRight = []
        self.PathHistoryNextLeft = []
        self.PathHistoryNextRight = []

        #discul afisat (default)
        settings = load_settings()
        self.currentPathLeft = Path(settings['left_path'])
        if not self.currentPathLeft.exists(): 
            self.currentPathLeft = Path("C:/")

        self.currentPathRight = Path(settings['right_path'])
        if not self.currentPathRight.exists():
            self.currentPathRight = Path("C:/")

        SHOW_EXTRA_MESSAGES = settings.get('show_extra_messages', True)
        
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

        # Delete - Recycle Bin
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self).activated.connect(self.TrashFile)

        # Ctrl + Del - Stergere
        QShortcut(QKeySequence("Ctrl+Del"), self).activated.connect(self.DelFile)

        # Ctrl + X pentru Tăiere (Cut)
        QShortcut(QKeySequence.StandardKey.Cut, self).activated.connect(self.CutPath)

        # Săgeată Stânga (Back)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self).activated.connect(self.GoBack)

        # Săgeată Dreapta (Next)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self).activated.connect(self.GoNext)
        
        self.auto_detect_theme()

    def update_disk_info(self, path, label_to_update):
        try:
            usage = psutil.disk_usage(str(path))
        
            free_k = usage.free // 1024
            total_k = usage.total // 1024
        
            f_free = f"{free_k:,}"
            f_total = f"{total_k:,}"
        
            text = f"[_none_] {f_free} k of {f_total} k free"

            label_to_update.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_to_update.setText(text)
        
        except Exception as e:
            print(f"Eroare la citirea adresei {path}: {e}")

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
        
            self.LeftLabel.setFont(font)
            self.RightLabel.setFont(font)

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

    def openDefaultPathSettings(self):
        settings = load_settings()
        dialog = DefaultPathDialog(settings['left_path'], settings['right_path'], self)
        if dialog.exec() == QDialog.DialogCode.Accepted and SHOW_EXTRA_MESSAGES:
            QMessageBox.information(self, "Succes", "Căile default au fost salvate pentru următoarea pornire.")

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

        self.changeAction = QAction("Schimba Dimensiunea Panel-urilor", self)
        self.changeAction.triggered.connect(self.ChangeSize)
        optionsMenu.addAction(self.changeAction)

        self.defaultPathAction = QAction("Setare Directoare Start", self)
        self.defaultPathAction.triggered.connect(self.openDefaultPathSettings)
        optionsMenu.addAction(self.defaultPathAction)

        self.messageToggleAction = QAction("Afisare Mesaje Confirmare", self)
        self.messageToggleAction.setCheckable(True)
        self.messageToggleAction.setChecked(SHOW_EXTRA_MESSAGES) 
        self.messageToggleAction.triggered.connect(self.toggle_extra_messages)
        optionsMenu.addAction(self.messageToggleAction)

        # Add the menu bar to your main layout
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

    def syncSidePanelsToPaths(self, side=None):
        """
        Sincronizează arborii laterali. 
        Dacă side='Left', sincronizează doar stânga. 
        Dacă side='Right', doar dreapta. 
        Dacă e None, ambele.
        """
        # Sincronizare Stânga
        if side is None or side == 'Left':
            left_idx = self.model.index(str(self.currentPathLeft))
            if left_idx.isValid():
                self.LeftPanelTree.setCurrentIndex(left_idx)
                self.LeftPanelTree.scrollTo(left_idx, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)
                self.LeftPanelTree.expand(left_idx)

        # Sincronizare Dreapta
        if side is None or side == 'Right':
            right_idx = self.model.index(str(self.currentPathRight))
            if right_idx.isValid():
                self.RightPanelTree.setCurrentIndex(right_idx)
                self.RightPanelTree.scrollTo(right_idx, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)
                self.RightPanelTree.expand(right_idx)

    def ClearFocus(self):
        for btn in self.all_buttons:
            btn.clearFocus()

    def ConfigWidgets(self): 

        self.LeftTree.installEventFilter(self)
        self.RightTree.installEventFilter(self)
        self.LeftPathLine.installEventFilter(self)
        self.RightPathLine.installEventFilter(self)
        self.LeftPanelTree.installEventFilter(self)
        self.RightPanelTree.installEventFilter(self)
        self.LeftPanelTree.viewport().installEventFilter(self)
        self.RightPanelTree.viewport().installEventFilter(self)

        self.LeftTree.viewport().installEventFilter(self)
        self.RightTree.viewport().installEventFilter(self)

        self.LeftPathLine.setMinimumWidth(50)
        self.RightPathLine.setMinimumWidth(50)

        self.SortColumns()

        self.SetupMenu()

        self.LeftTree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.RightTree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        
        self.LeftTree.customContextMenuRequested.connect(self.showContextMenu)
        self.RightTree.customContextMenuRequested.connect(self.showContextMenu)

        self.LeftTree.itemDoubleClicked.connect(self.OpenItem)
        self.RightTree.itemDoubleClicked.connect(self.OpenItem)

        # Activăm selecția extinsă pentru ambele paneluri
        self.LeftTree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.RightTree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

        # Headers pentru coloane
        self.LeftTree.setHeaderLabels(["Name", "Size", "Ext", "DateMod"])
        self.RightTree.setHeaderLabels(["Name", "Size", "Ext", "DateMod"])

        self.RefreshPanels()

        self.LeftTree.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.RightTree.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        #self.BackButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        #self.NextButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.BackButton.clicked.connect(self.GoBack)
        self.NextButton.clicked.connect(self.GoNext)
        self.butonLupa.clicked.connect(self.OpenSearch)
        self.butonRefresh.clicked.connect(self.RefreshPanels)
        self.butonCreare.clicked.connect(self.AddFile)
        self.butonArhivare.clicked.connect(self.ZipPath)
        self.butonDezarhivare.clicked.connect(self.UnzipPath)

        self.style_active_panel(self.LeftTree)

        self.refresh_memory_labels()

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
        if 'Del - Recycle Bin' in text: self.TrashFile()
        if 'CTRL + Del - Stergere' in text: self.DelFile()
        if 'CTRL + C - Copiere' in text: self.CopyPath()
        if 'CTRL + V - Lipire' in text: self.PastePath()
        if 'CTRL + X - Taiere' in text: self.CutPath()
        if 'CTRL + F5 - Dezarhivare' in text: self.UnzipPath()
        if 'Setari' in text: self.openSettings()
    
    def eventFilter(self, source, event):
        # Detectare Mouse Press pentru a salva poziția de start a drag-ului
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if source in [self.LeftTree, self.LeftTree.viewport(), self.RightTree, self.RightTree.viewport()]:
                self.drag_start_pos = event.pos()

        # Detectare Mouse Move pentru a iniția Drag-ul spre EXTERIOR
        if event.type() == QtCore.QEvent.Type.MouseMove:
            if source in [self.LeftTree, self.LeftTree.viewport(), self.RightTree, self.RightTree.viewport()]:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    # Verificăm dacă mouse-ul s-a mișcat suficient pentru a fi considerat drag
                    if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                        # Identificăm arborele corect (chiar dacă sursa e viewport-ul)
                        actual_tree = self.LeftTree if source in [self.LeftTree, self.LeftTree.viewport()] else self.RightTree
                        self.perform_external_drag(actual_tree)
                        return True # Consumăm evenimentul

        # Detectare focus 
        if event.type() == QtCore.QEvent.Type.FocusIn: #pentru tree uri
            # Clear focus pentru butoane ca Enter sa functioneze in paneluri
            self.ClearFocus()
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

        if event.type() == QtCore.QEvent.Type.KeyPress:
            # --- Logica pentru Tasta ENTER ---
            if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                # Dacă suntem în listele principale de fișiere
                if source in [self.LeftTree, self.LeftTree.viewport(), self.RightTree, self.RightTree.viewport()]:
                    tree = self.LeftTree if source in [self.LeftTree, self.LeftTree.viewport()] else self.RightTree
                    item = tree.currentItem()
                    if item:
                        self.OpenItem(item, 0, manual_widget=tree)
                    return True
                
                # NOU: Dacă suntem în panourile laterale (TreeViews)
                elif source in [self.LeftPanelTree, self.LeftPanelTree.viewport(), self.RightPanelTree, self.RightPanelTree.viewport()]:
                    tree = self.LeftPanelTree if "Left" in source.objectName() else self.RightPanelTree
                    idx = tree.currentIndex()
                    if idx.isValid():
                        # Expandează/colapsează folderul și actualizează lista principală
                        tree.setExpanded(idx, not tree.isExpanded(idx))
                        if tree == self.LeftPanelTree: self.LeftPanelClick(idx)
                        else: self.RightPanelClick(idx)
                    return True

            # --- Logica pentru Tasta BACKSPACE ---
            if event.key() == Qt.Key.Key_Backspace:
                # În listele principale, merge înapoi în istoric
                if source in [self.LeftTree, self.LeftTree.viewport(), self.RightTree, self.RightTree.viewport()]:
                    self.GoBack()
                    return True
                
                # NOU: În panourile laterale, urcă la folderul părinte
                elif source in [self.LeftPanelTree, self.LeftPanelTree.viewport(), self.RightPanelTree, self.RightPanelTree.viewport()]:
                    tree = self.LeftPanelTree if "Left" in source.objectName() else self.RightPanelTree
                    idx = tree.currentIndex()
                    parent_idx = idx.parent()
                    if parent_idx.isValid():
                        tree.setCurrentIndex(parent_idx)
                        tree.setExpanded(idx, False) # Închide folderul curent când urcă
                        # Actualizează vizualizarea principală pentru noul folder părinte
                        if tree == self.LeftPanelTree: self.LeftPanelClick(parent_idx)
                        else: self.RightPanelClick(parent_idx)
                    return True

        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if source in [self.LeftTree, self.LeftTree.viewport(), self.RightTree, self.RightTree.viewport(), self.LeftPanelTree, self.LeftPanelTree.viewport(), self.RightPanelTree, self.RightPanelTree.viewport()]:
                self.ClearFocus()
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

                actual_tree = source
                if hasattr(source, 'parent') and isinstance(source.parent(), QTreeWidget):
                    actual_tree = source.parent()
                # 3. Explicitly tell this tree to grab the keyboard focus
                # This ensures "Enter" goes to the tree, not the Back button.
                actual_tree.setFocus(Qt.FocusReason.MouseFocusReason)

                # pentru mouse
                if source in [self.LeftTree, self.LeftTree.viewport(), self.RightTree, self.RightTree.viewport()]:
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
            #if is_active:
            #    tree.clearFocus()
            #else:
            #    tree.setFocus()
        
            tree.setStyleSheet(f"QTreeWidget, QTreeView {{ background-color: {bg}; color: {text}; border: {width} solid {border}; }}")

    def getActivePanel(self):
        prefix = self.panel_activated
        if 'Right' in prefix: 
            prefix = "Right"
            active_tree = self.RightTree
        else: 
            prefix = "Left"
            active_tree = self.LeftTree
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

        trash_action = menu.addAction("Trimite la Recycle Bin")
        trash_action.triggered.connect(self.TrashFile)
        
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
        palette.setColor(QtGui.QPalette.ColorRole.PlaceholderText, QtGui.QColor(180, 180, 180))
        QApplication.setPalette(palette)

        self.setStyleSheet("""
        /* ... restul butoanelor ... */

        /* Când panoul ARE focus (Highlight albastru ca în imaginea ta) */
        QTreeWidget::item:selected:active, QTreeView::item:selected:active {
            background-color: #0078D7;
            color: white;
        }

        /* Când panoul NU ARE focus (Text ROȘU, fără fundal alb/albastru) */
        QTreeWidget::item:selected:!active, QTreeView::item:selected:!active {
            background-color: transparent;
            color: #FF5555; /* Roșu deschis pentru Dark Mode */
            font-weight: bold;
        }
        
        /* Elimină chenarul punctat de focus */
        QTreeView, QTreeWidget { outline: 0; }
    """)
        self.style_active_panel()

    def apply_light_theme(self):
            self.is_dark = False
        
            # 1. Configurăm Paleta de culori (exact ca în Dark Mode, dar cu culori de lumină)
            palette = QtGui.QPalette()
            # Fundalul ferestrei și textul
            palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(240, 240, 240))
            palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.black)
            # Fundalul listelor (TreeWidget) și textul din ele
            palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 255, 255))
            palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.black)
            # Butoanele și textul de pe ele
            palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(225, 225, 225))
            palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.black)
            # Highlight (albastru standard Windows)
            palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(0, 120, 215))
            palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.GlobalColor.white)
        
            QApplication.setPalette(palette)

            # 2. CSS-ul minim pentru comportamentul specific de selecție (Total Commander style)
            self.setStyleSheet("""
            /* Când panoul ARE focus: Fundal albastru, text alb */
            QTreeWidget::item:selected:active, QTreeView::item:selected:active {
                background-color: #0078D7;
                color: white;
            }

            /* Când panoul NU ARE focus: Text ROȘU pur, fără fundal colorat */
            QTreeWidget::item:selected:!active, QTreeView::item:selected:!active {
                background-color: transparent;
                color: red; 
                font-weight: bold;
            }
        
            /* Elimină chenarul punctat de focus inestetic */
            QTreeView, QTreeWidget { outline: 0; }
        """)
        
            # 3. Aplicăm bordurile de panel activ/inactiv
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

    def toggle_extra_messages(self):
        global SHOW_EXTRA_MESSAGES
        SHOW_EXTRA_MESSAGES = self.messageToggleAction.isChecked()
        
        # Save the current state along with the paths
        save_settings(self.currentPathLeft, self.currentPathRight, SHOW_EXTRA_MESSAGES)
        
        if SHOW_EXTRA_MESSAGES:
            print("Mesajele extra au fost activate.")
        else:
            print("Mesajele extra au fost dezactivate.")

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
                self.syncSidePanelsToPaths('Left')
                
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
                self.syncSidePanelsToPaths('Right')
                
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
        active_tree, _ = self.getActivePanel()
        items = active_tree.selectedItems()
        if not items: return
        # Salvăm lista de căi
        self.clipboard_paths = [Path(i.data(0, Qt.ItemDataRole.UserRole)) for i in items if i.text(0) != ".."]
        self.clipboard_operation = 'Copy'

        count = len(self.clipboard_paths)
        copiate = "element a fost pus in" if count == 1 else "elemente au fost pus in"
        if SHOW_EXTRA_MESSAGES:
            QMessageBox.information(self, "Clipboard", f"{count} {copiate} clipboard.")

    def CutPath(self):
        self.CopyPath()
        self.clipboard_operation = 'Cut'

    def PastePath(self):
        if not hasattr(self, 'clipboard_paths') or not self.clipboard_paths:
            return
    
        active_tree, prefix = self.getActivePanel()
        dest_dir = getattr(self, f'currentPath{prefix}')
        
        total_files = len(self.clipboard_paths)
        # Marcăm că aceasta este o operațiune explicita de clipboard
        self.is_clipboard_paste = True
        self.current_active_op = self.clipboard_operation

        self.pd = QtWidgets.QProgressDialog("Pregătire...", "Anulează", 0, total_files, self)
        self.pd.setWindowTitle("Operațiune în curs")
        self.pd.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.pd.setMinimumDuration(500) # Apare dupa 0.25 secunde
        self.pd.setAutoClose(True)

        self.file_worker = FileOperationWorker(self.clipboard_paths, dest_dir, self.clipboard_operation)
    
        # Conectăm semnalul de progres la dialog
        self.file_worker.progress.connect(lambda idx, name: self.pd.setValue(idx) or self.pd.setLabelText(f"Procesare: {name}"))
    
        self.file_worker.finished.connect(self.on_operation_complete)
        self.file_worker.error.connect(self.on_operation_error)
        self.pd.canceled.connect(self.file_worker.stop) # Trimite semnalul de oprire la threadF
        self.file_worker.start()

    def on_operation_complete(self, message):
        # 1. Verificăm dacă utilizatorul a anulat operațiunea (prin butonul Anulează sau prin X-ul ferestrei)
        if hasattr(self, 'pd') and self.pd.wasCanceled():
            # Dacă a fost anulat, închidem worker-ul și reîmprospătăm panourile fără a mai afișa mesajul final
            self.RefreshPanels()
            self.refresh_memory_labels()
            return

        if hasattr(self, 'pd'): self.pd.close() 
        self.RefreshPanels()
        self.refresh_memory_labels()

        # Folosim current_active_op pentru mesaj
        op_name = "Mutarea" if self.current_active_op == 'Cut' else "Copierea"

        # Mesajul de succes se afișează doar dacă setarea este activă și operațiunea NU a fost anulată
        if SHOW_EXTRA_MESSAGES:
            QMessageBox.information(self, "Operațiune Finalizată", f"{op_name} s-a încheiat.\n{message}")
    
        # RESETARE CLIPBOARD: Doar dacă a fost Cut manual și Paste manual
        if getattr(self, 'is_clipboard_paste', False) and self.clipboard_operation == 'Cut':
            self.clipboard_paths = []
            self.clipboard_operation = ''
        
        self.is_clipboard_paste = False # Resetăm flag-ul

    def on_operation_error(self, err_msg):
        if hasattr(self, 'pd'): self.pd.close()
        QMessageBox.critical(self, "Eroare", f"Operațiunea a eșuat:\n{err_msg}")

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
        
            if SHOW_EXTRA_MESSAGES:
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
        
            if SHOW_EXTRA_MESSAGES:
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

    def refresh_memory_labels(self):

        if hasattr(self, 'LeftLabel') and self.currentPathLeft:
            self.update_disk_info(self.currentPathLeft, self.LeftLabel)
        
        if hasattr(self, 'RightLabel') and self.currentPathRight:
            self.update_disk_info(self.currentPathRight, self.RightLabel)

    def OpenItem(self, item, column, manual_widget=None):
        # Dacă manual_widget este trimis (din eventFilter), îl folosim. 
        # Altfel, folosim self.sender() (pentru double-click).
        sender_widget = manual_widget if manual_widget else self.sender()

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
                if sender_widget in  [self.LeftTree, self.LeftTree.viewport()]:
                    self.PathHistoryBackLeft.append(self.currentPathLeft)
                    self.PathHistoryNextLeft = []
                    self.currentPathLeft = selected_path
                    self.setupTree(self.LeftTree, selected_path)
                    self.panel_activated = 'Left'
                    self.LeftPathLine.setText(str(selected_path))
                    self.syncSidePanelsToPaths('Left')
                else:
                    self.PathHistoryBackRight.append(self.currentPathRight)
                    self.PathHistoryNextRight = []
                    self.currentPathRight = selected_path
                    self.setupTree(self.RightTree, selected_path)
                    self.panel_activated = 'Right'
                    self.RightPathLine.setText(str(selected_path))
                    self.syncSidePanelsToPaths('Right')
                self.refresh_memory_labels()
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
                self.refresh_memory_labels()
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
        
        # Nu efectua pe Treepaneluri!
        if prefix not in ["Left", "Right"]:
            return

        history_back = getattr(self, f'PathHistoryBack{prefix}')
        history_next = getattr(self, f'PathHistoryNext{prefix}')
        
        self.style_active_panel(active_tree)

        if history_back:
            history_next.append(getattr(self, current_path_attr))
            new_path = history_back.pop()

            setattr(self, current_path_attr, new_path)
            self.setupTree(active_tree, new_path)
            self.LeftPathLine.setText(str(new_path))
            self.syncSidePanelsToPaths(prefix)
            print(f"Inapoi la: {new_path}")
        else:
            print("Nu exista istoric anterior.")
        self.refresh_memory_labels()

    def GoNext(self):
        active_tree, prefix = self.getActivePanel()
        current_path_attr = 'currentPath' + prefix
                
        # Nu efectua pe Treepaneluri!
        if prefix not in ["Left", "Right"]:
            return
        
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
        self.refresh_memory_labels()

    def DelFile(self):
        active_tree, prefix = self.getActivePanel()
        selected_items = active_tree.selectedItems()
        current_path = getattr(self, f'currentPath{prefix}')

        if not selected_items:
            QMessageBox.warning(self, "Atentie", "Selectati elementele pentru stergere.")
            return

        # Filtrăm elementele valide (fără "..")
        valid_items = [item for item in selected_items if item.text(0) != ".."]
        # Distingam plural sau singular
        elemente = "element" if len(valid_items)==1 else "elemente"
    
        reply = QMessageBox.question(self, 'Confirmare Stergere',
                                     f"Sunteti sigur ca doriti sa stergeti {len(valid_items)} {elemente}?\n(Atentie, nu este trimis in Recycle Bin!)",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        errors = []
        if reply == QMessageBox.StandardButton.Yes:
            for item in valid_items:
                path_str = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                try:
                    if item.text(2) == "DIR":
                        shutil.rmtree(path_str)
                    else:
                        os.remove(path_str)
                except Exception as e:
                    errors.append(f"{item.text(0)}: {e}")
            deleted_count = len(valid_items)
            if deleted_count > 0 and SHOW_EXTRA_MESSAGES:
                    # Mesaj specific pentru numărul de fișiere eliminate
                    QMessageBox.information(self, "Succes", f"{deleted_count} elemente au fost sterse.")
            if errors:
                QMessageBox.warning(self, "Erori", f"Nu s-au putut șterge {len(errors)} elemente.")
            
        self.RefreshPanels()
        self.refresh_memory_labels()

    def TrashFile(self):
        active_tree, prefix = self.getActivePanel()
        selected_items = active_tree.selectedItems()

        if not selected_items:
            return

        valid_items = [item for item in selected_items if item.text(0) != ".."]
    
        # Importăm aici pentru a nu genera erori dacă librăria nu e instalată
        try:
            from send2trash import send2trash
        except ImportError:
            QMessageBox.critical(self, "Eroare", "Librăria 'send2trash' nu este instalată!\nRulează: pip install send2trash")
            return

        try:
            for item in valid_items:
                path_str = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                # Transformăm path-ul în format nativ pentru sistemul de operare
                send2trash(os.path.abspath(path_str))
        
            self.RefreshPanels()
            self.refresh_memory_labels()
        
            if SHOW_EXTRA_MESSAGES:
                QMessageBox.information(self, "Recycle Bin", f"{len(valid_items)} elemente au fost trimise la coș.")
            
        except Exception as e:
            QMessageBox.critical(self, "Eroare", f"Nu s-a putut trimite la coș: {e}")

    def SortColumns(self):
        self.LeftTree.setSortingEnabled(False)
        self.RightTree.setSortingEnabled(False)
        
        self.LeftTree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        self.RightTree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)

    def setupTree(self, tree_widget: QTreeWidget, path: Path):
        tree_widget.setSortingEnabled(False) # Dezactivăm sortarea în timp ce adăugăm
        tree_widget.clear()
        parent_path = path.parent.resolve()

        icon_provider = QFileIconProvider()

        if parent_path != path:
            item_parent = PersistentTopItem(tree_widget, ["..", "", "DIR", ""])
            item_parent.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(parent_path))
            item_parent.setIcon(0, icon_provider.icon(QFileIconProvider.IconType.Folder))

        try:
            contents = list_directory_contents(str(path))
        except Exception as e:
            print(f"Eroare: {e}")
            return

        for item in contents:
            name_str = item['name']
            # numărul pur
            size_raw = item['size'] if item['is_file'] else -1
            # string-ul cu virgule DOAR pentru afisare
            size_display = f"{size_raw:,}" if item['is_file'] else ""
        
            ext = str(item['ext']) if item['is_file'] else 'DIR'
            date_mod = str(item['modify_date'])[:16]

            # Cream item-ul cu textul formatat
            tree_item = PersistentTopItem(tree_widget, [name_str, size_display, ext, date_mod])
        
            # Salvam PATH-ul pe coloana 0
            tree_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, item['path'])     
            tree_item.setData(1, QtCore.Qt.ItemDataRole.UserRole, size_raw)

            file_info = QFileInfo(item['path'])
            tree_item.setIcon(0, icon_provider.icon(file_info))

        tree_widget.setSortingEnabled(True)
        tree_widget.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)

    def setupPanel(self):
        self.model = QFileSystemModel()
        self.model.setRootPath("") 
        self.model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden | QDir.Filter.System)

        self.LeftPanelTree.setModel(self.model)
        self.RightPanelTree.setModel(self.model)

        # Ascundem coloanele de dimensiune, tip, dată (păstrăm doar numele)
        for i in range(1, self.model.columnCount()):
            self.LeftPanelTree.setColumnHidden(i, True)
            self.RightPanelTree.setColumnHidden(i, True)

        # Configurări vizuale pentru header
        for tree in [self.LeftPanelTree, self.RightPanelTree]:
            tree.header().hide()
            tree.setAnimated(True)
            tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            tree.header().setStretchLastSection(False)

        # Sincronizăm vizual arborele cu directoarele de pornire
        self.syncSidePanelsToPaths()
        self.LeftPanelTree.clearSelection()
        self.RightPanelTree.clearSelection()
        self.LeftPanelTree.setCurrentIndex(QtCore.QModelIndex())
        self.RightPanelTree.setCurrentIndex(QtCore.QModelIndex())
        self.LeftPanelTree.clicked.connect(self.LeftPanelClick)
        self.RightPanelTree.clicked.connect(self.RightPanelClick)

    def LeftPanelClick(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            active_tree = self.LeftTree
            prefix = "Left"
            setattr(self, f'currentPath{prefix}', Path(path))
            self.setupTree(active_tree, Path(path))
            self.LeftPathLine.setText(path)
            self.update_disk_info(path, self.LeftLabel)

    def RightPanelClick(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            active_tree = self.RightTree
            prefix = "Right"
            setattr(self, f'currentPath{prefix}', Path(path))
            self.setupTree(active_tree, Path(path))
            self.RightPathLine.setText(path)
            self.update_disk_info(path, self.RightLabel)

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
        path_line_edit = getattr(self, f'{prefix}PathLine') 
        path_line_edit.setText(folder_path)
    
        # 3. Refresh the tree widget
        self.RefreshPanels()
        self.syncSidePanelsToPaths(prefix)
    
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

    def handle_drop(self, event, target_tree):
        sources = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if local_path: sources.append(Path(local_path))
        elif event.source() is not None:
            selected_items = event.source().selectedItems()
            sources = [Path(i.data(0, Qt.ItemDataRole.UserRole)) for i in selected_items if i.text(0) != ".."]

        if not sources: return

        # Determinăm destinația
        prefix_target = "Left" if target_tree is self.LeftTree else "Right"
        current_target_dir = getattr(self, f'currentPath{prefix_target}')
        pos = event.position().toPoint()
        target_item = target_tree.itemAt(pos)
        drop_dir = current_target_dir
    
        if target_item:
            path_str = target_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if path_str:
                t_path = Path(path_str)
                drop_dir = t_path if t_path.is_dir() else t_path.parent

        # --- LOGICA DE FILTRARE (Cerința 2) ---
        # Nu facem nimic dacă sursa și destinația sunt identice
        valid_sources = [s for s in sources if s.parent.resolve() != drop_dir.resolve()]
        if not valid_sources:
            event.ignore()
            return 

        # Marcăm că este DRAG, nu clipboard paste (Cerința 1)
        self.is_clipboard_paste = False
        op = 'Copy' if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) else 'Cut'
        
        # Salvăm operațiunea curentă pentru mesajul de final, fără a strica self.clipboard_operation
        self.current_active_op = op 

        self.file_worker = FileOperationWorker(valid_sources, drop_dir, op)
        self.pd = QtWidgets.QProgressDialog(f"Transfer {op}...", "Anulează", 0, len(valid_sources), self)
        self.file_worker.progress.connect(lambda idx, name: self.pd.setValue(idx) or self.pd.setLabelText(f"Fișier: {name}"))
        self.file_worker.finished.connect(self.on_operation_complete)
        self.file_worker.start()
        event.acceptProposedAction()

    def handle_drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def custom_drag_enter(self, event):
        # Verificăm dacă sunt fișiere din exterior (Urls) sau obiecte interne
        if event.mimeData().hasUrls() or event.source() is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def custom_drag_move(self, event):
        if event.mimeData().hasUrls() or event.source() is not None:
            event.acceptProposedAction()

    def perform_external_drag(self, tree):
        selected_items = tree.selectedItems()
        # Preluăm căile stocate în UserRole, excluzând ".."
        paths = [item.data(0, Qt.ItemDataRole.UserRole) for item in selected_items if item.text(0) != ".."]
    
        if not paths:
            return

        # Creăm obiectul de Drag și MimeData (formatul universal de transfer)
        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
    
        # Transformăm string-urile de cale în QUrl-uri (esențial pentru Windows Explorer)
        urls = [QtCore.QUrl.fromLocalFile(p) for p in paths]
        mime_data.setUrls(urls)
    
        drag.setMimeData(mime_data)
    
        # (Opțional) Poți pune o iconiță care să urmărească mouse-ul
        if selected_items:
            drag.setPixmap(selected_items[0].icon(0).pixmap(32, 32))

        # Executăm operațiunea de Drag-and-Drop
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        self.RefreshPanels()
        self.refresh_memory_labels()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    myapp = MyApp()
    myapp.show()
    sys.exit(app.exec())
    