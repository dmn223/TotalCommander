import sys
from PyQt6.QtWidgets import QApplication, QInputDialog, QPushButton, QWidget, QTreeWidgetItem, QTreeWidget, QDialog, QMessageBox, QMenu, QLineEdit
from PyQt6.uic import loadUi
from pathlib import Path
import os
import shutil
import datetime
from PyQt6.QtCore import Qt
import PyQt6.QtCore as QtCore
import webbrowser

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
                'size': int(stats.st_size) if entry.is_file() else 0,
                'is_file': entry.is_file(),
                'ext': entry.suffix,
                'path': str(entry),
                'modify_date': datetime.datetime.fromtimestamp(stats.st_mtime)
            })
        except Exception:
            continue
    return contents

class MyApp(QDialog):

    LeftTree: QTreeWidget
    RightTree: QTreeWidget
    AddButton: QPushButton
    BackButton: QPushButton
    NextButton: QPushButton
    DelButton: QPushButton

    lineEdit: QLineEdit
    FindPathButton: QPushButton

    PathHistoryBackLeft: list[Path]
    PathHistoryBackRight: list[Path]
    PathHistoryNextLeft: list[Path]
    PathHistoryNextRight: list[Path]

    currentPathLeft: Path
    currentPathRight: Path
    panel_activated: str
    clipboard: Path

    def __init__(self):
        super().__init__()
        loadUi('Display.ui', self)

        self.PathHistoryBackLeft = []
        self.PathHistoryBackRight = []
        self.PathHistoryNextLeft = []
        self.PathHistoryNextRight = []

        self.currentPathLeft = Path("C:/")
        self.currentPathRight = Path("D:/") if Path("D:/").exists() else Path("C:/")
        
        self.panel_activated = 'Left' 
        self.ConfigWidgets()

        self.clipboard_path: Path | None = None
        self.clipboard_operation: str = '' # 'Copy' sau 'Cut'

    def ConfigWidgets(self): 

        self.LeftTree.installEventFilter(self)
        self.RightTree.installEventFilter(self)
        self.lineEdit.installEventFilter(self)

        self.LeftTree.viewport().installEventFilter(self)
        self.RightTree.viewport().installEventFilter(self)

        self.SortColumns()

        self.LeftTree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.RightTree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        
        self.LeftTree.customContextMenuRequested.connect(self.showContextMenu)
        self.RightTree.customContextMenuRequested.connect(self.showContextMenu)

        self.LeftTree.itemDoubleClicked.connect(self.OpenItem)
        self.RightTree.itemDoubleClicked.connect(self.OpenItem)

        self.LeftTree.setHeaderLabels(["Name", "Size", "Ext", "DateMod"])
        self.RightTree.setHeaderLabels(["Name", "Size", "Ext", "DateMod"])

        self.setupTree(self.LeftTree, self.currentPathLeft)
        self.setupTree(self.RightTree, self.currentPathRight)

        self.AddButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.BackButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.NextButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.DelButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.AddButton.clicked.connect(self.AddFile)
        self.BackButton.clicked.connect(self.GoBack)
        self.NextButton.clicked.connect(self.GoNext)
        self.DelButton.clicked.connect(self.DelFile)

        self.style_active_panel(self.LeftTree)

        self.lineEdit.returnPressed.connect(self.NavigateToPath)
        self.FindPathButton.clicked.connect(self.NavigateToPath)
        
        self.lineEdit.setText(str(self.currentPathLeft))

        self.setupSizeTree()
    def eventFilter(self, source, event):
        # Detectare focus (codul tau existent)
        if event.type() == QtCore.QEvent.Type.FocusIn:  
            if source == self.LeftTree:
                self.panel_activated = 'Left'
                self.style_active_panel(self.LeftTree)
            elif source == self.RightTree:
                self.panel_activated = 'Right'
                self.style_active_panel(self.RightTree)

        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if source in [self.LeftTree, self.LeftTree.viewport(), self.RightTree, self.RightTree.viewport()]:
            
                if source in [self.LeftTree, self.LeftTree.viewport()]:
                    self.panel_activated = 'Left'
                    self.style_active_panel(self.LeftTree)
                else:
                    self.panel_activated = 'Right'
                    self.style_active_panel(self.RightTree)

                if event.button() == Qt.MouseButton.XButton1:
                    self.GoBack()
                    return True 
                elif event.button() == Qt.MouseButton.XButton2:
                    self.GoNext()
                    return True

        return super().eventFilter(source, event)
    def style_active_panel(self, active_tree: QTreeWidget):
        inactive_tree = self.RightTree if active_tree == self.LeftTree else self.LeftTree
        
        active_style = "QTreeWidget {border: 2px solid #0078D7;}"
        inactive_style = "QTreeWidget {border: 1px solid gray;}"

        active_tree.setStyleSheet(active_style)
        inactive_tree.setStyleSheet(inactive_style)
    def getActivePanel(self):
        prefix = self.panel_activated
        active_tree = self.LeftTree if prefix == 'Left' else self.RightTree
        return active_tree, prefix
    def showContextMenu(self, position):
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
        
        menu.exec(active_tree.mapToGlobal(position))
    def NavigateToPath(self):
        address = self.lineEdit.text()
        if not address:
            QMessageBox.warning(self, "Atentie", "Va rugam introduceti o cale sau o adresa.")
            return

        active_tree, prefix = self.getActivePanel()
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
                self.lineEdit.setText(str(target_path))
                
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
            
            # Copiaza calea in clipboard-ul de sistem (optional, pentru compatibilitate)
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
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.XButton1:
            self.GoBack()
        elif event.button() == Qt.MouseButton.XButton2:
            self.GoNext()
        else:
            super().mousePressEvent(event)
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
                    self.lineEdit.setText(str(selected_path))
                else:
                    self.PathHistoryBackRight.append(self.currentPathRight)
                    self.PathHistoryNextRight = []
                    self.currentPathRight = selected_path
                    self.setupTree(self.RightTree, selected_path)
                    self.panel_activated = 'Right'
                    self.lineEdit.setText(str(selected_path))
                
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
            self.lineEdit.setText(str(new_path))
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
            self.lineEdit.setText(str(new_path))
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
    def setupSizeTree(self):
        print("setup sizes...")  
    def SortColumns(self):
        self.LeftTree.setSortingEnabled(True)
        self.RightTree.setSortingEnabled(True)
        
        self.LeftTree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        self.RightTree.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)       
    def setupTree(self, tree_widget: QTreeWidget, path: Path):
        tree_widget.clear()
        parent_path = path.parent.resolve()

        if parent_path != path:
            item_parent = QTreeWidgetItem(tree_widget, ["..", "", "DIR", ""])
            item_parent.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(parent_path))

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
if __name__ == '__main__':
    app = QApplication(sys.argv)
    myapp = MyApp()
    myapp.show()
    sys.exit(app.exec())