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
from Orange.widgets.tods_base_widget import TODS_BaseWidget, PrimitiveInfo
#from autovideo.recognition.c3d_primitive import *
class OWC3D(TODS_BaseWidget):
    name = "C3D"
    description = ("Action Recognoition with C3D model")
    icon = "icons/C3D.svg"
    category = "Detection Algorithm"
    keywords = []


    
    class Inputs:
        pipline_in1 = Input("Inputs", list)
        pipline_in2 = Input("Outputs", list)

    class Outputs:
        pipline_out = Output("Output results", list)
    want_main_area = False
    buttons_area_orientatio = Qt.Vertical
    resizing_enabled = False


#    # set default hyperparameters here
    test_treatment = Setting(0)
    autosend = Setting(True)

    num_workers = Setting(0)
    batch_size = Setting(1)
    epochs = Setting(5)
    num_segments = Setting(16)
    modality = Setting('RGB')
    load_pretrained = Setting(False)


    def __init__(self):
        super().__init__()
        TODS_BaseWidget.count += 1
        self.primitive_list.append("primitive"+str(len(self.primitive_list)+1))
        print(self.primitive_list)
        self._init_ui()

        self.pipline_in1_flag, self.pipline_in2_flag = False, False
        
        # Info will be passed
        self.hyperparameter = { 'modality':self.modality, 'load_pretrained':self.load_pretrained, 'batch_size': self.batch_size,'epochs':self.epochs, 'num_segments': self.num_segments, 'num_workers': self.num_workers}
        self.python_path = 'd3m.primitives.autovideo.recognition.c3d'
        self.id = TODS_BaseWidget.count

        self.primitive_info = PrimitiveInfo(python_path = self.python_path,
                                            id = self.id,
                                            hyperparameter = self.hyperparameter,
                                            ancestors = {},
                                            )

    def _init_ui(self):
        # implement your user interface here (for setting hyperparameters)
        gui.separator(self.controlArea)
        box = gui.widgetBox(self.controlArea, "Hyperparameter")

        gui.separator(self.controlArea)
        gui.lineEdit(box, self, "num_workers", label='Number of workers',
                     validator=None, callback=self._use_columns_callback)
        gui.lineEdit(box, self, "batch_size", label='The batch size of training',
                     validator=None, callback=self._use_columns_callback)

        gui.lineEdit(box, self, "epochs", label='Number of epoch for training',
                     validator=None, callback=self._use_columns_callback)
        gui.lineEdit(box, self, "num_segments", label='Number of segments',
                     validator=None, callback=self._use_columns_callback)
        gui.comboBox(box, self, "modality", sendSelectedValue=True, label='Modality.', items=['RGB', 'RGBDiff', 'Flow'], callback=self._use_columns_callback)
        gui.comboBox(box, self, "load_pretrained", sendSelectedValue=True, label='Load Pretrained.', items=['True', 'False'], callback=self._exclude_columns_callback)


        # Only for test
        gui.button(box, self, "Print Hyperparameters", callback=self._print_hyperparameter)
        gui.auto_apply(box, self, "autosend", box=False)
    
        self.data = None
        self.info.set_input_summary(self.info.NoInput)
        self.info.set_output_summary(self.info.NoOutput)


    def _use_columns_callback(self):
        self.settings_changed()

    def _exclude_columns_callback(self):
        self.settings_changed()
    def _print_hyperparameter(self):
        print(self.num_workers, type(self.num_workers))
        print(self.num_segments, type(self.num_segments))
        print(self.batch_size, type(self.batch_size))
        print(self.epochs, type(self.epochs))
        print(self.modality, type(self.modality))
        print(self.load_pretrained, type(self.load_pretrained))
#        self.commit()

    @Inputs.pipline_in1
    def set_pipline_in1(self, pipline_in1):
        if pipline_in1 is not None:
            self.pipline_in1_flag = True
            self.in1 = pipline_in1
        
        else:
            self.pipline_in1_flag = False
        
        self.exist_both_inputs()

    @Inputs.pipline_in2
    def set_pipline_in2(self, pipline_in2):
        if pipline_in2 is not None:
            self.pipline_in2_flag = True
            self.in2 = pipline_in2

        else:
            self.pipline_in2_flag = False
        
        self.exist_both_inputs()


    def settings_changed(self):
        self.commit()

    def commit(self):
        self.hyperparameter['modality'] = self.modality
        self.hyperparameter['load_pretrained'] = self.load_pretrained
        self.hyperparameter['num_segments'] = self.num_segments
        self.hyperparameter['num_workers'] = self.num_workers
        self.hyperparameter['epochs'] = self.epochs
        self.hyperparameter['batch_size'] = self.batch_size
        self.primitive_info.hyperparameter = self.hyperparameter

        if self.Inputs.pipline_in1 is not None and self.Inputs.pipline_in2 is not None:
            self.Outputs.pipline_out.send([self.output_list + [self.primitive_info], self.id])

    def exist_both_inputs(self):
        if self.pipline_in1_flag and self.pipline_in2_flag:
            output_list_sub1 = self.in1[0]
            ancestors_path_sub1 = self.in1[1]

            output_list_sub2 = self.in2[0]
            ancestors_path_sub2 = self.in2[1]

            output_list = []
            already_in_output_list=set()

            for i in output_list_sub1:
                if i.python_path not in already_in_output_list:
                    output_list.append(i)
                    already_in_output_list.add(i.python_path)

            for i in output_list_sub2:
                if i.python_path not in already_in_output_list:
                    output_list.append(i)
                    already_in_output_list.add(i.python_path)

            self.primitive_info.ancestors['inputs'] = ancestors_path_sub1
            self.primitive_info.ancestors['outputs'] = ancestors_path_sub2

            output_list.append(self.primitive_info)
            self.output_list = output_list
            self.Outputs.pipline_out.send([output_list, self.id])

            return

        elif self.pipline_in1_flag or self.pipline_in2_flag:
            self.primitive_info.ancestors = {}
            self.Outputs.pipline_out.send(None)

        else:
            self.primitive_info.ancestors = {}
            self.Outputs.pipline_out.send(None)


if __name__ == "__main__":
    WidgetPreview(OWC3D).run(Orange.data.Table("iris"))
