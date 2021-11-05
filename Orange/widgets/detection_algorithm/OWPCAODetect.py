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
from tods.detection_algorithm.PCAODetect import *

class OWPCAODetect(SingleInputWidget):
    name = "PCAODetect"
    description = ("PCA-based outlier detection.")
    icon = "icons/PCAOD.svg"
    category = "Detection Algorithm"
    keywords = []

    want_main_area = False
    buttons_area_orientatio = Qt.Vertical
    resizing_enabled = False


    # set default hyperparameters here
    autosend = Setting(True)

    svd_solver = Setting('auto')
    n_components = Setting(None)
    n_selected_components = Setting(None)
    tol = Setting(0.)
    iterated_power = Setting('auto')
    random_state = Setting(None)
    whiten = Setting(True)
    standardization = Setting(True)

    contamination = Setting(0.1)
    window_size = Setting(1)
    step_size = Setting(1)
    return_subseq_inds = Setting(False)

    use_columns_buf = Setting(())
    use_columns = ()
    exclude_columns_buf = Setting(())
    exclude_columns = ()
    return_result = Setting('new')
    use_semantic_types = Setting(False)
    add_index_columns = Setting(False)
    error_on_no_input = Setting(True)
    return_semantic_type = Setting('https://metadata.datadrivendiscovery.org/types/Attribute')

    primitive = PCAODetectorPrimitive



    


    def _use_columns_callback(self):
        self.use_columns = eval(''.join(self.use_columns_buf))
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

        gui.comboBox(box, self, 'svd_solver', label='Algorithm of solver.',
                     items=['auto', 'full', 'arpack', 'randomized'], callback=None)

        gui.lineEdit(box, self, 'n_components', label='Number of components to keep. (IntVariable or None)', callback=None)
        gui.lineEdit(box, self, 'n_selected_components', label='Number of selected principal components for calculating outlier scores. (Int or None)', callback=None)
        gui.lineEdit(box, self, 'tol', label='Tolerance for singular values computed by svd_solver is arpack. (Float)', callback=None)
        gui.lineEdit(box, self, 'iterated_power', label='Number of iterations for the power method computed by svd_solver is randomized. (Int or auto)', callback=None)
        gui.lineEdit(box, self, 'random_state', label='Seed used by the random number generator. (Int or None)', callback=None)
        gui.checkBox(box, self, "whiten", label='Using eigenvalues to calculate outlier scores.',  callback=None)
        gui.checkBox(box, self, "standardization", label='Convert the data to zero mean and unit variance.',  callback=None)

        gui.doubleSpin(
            box, self,
            "contamination",
            minv=0.,
            maxv=1.,
            step=0.001,
            label="Input contamination, float in (0,0.5].",
            # callbackOnReturn = True,
            # checked = "BoundedFloat"
        )

        gui.lineEdit(box, self, 'window_size', label='The moving window size. (IntVariable)', callback=None)

        gui.lineEdit(box, self, 'step_size', label='The displacement for moving window. (IntVariable)', callback=None)

        # return_subseq_inds = Setting(False)
        gui.checkBox(box, self, "return_subseq_inds", label='If return subsequence index.',  callback=None)

        # use_semantic_types = Setting(False)
        gui.checkBox(box, self, "use_semantic_types", label='Mannally select columns if active.',  callback=None)

        # use_columns = Setting(())
        gui.lineEdit(box, self, "use_columns_buf", label='Column index to use when use_semantic_types is activated. Tuple, e.g. (0,1,2)',
                     validator=None, callback=self._use_columns_callback)

        # exclude_columns = Setting(())
        gui.lineEdit(box, self, "exclude_columns_buf", label='Column index to exclude when use_semantic_types is activated. Tuple, e.g. (0,1,2)',
                     validator=None, callback=self._exclude_columns_callback)

        # return_result = Setting(['append', 'replace', 'new'])
        gui.comboBox(box, self, "return_result", sendSelectedValue=True, label='Output results.', items=['new', 'append', 'replace'], )

        # add_index_columns = Setting(False)
        gui.checkBox(box, self, "add_index_columns", label='Keep index in the outputs.',  callback=None)

        # error_on_no_input = Setting(True)
        gui.checkBox(box, self, "error_on_no_input", label='Error on no input.',  callback=None)

        # return_semantic_type = Setting(['https://metadata.datadrivendiscovery.org/types/Attribute',
        #                                 'https://metadata.datadrivendiscovery.org/types/ConstructedAttribute'])
        gui.comboBox(box, self, "return_semantic_type", sendSelectedValue=True, label='Semantic type attach with results.', items=['https://metadata.datadrivendiscovery.org/types/Attribute',
                                                                                        'https://metadata.datadrivendiscovery.org/types/ConstructedAttribute'], )
        # Only for test
        gui.button(box, self, "Print Hyperparameters", callback=self._print_hyperparameter)

        gui.auto_apply(box, self, "autosend", box=False)

        self.data = None
        self.info.set_input_summary(self.info.NoInput)
        self.info.set_output_summary(self.info.NoOutput)

    def _print_hyperparameter(self):
        print(self.IntVariable, type(self.IntVariable))
        print(self.FloatVariable, type(self.FloatVariable))
        print(self.BoolVariable, type(self.BoolVariable))
        print(self.TupleVariable, type(self.TupleVariable))
        print(self.ListVariable, type(self.ListVariable))
        print(self.EnumVariable, type(self.EnumVariable))
        print(self.BoundedInt, type(self.BoundedInt))
        print(self.BoundedFloat, type(self.BoundedFloat))
        print(self.contamination, type(self.contamination))
        print(self.return_subseq_inds, type(self.return_subseq_inds))
        print(self.use_columns, type(self.use_columns))
        print(self.exclude_columns, type(self.exclude_columns))
        print(self.return_result, type(self.return_result))
        print(self.use_semantic_types, type(self.use_semantic_types))
        print(self.add_index_columns, type(self.add_index_columns))
        print(self.error_on_no_input, type(self.error_on_no_input))
        print(self.return_semantic_type, type(self.return_semantic_type))


        self.commit()

    

    

    

    

if __name__ == "__main__":
    WidgetPreview(OWPyodKNN).run(Orange.data.Table("iris"))