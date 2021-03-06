import sys
import os
import code
import keyword
import itertools
import unicodedata
from functools import reduce
from collections import defaultdict
from unittest.mock import patch

from typing import Optional, List, TYPE_CHECKING

from AnyQt.QtWidgets import (
    QPlainTextEdit, QListView, QSizePolicy, QMenu, QSplitter, QLineEdit,
    QAction, QToolButton, QFileDialog, QStyledItemDelegate,
    QStyleOptionViewItem, QPlainTextDocumentLayout, QTableWidget, QHeaderView, QPushButton, QComboBox
)
from AnyQt.QtGui import (
    QColor, QBrush, QPalette, QFont, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence,QFont
)
from AnyQt.QtCore import Qt, QRegExp, QByteArray, QItemSelectionModel, QSize, QThread, pyqtSignal, QObject

from Orange.data import Table
from Orange.base import Learner, Model
from Orange.util import interleave
from Orange.widgets import gui
from Orange.widgets.utils import itemmodels
from Orange.widgets.settings import Setting
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import OWWidget, Input, Output

from Orange.widgets.pipepline_utils import build_pipeline, run_pipeline

from Orange.widgets.tods_base_widget import PrimitiveInfo

from PyQt5.QtWidgets import *

from Orange.widgets.utils.itemmodels import DomainModel
from orangewidget.utils.combobox import ComboBoxSearch
from AnyQt.QtCore import Qt, QRegExp, QByteArray, QItemSelectionModel, QSize, QPersistentModelIndex


from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from time import sleep
import numpy as np

from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QDir, Qt, QUrl, QSize
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
        QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget, QStatusBar)






import os
import argparse

import pandas as pd


if TYPE_CHECKING:
    from typing_extensions import TypedDict

__all__ = ["OWPipeline_console"]


def text_format(foreground=Qt.black, weight=QFont.Normal):
    fmt = QTextCharFormat()
    fmt.setForeground(QBrush(foreground))
    fmt.setFontWeight(weight)
    return fmt


def read_file_content(filename, limit=None):
    try:
        with open(filename, encoding="utf-8", errors='strict') as f:
            text = f.read(limit)
            return text
    except (OSError, UnicodeDecodeError):
        return None


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):

        self.keywordFormat = text_format(Qt.blue, QFont.Bold)
        self.stringFormat = text_format(Qt.darkGreen)
        self.defFormat = text_format(Qt.black, QFont.Bold)
        self.commentFormat = text_format(Qt.lightGray)
        self.decoratorFormat = text_format(Qt.darkGray)

        self.keywords = list(keyword.kwlist)

        self.rules = [(QRegExp(r"\b%s\b" % kwd), self.keywordFormat)
                      for kwd in self.keywords] + \
                     [(QRegExp(r"\bdef\s+([A-Za-z_]+[A-Za-z0-9_]+)\s*\("),
                       self.defFormat),
                      (QRegExp(r"\bclass\s+([A-Za-z_]+[A-Za-z0-9_]+)\s*\("),
                       self.defFormat),
                      (QRegExp(r"'.*'"), self.stringFormat),
                      (QRegExp(r'".*"'), self.stringFormat),
                      (QRegExp(r"#.*"), self.commentFormat),
                      (QRegExp(r"@[A-Za-z_]+[A-Za-z0-9_]+"),
                       self.decoratorFormat)]

        self.multilineStart = QRegExp(r"(''')|" + r'(""")')
        self.multilineEnd = QRegExp(r"(''')|" + r'(""")')

        super().__init__(parent)

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            exp = QRegExp(pattern)
            index = exp.indexIn(text)
            while index >= 0:
                length = exp.matchedLength()
                if exp.captureCount() > 0:
                    self.setFormat(exp.pos(1), len(str(exp.cap(1))), fmt)
                else:
                    self.setFormat(exp.pos(0), len(str(exp.cap(0))), fmt)
                index = exp.indexIn(text, index + length)

        # Multi line strings
        start = self.multilineStart
        end = self.multilineEnd

        self.setCurrentBlockState(0)
        startIndex, skip = 0, 0
        if self.previousBlockState() != 1:
            startIndex, skip = start.indexIn(text), 3
        while startIndex >= 0:
            endIndex = end.indexIn(text, startIndex + skip)
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLen = len(text) - startIndex
            else:
                commentLen = endIndex - startIndex + 3
            self.setFormat(startIndex, commentLen, self.stringFormat)
            startIndex, skip = (start.indexIn(text,
                                              startIndex + commentLen + 3),
                                3)


class PythonScriptEditor(QPlainTextEdit):
    INDENT = 4

    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def lastLine(self):
        text = str(self.toPlainText())
        pos = self.textCursor().position()
        index = text.rfind("\n", 0, pos)
        text = text[index: pos].lstrip("\n")
        return text

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            if event.modifiers() & (
                    Qt.ShiftModifier | Qt.ControlModifier | Qt.MetaModifier):
                self.widget.commit()
                return
            text = self.lastLine()
            indent = len(text) - len(text.lstrip())
            if text.strip() == "pass" or text.strip().startswith("return "):
                indent = max(0, indent - self.INDENT)
            elif text.strip().endswith(":"):
                indent += self.INDENT
            super().keyPressEvent(event)
            self.insertPlainText(" " * indent)
        elif event.key() == Qt.Key_Tab:
            self.insertPlainText(" " * self.INDENT)
        elif event.key() == Qt.Key_Backspace:
            text = self.lastLine()
            if text and not text.strip():
                cursor = self.textCursor()
                for _ in range(min(self.INDENT, len(text))):
                    cursor.deletePreviousChar()
            else:
                super().keyPressEvent(event)

        else:
            super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        """
        Reimplemented from QPlainTextEdit.insertFromMimeData.
        """
        urls = source.urls()
        if urls:
            self.pasteFile(urls[0])
        else:
            super().insertFromMimeData(source)

    def pasteFile(self, url):
        new = read_file_content(url.toLocalFile())
        if new:
            # inserting text like this allows undo
            cursor = QTextCursor(self.document())
            cursor.select(QTextCursor.Document)
            cursor.insertText(new)


class PythonConsole(QPlainTextEdit, code.InteractiveConsole):
    # `locals` is reasonably used as argument name
    # pylint: disable=redefined-builtin
    def __init__(self, locals=None, parent=None):
        QPlainTextEdit.__init__(self, parent)
        code.InteractiveConsole.__init__(self, locals)
        self.newPromptPos = 0
        self.history, self.historyInd = [""], 0
        self.loop = self.interact()
        next(self.loop)

    def setLocals(self, locals):
        self.locals = locals

    def updateLocals(self, locals):
        self.locals.update(locals)

    def interact(self, banner=None, _=None):
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        cprt = ('Type "help", "copyright", "credits" or "license" '
                'for more information.')
        if banner is None:
            self.write("Python %s on %s\n%s\n(%s)\n" %
                       (sys.version, sys.platform, cprt,
                        self.__class__.__name__))
        else:
            self.write("%s\n" % str(banner))
        more = 0
        while 1:
            try:
                if more:
                    prompt = sys.ps2
                else:
                    prompt = sys.ps1
                self.new_prompt(prompt)
                yield
                try:
                    line = self.raw_input(prompt)
                except EOFError:
                    self.write("\n")
                    break
                else:
                    more = self.push(line)
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0

    def raw_input(self, prompt=""):
        input_str = str(self.document().lastBlock().previous().text())
        return input_str[len(prompt):]

    def new_prompt(self, prompt):
        self.write(prompt)
        self.newPromptPos = self.textCursor().position()
        self.repaint()

    def write(self, data):
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
        cursor.insertText(data)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        pass

    def push(self, line):
        if self.history[0] != line:
            self.history.insert(0, line)
        self.historyInd = 0

        # prevent console errors to trigger error reporting & patch stdout, stderr
        with patch('sys.excepthook', sys.__excepthook__),\
             patch('sys.stdout', self),\
             patch('sys.stderr', self):
            return code.InteractiveConsole.push(self, line)

    def setLine(self, line):
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.End)
        cursor.setPosition(self.newPromptPos, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(line)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.write("\n")
            next(self.loop)
        elif event.key() == Qt.Key_Up:
            self.historyUp()
        elif event.key() == Qt.Key_Down:
            self.historyDown()
        elif event.key() == Qt.Key_Tab:
            self.complete()
        elif event.key() in [Qt.Key_Left, Qt.Key_Backspace]:
            if self.textCursor().position() > self.newPromptPos:
                QPlainTextEdit.keyPressEvent(self, event)
        else:
            QPlainTextEdit.keyPressEvent(self, event)

    def historyUp(self):
        self.setLine(self.history[self.historyInd])
        self.historyInd = min(self.historyInd + 1, len(self.history) - 1)

    def historyDown(self):
        self.setLine(self.history[self.historyInd])
        self.historyInd = max(self.historyInd - 1, 0)

    def complete(self):
        pass

    def _moveCursorToInputLine(self):
        """
        Move the cursor to the input line if not already there. If the cursor
        if already in the input line (at position greater or equal to
        `newPromptPos`) it is left unchanged, otherwise it is moved at the
        end.

        """
        cursor = self.textCursor()
        pos = cursor.position()
        if pos < self.newPromptPos:
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)

    def pasteCode(self, source):
        """
        Paste source code into the console.
        """
        self._moveCursorToInputLine()

        for line in interleave(source.splitlines(), itertools.repeat("\n")):
            if line != "\n":
                self.insertPlainText(line)
            else:
                self.write("\n")
                next(self.loop)

    def insertFromMimeData(self, source):
        """
        Reimplemented from QPlainTextEdit.insertFromMimeData.
        """
        if source.hasText():
            self.pasteCode(str(source.text()))
            return


class Script:
    Modified = 1
    MissingFromFilesystem = 2

    def __init__(self, name, script, flags=0, filename=None):
        self.name = name
        self.script = script
        self.flags = flags
        self.filename = filename

    def asdict(self) -> '_ScriptData':
        return dict(name=self.name, script=self.script, filename=self.filename)

    @classmethod
    def fromdict(cls, state: '_ScriptData') -> 'Script':
        return Script(state["name"], state["script"], filename=state["filename"])


class ScriptItemDelegate(QStyledItemDelegate):
    # pylint: disable=no-self-use
    def displayText(self, script, _locale):
        if script.flags & Script.Modified:
            return "*" + script.name
        else:
            return script.name

    def paint(self, painter, option, index):
        script = index.data(Qt.DisplayRole)

        if script.flags & Script.Modified:
            option = QStyleOptionViewItem(option)
            option.palette.setColor(QPalette.Text, QColor(Qt.red))
            option.palette.setColor(QPalette.Highlight, QColor(Qt.darkRed))
        super().paint(painter, option, index)

    def createEditor(self, parent, _option, _index):
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        script = index.data(Qt.DisplayRole)
        editor.setText(script.name)

    def setModelData(self, editor, model, index):
        model[index.row()].name = str(editor.text())


def select_row(view, row):
    """
    Select a `row` in an item view
    """
    selmodel = view.selectionModel()
    selmodel.select(view.model().index(row, 0),
                    QItemSelectionModel.ClearAndSelect)


if TYPE_CHECKING:
    # pylint: disable=used-before-assignment
    _ScriptData = TypedDict("_ScriptData", {
        "name": str, "script": str, "filename": Optional[str]
    })
    
    
class Worker1(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    def __init__(self, graph_widget = None):
        QThread.__init__(self)
        self.graph_widget = graph_widget
#        print("INSIDE", self.graph_widget)
#        self.stopped = event
        
    def run(self):
    
        """Long-running task."""
        for i in range(5):
            sleep(5)
#            print("HH")
            graph = pd.read_csv("tmp/graph_train.csv", index_col = None) #/Users/zaidbhat/GUI/training.csv
            c1,c2 = np.array(graph.iloc[:,0]), np.array(graph.iloc[:,1])
#            print("HERE:", c1,c2)
            self.graph_widget.plot(c1, c2)
            self.progress.emit(i + 1)
        self.finished.emit()
    

class Worker(QThread):
#    finished = pyqtSignal()
#    progress = pyqtSignal(int)
    update = pyqtSignal()
    def __init__(self, event=True, graph_widget = None):
        QThread.__init__(self)
        self.graph_widget = graph_widget
        self.stopped = event
        
    def run(self):
    
        while self.stopped:#not self.stopped.wait(0.02):
#            print("KK")
            self.update.emit()


class OWPythonScript(OWWidget):
    name = "Pipeline Console"
    description = "Console of pipeline."
    icon = "icons/PythonScript.svg"
    priority = 3150
    keywords = ["build", "run"]

    class Inputs:
        data = Input("Data", Table, replaces=["in_data"],
                     default=True, multiple=True)
        learner = Input("Learner", Learner, replaces=["in_learner"],
                        default=True, multiple=True)
        classifier = Input("Classifier", Model, replaces=["in_classifier"],
                           default=True, multiple=True)
        object = Input("Object", object, replaces=["in_object"],
                       default=False, multiple=True)

        # Pipeline structure
        pipline_in = Input("Input info", list)

    class Outputs:
        data = Output("Data", Table, replaces=["out_data"])
        learner = Output("Learner", Learner, replaces=["out_learner"])
        classifier = Output("Classifier", Model, replaces=["out_classifier"])
        object = Output("Object", object, replaces=["out_object"])

    # JJ
    @Inputs.pipline_in
    def set_pipline_in(self, pipline_in):
        if pipline_in is not None:
            # self.infoa.setText("There is input, which is the beginning of th pipeline.")
            self.pipeline_wrapping(pipline_in)
            # self.pipeline_writing()  ########## Only for test
            # self.read()  ########## Only for test
        # else:
        #     self.infoa.setText("No data on input yet, waiting to get something.")


    signal_names = ("data", "learner", "classifier", "object")

    settings_version = 2
    scriptLibrary: 'List[_ScriptData]' = Setting([{
        "name": "Hello world",
        "script": "print('Hello world')\n",
        "filename": None
    }])
    currentScriptIndex = Setting(0)
    scriptText: Optional[str] = Setting(None, schema_only=True)
    splitterState: Optional[bytes] = Setting(None)

    # Widgets in the same schema share namespace through a dictionary whose
    # key is self.signalManager. ales-erjavec expressed concern (and I fully
    # agree!) about widget being aware of the outside world. I am leaving this
    # anyway. If this causes any problems in the future, replace this with
    # shared_namespaces = {} and thus use a common namespace for all instances
    # of # PythonScript even if they are in different schemata.
    shared_namespaces = defaultdict(dict)

    class Error(OWWidget.Error):
        pass

    def __init__(self):
        super().__init__()
        self.libraryListSource = []

        for name in self.signal_names:
            setattr(self, name, {})

        self._cachedDocuments = {}

#Remove info box
#        self.infoBox = gui.vBox(self.controlArea, 'Info')
#        gui.label(
#            self.infoBox, self,
#            "<p>Execute python script.</p><p>Input variables:<ul><li> " +
#            "<li>".join(map("in_{0}, in_{0}s".format, self.signal_names)) +
#            "</ul></p><p>Output variables:<ul><li>" +
#            "<li>".join(map("out_{0}".format, self.signal_names)) +
#            "</ul></p>"
#        )

        self.libraryList = itemmodels.PyListModel(
            [], self,
            flags=Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

        self.libraryList.wrap(self.libraryListSource)
#
#        self.controlBox = gui.vBox(self.controlArea, 'Library')
#        self.controlBox.layout().setSpacing(1)

        self.libraryView = QListView(
            editTriggers=QListView.DoubleClicked |
            QListView.EditKeyPressed,
            sizePolicy=QSizePolicy(QSizePolicy.Ignored,
                                   QSizePolicy.Preferred)
        )
        self.libraryView.setItemDelegate(ScriptItemDelegate(self))
        self.libraryView.setModel(self.libraryList)

        self.libraryView.selectionModel().selectionChanged.connect(
            self.onSelectedScriptChanged
        )
        #Z: remove the library widget
#        self.controlBox.layout().addWidget(self.libraryView)

        w = itemmodels.ModelActionsWidget()

        self.addNewScriptAction = action = QAction("+", self)
        action.setToolTip("Add a new script to the library")
        action.triggered.connect(self.onAddScript)
        w.addAction(action)

        action = QAction(unicodedata.lookup("MINUS SIGN"), self)
        action.setToolTip("Remove script from library")
        action.triggered.connect(self.onRemoveScript)
        w.addAction(action)

        action = QAction("Update", self)
        action.setToolTip("Save changes in the editor to library")
        action.setShortcut(QKeySequence(QKeySequence.Save))
        action.triggered.connect(self.commitChangesToLibrary)
        w.addAction(action)

        action = QAction("More", self, toolTip="More actions")

        new_from_file = QAction("Import Script from File", self)
        save_to_file = QAction("Save Selected Script to File", self)
        restore_saved = QAction("Undo Changes to Selected Script", self)
        save_to_file.setShortcut(QKeySequence(QKeySequence.SaveAs))

        new_from_file.triggered.connect(self.onAddScriptFromFile)
        save_to_file.triggered.connect(self.saveScript)
        restore_saved.triggered.connect(self.restoreSaved)

        menu = QMenu(w)
        menu.addAction(new_from_file)
        menu.addAction(save_to_file)
        menu.addAction(restore_saved)
        action.setMenu(menu)
        button = w.addAction(action)
        button.setPopupMode(QToolButton.InstantPopup)

        w.layout().setSpacing(1)
        #Z: Remove Library widget
#        self.controlBox.layout().addWidget(w)

        self.execute_button = gui.button(self.controlArea, self, 'Run Script', callback=self.commit)

#        self.build_pipeline_button = gui.button(self.controlArea, self, 'Recognise', callback=self.recognise)
        self.build_pipeline_button = gui.button(self.controlArea, self, 'Build Pipeline', callback=self.build_pipeline)
        self.run_pipeline_button = gui.button(self.controlArea, self, 'Fit', callback=self.fit)
        
        self.produce_button = gui.button(self.controlArea, self, 'Produce', callback=self.produce)
        self.search_button = gui.button(self.controlArea, self, 'Search', callback=self.search)
        
        
        #To take search space
        
        
#        self.box_1 = gui.vBox(self, 'SS') #stretch  = 100
#        self.cond_list1 = QTableWidget(
#            self, showGrid=True, selectionMode=QTableWidget.NoSelection)
#        self.splitCanvas.addWidget(self.box_1)
#        self.box_1.layout().addWidget(self.cond_list1)
#
#        self.box_1.setAlignment(Qt.AlignTop)
#        self.textBox1 = gui.vBox(self, 'SS')
#        self.controlArea.addWidget(self.textBox1)
#        self.text1 = PythonScriptEditor(self)
#        self.textBox1.layout().addWidget(self.text1)

#        self.textBox1.setAlignment(Qt.AlignTop)
#        self.text.setTabStopWidth(4)

#        self.text1.modificationChanged[bool].connect(self.onModificationChanged)

        

        run = QAction("Run script", self, triggered=self.commit,
                      shortcut=QKeySequence(Qt.ControlModifier | Qt.Key_R))
        self.addAction(run)

        self.splitCanvas = QSplitter(Qt.Vertical, self.mainArea)
        self.mainArea.layout().addWidget(self.splitCanvas)

        self.defaultFont = defaultFont = \
            "Monaco" if sys.platform == "darwin" else "Courier"

        self.textBox = gui.vBox(self, 'Python Script')
        self.splitCanvas.addWidget(self.textBox)
        self.text = PythonScriptEditor(self)
        self.textBox.layout().addWidget(self.text)

        self.textBox.setAlignment(Qt.AlignTop)
        self.text.setTabStopWidth(4)

        self.text.modificationChanged[bool].connect(self.onModificationChanged)

        self.saveAction = action = QAction("&Save", self.text)
        action.setToolTip("Save script to file")
        action.setShortcut(QKeySequence(QKeySequence.Save))
        action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        action.triggered.connect(self.saveScript)
        
#        #To display the outpuit predictions table
#        self.box_1 = gui.vBox(self, 'SS') #stretch  = 100
#        self.cond_list1 = QTableWidget(
#            self, showGrid=True, selectionMode=QTableWidget.NoSelection)
#        self.splitCanvas.addWidget(self.box_1)
#        self.box_1.layout().addWidget(self.cond_list1)
#
#        self.box_1.setAlignment(Qt.AlignTop)
        
        
        #To display the outpuit predictions table
        self.box_ = gui.vBox(self, 'Output') #stretch  = 100
        self.cond_list = QTableWidget(
            self, showGrid=True, selectionMode=QTableWidget.NoSelection)
        self.splitCanvas.addWidget(self.box_)
        self.box_.layout().addWidget(self.cond_list)
        
        self.box_.setAlignment(Qt.AlignVCenter)
        
        
        
        
        self.consoleBox = gui.vBox(self, 'Console')
        self.splitCanvas.addWidget(self.consoleBox)
        self.console = PythonConsole({}, self)
        self.consoleBox.layout().addWidget(self.console)
        self.console.document().setDefaultFont(QFont(defaultFont))
        self.consoleBox.setAlignment(Qt.AlignBottom)
        self.console.setTabStopWidth(4)
        self.splitCanvas.setSizes([2, 1])
        self.setAcceptDrops(True)
        self.controlArea.layout().addStretch(10)

        self._restoreState()
        self.settingsAboutToBePacked.connect(self._saveState)


        # pipeline infomation
        self.hyperparameter = {}
        self.python_path = "ENDING"
        self.primitive_info = PrimitiveInfo(python_path=self.python_path,
                                            id=-1,
                                            hyperparameter=self.hyperparameter,
                                            ancestors={}
                                            )
    def display(self, video_path = None):
        
        #The name of the button that is clicked on
        rbt = self.sender()
        video_path = self.media_dir + '/' + str(rbt.text())
        v = VideoPlayer2(video_path)
        v.show()
        
    def search_space(self):
        r,c = 5,2
        self.cond_list1.setColumnCount(c)
        self.cond_list1.setRowCount(r)
        self.cond_list1.verticalHeader()#.hide()
        self.cond_list1.horizontalHeader()#.hide()
        ss = ["algorithm", "learning_rate", "momentum","weight_decay", "num_segments"]
#        search_space = {
#        "algorithm": tune.choice(["tsn"]),
#        "learning_rate": tune.uniform(0.0001, 0.001),
#        "momentum": tune.uniform(0.9,0.99),
#        "weight_decay": tune.uniform(5e-4,1e-3),
#        "num_segments": tune.choice([8,16,32]),
#    }
        for i in range(r):
            self.cond_list1.setItem(i,0, QTableWidgetItem(ss[i]))
                
        
    def add_row(self, df=None):
        '''
        Add rows to the Table Widget
        '''
        r,c = df.shape
        
        self.cond_list.setColumnCount(c)
        self.cond_list.setRowCount(r)
        self.cond_list.verticalHeader()#.hide()
        self.cond_list.horizontalHeader()#.hide()
        self.cond_list.setHorizontalHeaderLabels(list(df.columns))
        
        for i in range(r):
            for j in range(c):
                if j==1: #Making the column with video path as buttons
                    self.showBtn = gui.button(self.controlArea, self, str(df.iloc[i,j]), callback=self.display)
                    self.cond_list.setCellWidget(i,j,self.showBtn)
                else:
                    self.cond_list.setItem(i,j, QTableWidgetItem(str(df.iloc[i,j])))

    def sizeHint(self) -> QSize:
        return super().sizeHint().expandedTo(QSize(800, 600))

    def _restoreState(self):
        self.libraryListSource = [Script.fromdict(s) for s in self.scriptLibrary]
        self.libraryList.wrap(self.libraryListSource)
        select_row(self.libraryView, self.currentScriptIndex)

        if self.scriptText is not None:
            current = self.text.toPlainText()
            # do not mark scripts as modified
            if self.scriptText != current:
                self.text.document().setPlainText(self.scriptText)

        if self.splitterState is not None:
            self.splitCanvas.restoreState(QByteArray(self.splitterState))

    def _saveState(self):
        self.scriptLibrary = [s.asdict() for s in self.libraryListSource]
        self.scriptText = self.text.toPlainText()
        self.splitterState = bytes(self.splitCanvas.saveState())

    def handle_input(self, obj, sig_id, signal):
        sig_id = sig_id[0]
        dic = getattr(self, signal)
        if obj is None:
            if sig_id in dic.keys():
                del dic[sig_id]
        else:
            dic[sig_id] = obj

    @Inputs.data
    def set_data(self, data, sig_id):
        self.handle_input(data, sig_id, "data")

    @Inputs.learner
    def set_learner(self, data, sig_id):
        self.handle_input(data, sig_id, "learner")

    @Inputs.classifier
    def set_classifier(self, data, sig_id):
        self.handle_input(data, sig_id, "classifier")

    @Inputs.object
    def set_object(self, data, sig_id):
        self.handle_input(data, sig_id, "object")

    def handleNewSignals(self):
        self.commit()

    def selectedScriptIndex(self):
        rows = self.libraryView.selectionModel().selectedRows()
        if rows:
            return [i.row() for i in rows][0]
        else:
            return None

    def setSelectedScript(self, index):
        select_row(self.libraryView, index)

    def onAddScript(self, *_):
        self.libraryList.append(Script("New script", self.text.toPlainText(), 0))
        self.setSelectedScript(len(self.libraryList) - 1)

    def onAddScriptFromFile(self, *_):
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Open Python Script',
            os.path.expanduser("~/"),
            'Python files (*.py)\nAll files(*.*)'
        )
        if filename:
            name = os.path.basename(filename)
            # TODO: use `tokenize.detect_encoding`
            with open(filename, encoding="utf-8") as f:
                contents = f.read()
            self.libraryList.append(Script(name, contents, 0, filename))
            self.setSelectedScript(len(self.libraryList) - 1)

    def onRemoveScript(self, *_):
        index = self.selectedScriptIndex()
        if index is not None:
            del self.libraryList[index]
            select_row(self.libraryView, max(index - 1, 0))

    def onSaveScriptToFile(self, *_):
        index = self.selectedScriptIndex()
        if index is not None:
            self.saveScript()

    def onSelectedScriptChanged(self, selected, _deselected):
        index = [i.row() for i in selected.indexes()]
        if index:
            current = index[0]
            if current >= len(self.libraryList):
                self.addNewScriptAction.trigger()
                return

            self.text.setDocument(self.documentForScript(current))
            self.currentScriptIndex = current

    def documentForScript(self, script=0):
        if not isinstance(script, Script):
            script = self.libraryList[script]
        if script not in self._cachedDocuments:
            doc = QTextDocument(self)
            doc.setDocumentLayout(QPlainTextDocumentLayout(doc))
            doc.setPlainText(script.script)
            doc.setDefaultFont(QFont(self.defaultFont))
            doc.highlighter = PythonSyntaxHighlighter(doc)
            doc.modificationChanged[bool].connect(self.onModificationChanged)
            doc.setModified(False)
            self._cachedDocuments[script] = doc
        return self._cachedDocuments[script]

    def commitChangesToLibrary(self, *_):
        index = self.selectedScriptIndex()
        if index is not None:
            self.libraryList[index].script = self.text.toPlainText()
            self.text.document().setModified(False)
            self.libraryList.emitDataChanged(index)

    def onModificationChanged(self, modified):
        index = self.selectedScriptIndex()
        if index is not None:
            self.libraryList[index].flags = Script.Modified if modified else 0
            self.libraryList.emitDataChanged(index)

    def restoreSaved(self):
        index = self.selectedScriptIndex()
        if index is not None:
            self.text.document().setPlainText(self.libraryList[index].script)
            self.text.document().setModified(False)

    def saveScript(self):
        index = self.selectedScriptIndex()
        if index is not None:
            script = self.libraryList[index]
            filename = script.filename
        else:
            filename = os.path.expanduser("~/")

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Save Python Script',
            filename,
            'Python files (*.py)\nAll files(*.*)'
        )

        if filename:
            fn = ""
            head, tail = os.path.splitext(filename)
            if not tail:
                fn = head + ".py"
            else:
                fn = filename

            f = open(fn, 'w')
            f.write(self.text.toPlainText())
            f.close()

    def initial_locals_state(self):
        d = self.shared_namespaces[self.signalManager].copy()
        for name in self.signal_names:
            value = getattr(self, name)
            all_values = list(value.values())
            one_value = all_values[0] if len(all_values) == 1 else None
            d["in_" + name + "s"] = all_values
            d["in_" + name] = one_value
        return d

    def update_namespace(self, namespace):
        not_saved = reduce(set.union,
                           ({f"in_{name}s", f"in_{name}", f"out_{name}"}
                            for name in self.signal_names))
        self.shared_namespaces[self.signalManager].update(
            {name: value for name, value in namespace.items()
             if name not in not_saved})

    def commit(self):
        self.Error.clear()
        lcls = self.initial_locals_state()
        lcls["_script"] = str(self.text.toPlainText())
        self.console.updateLocals(lcls)
        self.console.write("\nRunning script:\n")
        self.console.push("exec(_script)")
        self.console.new_prompt(sys.ps1)
        self.update_namespace(self.console.locals)
        for signal in self.signal_names:
            out_var = self.console.locals.get("out_" + signal)
            signal_type = getattr(self.Outputs, signal).type
            if not isinstance(out_var, signal_type) and out_var is not None:
                self.Error.add_message(signal,
                                       "'{}' has to be an instance of '{}'.".
                                       format(signal, signal_type.__name__))
                getattr(self.Error, signal)()
                out_var = None
            getattr(self.Outputs, signal).send(out_var)



    def dragEnterEvent(self, event):  # pylint: disable=no-self-use
        urls = event.mimeData().urls()
        if urls:
            # try reading the file as text
            c = read_file_content(urls[0].toLocalFile(), limit=1000)
            if c is not None:
                event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle file drops"""
        urls = event.mimeData().urls()
        if urls:
            self.text.pasteFile(urls[0])

    @classmethod
    def migrate_settings(cls, settings, version):
        if version is not None and version < 2:
            scripts = settings.pop("libraryListSource")  # type: List[Script]
            library = [dict(name=s.name, script=s.script, filename=s.filename)
                       for s in scripts]  # type: List[_ScriptData]
            settings["scriptLibrary"] = library
            
            

#    def run_pipeline(self):
#
#        print('run_pipeline')
#        run_pipeline(self.output_list_ending, stdout=self.console)
#        self.console.new_prompt(sys.ps1) # flush the console
#        pass
    
    def build_pipeline(self):
        '''
        Build pipeline description
        '''
        print('build_pipeline')
        self.pipeline_desc  = build_pipeline(self.output_list_ending, self.primitive_mapping, stdout=self.console)
#        print(self.pipeline_desc)
        import sys
        sys.stdout = self.console
        sys.stdout.flush()
#        self.console.flush()
        self.console.new_prompt(sys.ps1) # flush the console
        pass
        

    def fit(self):
        from autovideo.utils import set_log_path, logger
        set_log_path('log.txt')
        #Get dataset directory
        data_dir = self.output_list_ending[0].hyperparameter['dataset_folder']
        train_table_path = os.path.join(data_dir, 'train.csv')
        train_media_dir = os.path.join(data_dir, 'media')
        target_index = 2

        from autovideo import fit, build_pipeline, compute_accuracy_with_preds
        # Read the CSV file
        train_dataset = pd.read_csv(train_table_path)
        pipeline = self.pipeline_desc
        
        #Methods tried for graphs
        #Method 2: Works only static not dynamic
#        stop_flag = Event()
#        self.timer_thread = Worker()
#        self.timer_thread.update.connect(self.update_graph)
#        self.timer_thread.start()
        
#       #Method 3: Only static does not work dynamic
#        self.thread = QThread()
#        print("GW", self.graph_widget)
#        self.worker = Worker1(self.graph_widget)
#        self.worker.moveToThread(self.thread)
#        # Step 5: Connect signals and slots
#        self.thread.started.connect(self.worker.run)
#        self.worker.finished.connect(self.thread.quit)
#        self.thread.start()

        _, fitted_pipeline = fit(train_dataset=train_dataset,
                                 train_media_dir=train_media_dir,
                                 target_index=target_index,
                                 pipeline=pipeline)

        # Save the fitted pipeline
        #change using self.output_list_ending[0].hyperparameter['dataset_folder']
        tmp_dir = os.path.join("tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.save_path = os.path.join(tmp_dir, "fitted_pipeline")
#        print(self.save_path)
        import torch
        torch.save(fitted_pipeline, self.save_path)
        
        #Method 1: Works somewhat but error that Qwidget cannot be put on thread)
        self.worker = GraphPlayer("tmp/graph_train.csv")#/Users/zaidbhat/GUI/training.csv")
        self.worker.show()
        
        #Does not work when putting on thread
#        self.thread = QThread()
#         # Step 4: Move worker to the thread
#        self.worker.moveToThread(self.thread)
#        # Step 5: Connect signals and slots
#        self.thread.started.connect(self.worker.callback1)
#        self.worker.finished.connect(self.thread.quit)
#        self.worker.finished.connect(self.worker.deleteLater)
#        self.thread.finished.connect(self.thread.deleteLater)
##        self.worker.progress.connect(self.reportProgress)
#        # Step 6: Start the thread
#        self.thread.start()
#        self.worker.show()
        
        


#
#    def update_graph(self):
##        print("GRAPH")
#        graph = pd.read_csv("/Users/zaidbhat/GUI/training.csv", index_col = None)
#        c1,c2 = np.array(graph.iloc[:,0]), np.array(graph.iloc[:,1])
##            print("HERE:", c1,c2)
#        self.graph_widget.plot(c1, c2)

    def search(self):
        import ray
        from ray import tune
        from hyperopt import hp
        from autovideo.searcher import RaySearcher
        data_dir = self.output_list_ending[0].hyperparameter['dataset_folder']
#        print("SEARCH", data_dir)
        train_table_path = os.path.join(data_dir, 'train.csv')
        valid_table_path = os.path.join(data_dir, 'test.csv')
        train_media_dir = os.path.join(data_dir, 'media')
        valid_media_dir = train_media_dir

        train_dataset = pd.read_csv(train_table_path)
        valid_dataset = pd.read_csv(valid_table_path)

        searcher = RaySearcher(
            train_dataset=train_dataset,
            train_media_dir=train_media_dir,
            valid_dataset=valid_dataset,
            valid_media_dir=valid_media_dir
        )

        #Search Space
        search_space = {
            "algorithm": tune.choice(["tsn"]),
            "learning_rate": tune.uniform(0.0001, 0.001),
            "momentum": tune.uniform(0.9,0.99),
            "weight_decay": tune.uniform(5e-4,1e-3),
            "num_segments": tune.choice([3]),
        }
        alg = 'hyperopt'
        num_samples = 1
        # Tuning
        config = {
            "searching_algorithm": alg,
            "num_samples": num_samples,
        }

        best_config = searcher.search(
            search_space=search_space,
            config=config
        )

        print("Best config: ", best_config)
        print("Search complete")
        import sys
        sys.stdout = self.console
        sys.stdout.flush()
        self.console.new_prompt(sys.ps1) # flush the console

    def produce(self):
        '''
        Make predictions on test set
        '''
        from autovideo.utils import set_log_path, logger
        set_log_path('log.txt')
        data_dir = self.output_list_ending[0].hyperparameter['dataset_folder']
        test_table_path = os.path.join(data_dir, 'test.csv')
        test_media_dir = os.path.join(data_dir, 'media')
        self.media_dir = test_media_dir
        target_index = 2

        from autovideo import produce, compute_accuracy_with_preds
        # Read the CSV file
        test_dataset_ = pd.read_csv(test_table_path)
        test_dataset = test_dataset_.drop(['label'], axis=1)
        test_labels = test_dataset_['label']
        self.tmp_dir = os.path.join("tmp")
        load_path = os.path.join(self.tmp_dir, "fitted_pipeline")
#        print(load_path,"LOAD")
        # Load fitted pipeline
        import torch
#        if torch.cuda.is_available():
#            fitted_pipeline = torch.load(load_path, map_location="cuda:0")
#        else:
#            fitted_pipeline = torch.load(load_path, map_location="cpu")
        fitted_pipeline = torch.load(load_path)

        # Produce
        predictions = produce(test_dataset=test_dataset,
                              test_media_dir=test_media_dir,
                              target_index=target_index,
                              fitted_pipeline=fitted_pipeline)

        # Get accuracy
        map_label = {0:'brush_hair', 1:'cartwheel', 2: 'catch', 3:'chew', 4:'clap',5:'climb'}
        test_dataset_['predictions'] = predictions['label']
        for i in range(len(test_dataset_['predictions'])):
            test_dataset_['predictions'][i] = map_label[test_dataset_['predictions'][i]]
#        print(predictions, test_dataset_)
        #self.add_row(test_dataset_, test_media_dir )
        test_acc = compute_accuracy_with_preds(predictions['label'], test_labels)
        self.add_row(test_dataset_)
        self.console.new_prompt(sys.ps1)
        #logger.info('Testing accuracy {:5.4f}'.format(test_acc))
        
    def pipeline_wrapping(self, pipline_in):
        self.output_list = pipline_in[0]
        self.ancestors_path = pipline_in[1]
        self.primitive_info.ancestors['inputs'] = self.ancestors_path
        
        #Z: adding pipeline console widget as the last widget in the pipeline using self.primitive_info
        #Z: pipline_in contains the pipeline without the last ending console
        self.output_list_ending = self.output_list + [self.primitive_info]

        self.primitive_mapping = {}
        for i in range(0, len(self.output_list_ending)):
            
            self.primitive_mapping[self.output_list_ending[i].id] = i
        print(self.primitive_mapping)
        

class VideoPlayer2(OWWidget):
    name = "Video Player"
    description = "Console1 "
    icon = "icons/PythonScript.svg"
    priority = 31512
    keywords = ["build2", "run2"]

    def __init__(self, video_path = None):
        super().__init__()
        
        self.splitCanvas = QSplitter(self.mainArea)
        self.mainArea.layout().addWidget(self.splitCanvas)
#        self.box = gui.vBox(self, 'Output') #stretch  = 100
#        self.splitCanvas.addWidget(self.box)
        self.video = QVideoWidget(self.mainArea)
#        self.video.setFullScreen(True)
        self.video.resize(480, 360)
        self.video.move(0, 0)
        self.player = QMediaPlayer(self.mainArea)
        self.player.setVideoOutput(self.video)

        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        self.execute_button = gui.button(self.controlArea, self, 'Play Video', callback=self.callback1)
#        self.execute_button1 = gui.button(self.controlArea, self, 'Play Video', callback=self.callback1)

    def callback1(self):
        self.player.setPosition(0) # to start at the beginning of the video every time
        self.player.play()


class GraphPlayer(OWWidget):
    name = "Graph Player"
    description = "Console1 "
    icon = "icons/PythonScript.svg"
    priority = 31513
    keywords = ["build2", "run2"]

    def __init__(self, graph_path = None):
        super().__init__()
        self.splitCanvas = QSplitter( self.mainArea)
        self.mainArea.layout().addWidget(self.splitCanvas)
#        self.box = gui.vBox(self, 'Output') #stretch  = 100

        self.graph_path = graph_path
        graph = pd.read_csv(graph_path, index_col = None)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.pen = pg.mkPen(color=(173, 216, 230), width=4.5)
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setLabel('left', text = "Accuracy")
        self.graphWidget.setLabel('bottom', text = "Epochs")
        self.graphWidget.setYRange(0,100)
        self.graphWidget.setTitle("Accuracy vs Epochs")
        
        font=QFont()
        font.setPixelSize(200)
        self.graphWidget.getAxis("bottom").tickFont = font
        
        self.splitCanvas.addWidget(self.graphWidget)
        
        self.execute_button = gui.button(self.mainArea, self, 'Plot Graph', callback=self.callback1)


    def callback1(self):
#        print("YAHAN", self.graph_path)
        graph = pd.read_csv(self.graph_path, index_col = None)
        c1,c2 = np.array(graph.iloc[:,0]), np.array(graph.iloc[:,1])
        self.graphWidget.plot(c1, c2, pen = self.pen)




if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWPythonScript).run()
