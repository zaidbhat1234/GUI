from functools import reduce
from types import SimpleNamespace

from AnyQt.QtCore import Qt
from AnyQt.QtWidgets import QGridLayout
from AnyQt.QtWidgets import QFormLayout
from AnyQt.QtGui import QIntValidator

import Orange.data
from Orange.util import Reprable
from Orange.statistics import distribution
from Orange.preprocess import Continuize
from Orange.preprocess.transformation import Identity, Indicator, Normalizer
from Orange.data.table import Table
from Orange.widgets import gui, widget
from Orange.widgets.settings import Setting
from Orange.widgets.utils.sql import check_sql_input
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.utils.state_summary import format_summary_details
from Orange.widgets.widget import Input, Output
from Orange.widgets.tods_base_widget import SingleInputWidget

#from tods.detection_algorithm.PyodCOF import *
from autovideo.recognition.tsn_primitive import *
class OWTSN(SingleInputWidget):
    name = "Temporal Segment Networks (TSN)"
#    id1 = "tsn"
    description = ("Action Recognoition with TSN model")
    icon = "icons/TSN.svg"
    category = "Detection Algorithm"
    keywords = []

    want_main_area = False
    buttons_area_orientatio = Qt.Vertical
    resizing_enabled = False


    # set default hyperparameters here
    autosend = Setting(True)

    contamination = Setting(0.1)
    use_columns_buf = Setting(())
    use_columns = ()
    exclude_columns_buf = Setting(())
    exclude_columns = ()
    #modality = Setting('new')
    use_semantic_types = Setting(False)
    add_index_columns = Setting(False)
    error_on_no_input = Setting(True)



    num_workers = Setting(1)
    batch_size = Setting(64)
    num_epochs = Setting(5)
    modality = Setting('RGB')
    load_pretrained = Setting('False')


    BoundedInt = Setting(10)
    BoundedFloat = Setting(10.0)
    primitive = TSNPrimitive



    


    def _use_columns_callback(self):
        #self.use_columns = eval(''.join(self.use_columns_buf))
        # print(self.use_columns)
        self.settings_changed()

    def _exclude_columns_callback(self):
        self.exclude_columns = eval(''.join(self.exclude_columns_buf))
        # print(self.exclude_columns)
        self.settings_changed()

    def _init_ui(self):
        # implement your user interface here (for setting hyperparameters)
        gui.separator(self.controlArea)
        box = gui.widgetBox(self.controlArea, "Hyperparameter")
        gui.separator(self.controlArea)

        

        gui.doubleSpin(
            box, self,
            "num_workers",
            minv=1,
            maxv=10,
            step=1,
            label="The number of subprocesses to use for data loading. 0 means that the data will be loaded in the main process",
        )

        gui.lineEdit(box, self, "batch_size", label='The batch size of training',
                     validator=None, callback=None)

        gui.lineEdit(box, self, "num_epochs", label='Number of epoch for training',
                     validator=None, callback=None)

        gui.comboBox(box, self, "modality", sendSelectedValue=True, label='Modality.', items=['RGB', 'RGBDiff', 'Flow'], )
        gui.comboBox(box, self, "load_pretrained", sendSelectedValue=True, label='Load Pretrained.', items=['True', 'False'], )


        # Only for test
        gui.button(box, self, "Print Hyperparameters", callback=self._print_hyperparameter)

        self.data = None
        self.info.set_input_summary(self.info.NoInput)
        self.info.set_output_summary(self.info.NoOutput)

    def _print_hyperparameter(self):
        print(self.num_workers, type(self.num_workers))
        print(self.batch_size, type(self.batch_size))
        print(self.num_epochs, type(self.num_epochs))
        print(self.load_pretrained, type(self.load_pretrained))
        print(self.modality, type(self.modality))


        #self.commit()

    

    

    

if __name__ == "__main__":
    WidgetPreview(OWTSN).run(Orange.data.Table("iris"))
