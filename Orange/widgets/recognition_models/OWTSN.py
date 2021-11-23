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
#from tods.detection_algorithm.PyodCOF import *
from autovideo.recognition.tsn_primitive import *
class OWTSN(TODS_BaseWidget):
    name = "Temporal Segment Networks (TSN)"
#    id1 = "tsn"
    description = ("Action Recognoition with TSN model")
    icon = "icons/TSN.svg"
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


#Having these causes it to not run on my machine, check the default values in UROVIDEO  TSN file only those work
#    num_workers = Setting(0)
#    batch_size = Setting(1)
#    epochs = Setting(5)
#    num_epochs = Setting(5)
    modality = Setting('RGB')
    load_pretrained = Setting('True')


    BoundedInt = Setting(10)
    BoundedFloat = Setting(10.0)
    primitive = TSNPrimitive



    def __init__(self):
        super().__init__()
        TODS_BaseWidget.count += 1
        self.primitive_list.append("primitive"+str(len(self.primitive_list)+1))
        print(self.primitive_list)
        self._init_ui()

        self.pipline_in1_flag, self.pipline_in2_flag = False, False
        
        # Info will be passed
        self.hyperparameter = { 'modality':self.modality, 'load_pretrained':self.load_pretrained
                            } #'num_workers':self.num_workers, 'batch_size': self.batch_size,'epochs':self.epochs,
        self.python_path = 'd3m.primitives.autovideo.recognition.tsn'
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

#        gui.doubleSpin(
#            box, self,
#            "num_workers",
#            minv=1,
#            maxv=10,
#            step=1,
#            label="The number of subprocesses to use for data loading. 0 means that the data will be loaded in the main process",
#        )
#
#        gui.lineEdit(box, self, "batch_size", label='The batch size of training',
#                     validator=None, callback=None)
#
#        gui.lineEdit(box, self, "epochs", label='Number of epoch for training',
#                     validator=None, callback=None)

        gui.comboBox(box, self, "modality", sendSelectedValue=True, label='Modality.', items=['RGB', 'RGBDiff', 'Flow'], )
        gui.comboBox(box, self, "load_pretrained", sendSelectedValue=True, label='Load Pretrained.', items=['True', 'False'], )


        # Only for test
        gui.button(box, self, "Print Hyperparameters", callback=self._print_hyperparameter)

    
        self.data = None
        self.info.set_input_summary(self.info.NoInput)
        self.info.set_output_summary(self.info.NoOutput)


    def _use_columns_callback(self):
#        self.use_columns = eval(''.join(self.use_columns_buf))
        self.settings_changed()

    def _exclude_columns_callback(self):
#        self.exclude_columns = eval(''.join(self.exclude_columns_buf))
        self.settings_changed()
    def _print_hyperparameter(self):
#        print(self.num_workers, type(self.num_workers))
#        print(self.batch_size, type(self.batch_size))
#        print(self.epochs, type(self.epochs))
        print(self.return_result, type(self.return_result))
        print(self.load_pretrained, type(self.load_pretrained))


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


#    def settings_changed(self):
#        self.commit()

#    def commit(self):
#        self.hyperparameter['use_columns'] = self.use_columns
#        self.hyperparameter['exclude_columns'] = self.exclude_columns
#
#        self.primitive_info.hyperparameter = self.hyperparameter
#
#        if self.Inputs.pipline_in is not None:
#            self.Outputs.pipline_out.send([self.output_list + [self.primitive_info], self.id])

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
            self.Outputs.pipline_out.send([output_list, self.id])

            return

        elif self.pipline_in1_flag or self.pipline_in2_flag:
            self.primitive_info.ancestors = {}
            self.Outputs.pipline_out.send(None)

        else:
            self.primitive_info.ancestors = {}
            self.Outputs.pipline_out.send(None)


if __name__ == "__main__":
    WidgetPreview(OWTSN).run(Orange.data.Table("iris"))

    


"""def _use_columns_callback(self):
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
    WidgetPreview(OWTSN).run(Orange.data.Table("iris"))"""

