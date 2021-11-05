from functools import reduce
from types import SimpleNamespace

from AnyQt.QtCore import Qt
from AnyQt.QtWidgets import QGridLayout
from AnyQt.QtWidgets import QFormLayout

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
from tods.feature_analysis.SKTruncatedSVD import *

class OWSKTruncatedSVD(SingleInputWidget):
    name = "SKTruncatedSVD"
    description = ("Primitive wrapping for sklearn TruncatedSVD.")
    icon = "icons/svd.svg"
    category = "Feature Analysis"
    keywords = []


    want_main_area = False
    buttons_area_orientatio = Qt.Vertical
    resizing_enabled = False


    # set default hyperparameters here
    test_treatment = Setting(0)
    autosend = Setting(True)
    
    n_components = Setting(2)
    algorithm = Setting('randomized')

    use_columns_buf = Setting(())
    use_columns = ()
    exclude_columns_buf = Setting(())
    exclude_columns = ()
    return_result = Setting('new')
    use_semantic_types = Setting(False)
    add_index_columns = Setting(False)
    error_on_no_input = Setting(True)
    return_semantic_type = Setting('https://metadata.datadrivendiscovery.org/types/Attribute')
    
    hyperparameter_list=['n_components',
                        'algorithm',
                        'use_columns',
                        'exclude_columns',
                        'return_result',
                        'use_semantic_types',
                        'add_index_columns',
                        'error_on_no_input',
                        'return_semantic_type']
    python_path = "d3m.primitives.tods.feature_analysis.truncated_svd"

    primitive = SKTruncatedSVDPrimitive



    # def __init__(self):
    #     super().__init__()
    #     self.primitive_list.append("primitive"+str(len(self.primitive_list)+1))
    #     print(self.primitive_list)
    #     self._init_ui()

    #     # Info will be passed
    #     self.hyperparameter = {'n_components':self.n_components,
    #                             'algorithm':self.algorithm,
    #                             'use_columns':self.use_columns,
    #                             'exclude_columns':self.exclude_columns,
    #                             'return_result':self.return_result,
    #                             'use_semantic_types':self.use_semantic_types,
    #                             'add_index_columns':self.add_index_columns,
    #                             'error_on_no_input':self.error_on_no_input,
    #                             'return_semantic_type':self.return_semantic_type,                               
    #                         }
        

    #     self.primitive_info = PrimitiveInfo(python_path = self.python_path,
    #                                     hyperparameter = self.hyperparameter,
    #                                     ancestors = {},
    #                                     # descendants = []
    #                                     )

    def __del__(self):
        self.primitive.pop()
        print(self.primitive_list)

    def __init__(self):
        super().__init__()
        self.primitive_list.append("primitive"+str(len(self.primitive_list)+1))
        print(self.primitive_list)
        self._init_ui()


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

        gui.lineEdit(
            box, self, "n_components", label='n_components', valueType=int,
            callback=None)

        gui.comboBox(
            box, self, "algorithm", label='algorithm', items=['randomized', 'arpack'],
            orientation=Qt.Horizontal,)

        gui.checkBox(box, self, "use_semantic_types", label='Mannally select columns if active.',  callback=None)

        gui.lineEdit(box, self, "use_columns_buf", label='Column index to use when use_semantic_types is activated. Tuple, e.g. (0,1,2)',
                     validator=None, callback=self._use_columns_callback)

        gui.lineEdit(box, self, "exclude_columns_buf", label='Column index to exclude when use_semantic_types is activated. Tuple, e.g. (0,1,2)',
                     validator=None, callback=self._exclude_columns_callback)

        gui.comboBox(box, self, "return_result", sendSelectedValue=True, label='Output results.', items=['new', 'append', 'replace'], )

        gui.checkBox(box, self, "add_index_columns", label='Keep index in the outputs.',  callback=None)

        gui.checkBox(box, self, "error_on_no_input", label='Error on no input.',  callback=None)

        gui.comboBox(box, self, "return_semantic_type", sendSelectedValue=True, label='Semantic type attach with results.', items=['https://metadata.datadrivendiscovery.org/types/Attribute',
                                                                                                            'https://metadata.datadrivendiscovery.org/types/ConstructedAttribute'], )
          

        gui.auto_apply(box, self, "autosend", box=False)

        self.data = None
        self.info.set_input_summary(self.info.NoInput)
        self.info.set_output_summary(self.info.NoOutput)

    

       

    


from Orange.widgets.utils.widgetpreview import WidgetPreview
if __name__ == "__main__":
    WidgetPreview(OWSKTruncatedSVD).run(Orange.data.Table("iris"))
