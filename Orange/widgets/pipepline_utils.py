from d3m import index
from d3m.metadata.base import ArgumentType
from d3m.metadata.pipeline import Pipeline, PrimitiveStep
from d3m.metadata import hyperparams
import sys

def build_pipeline(pipepline_info, pipepline_mapping, stdout=None):
    
    
    default_stdout = sys.stdout
    if stdout is not None:
        sys.stdout = stdout

    # Creating pipeline
    pipeline_description = Pipeline()
    pipeline_description.add_input(name='inputs')
    data1 = None
    dict_hyper = {}
    counter = 0 #For keeping track of the placeholder for video procesing fake primitive
    flag_c = 0 #Same as above purpose
    for primitive_info in pipepline_info:
        
        #print("PIPELINE DESCRIPTOION: ", pipeline_description)
#        print("PPPPP: ", primitive_info)
#        print("PRIMITIVES: ")
        print(primitive_info.python_path)
        print(primitive_info.hyperparameter)
        print(primitive_info.ancestors)

        if primitive_info.python_path == 'HEAD':
            dataset_fullname = "/Users/zaidbhat/autovideo/datasets/hmdb6"
            dataset_fullname = primitive_info.hyperparameter['dataset_folder']
            data1 = dataset_fullname
            print(dataset_fullname)
            continue

        elif primitive_info.python_path == 'ENDING':

            ancestors = primitive_info.ancestors
            end_step_num = pipepline_mapping[ancestors['inputs']] - 1 - flag_c
            pipeline_description.add_output(name='output predictions', data_reference='steps.' + str(end_step_num) + '.produce')

        else:
            counter+=1
            # print(primitive_info.python_path)
            if counter ==2:
                flag_c = 1
                continue
            if counter ==3:
                flag_c = 2
                continue
            primitive = index.get_primitive(primitive_info.python_path)
            step = PrimitiveStep(primitive=primitive)
            print("STEP:", step, primitive, ":")

            hyperparameters = primitive_info.hyperparameter
            ancestors = primitive_info.ancestors
#            print("HYPER: ", hyperparameters, ancestors)
            # add add_inputs
            # print(ancestors)
            flag = 0
            #alg = None
            if ancestors['inputs'] != 0:
                for ances_key in ancestors.keys():
                    print("CONST: ", ances_key, ancestors[ances_key], pipepline_mapping)
#                    print("KKKK",ances_key, ancestors[ances_key], pipepline_mapping[ancestors[ances_key]] - 1)

                    step_num = pipepline_mapping[ancestors[ances_key]] - 1 - flag_c
                    print("STEP NUM:", step_num)
#                    if 'recognition' in str(primitive):
#                        dict_hyper['algorithm'] = str(primitive).split('.')[-1]
#                        flag = 1
#                        step.add_argument(name='outputs', argument_type=ArgumentType.CONTAINER, data_reference='steps.' + str(step_num) + '.produce')
#                        step.add_argument(name=ances_key, argument_type=ArgumentType.CONTAINER, data_reference='steps.' + str(step_num) + '.produce')
#                    else:
                    step.add_argument(name=ances_key, argument_type=ArgumentType.CONTAINER, data_reference='steps.' + str(step_num) + '.produce')

            else:
                step.add_argument(name='inputs', argument_type=ArgumentType.CONTAINER, data_reference='inputs.0')

            # add add_hyperparameter
            for hyper in hyperparameters.keys():
                # print(hyper, hyperparameters[hyper], type(hyperparameters[hyper]))
                
                
                hyper_value = hyperparameters[hyper]
                if hyper =='load_pretrained':
                    if hyper_value =='False':
                        hyper_value = False
                    else:
                        hyper_value = True

                step.add_hyperparameter(name=hyper, argument_type=ArgumentType.VALUE, data=hyper_value)

            step.add_output('produce')
            pipeline_description.add_step(step)

            # print('\n')
#        data = pipeline_description.to_json()
    #print("Pipeline Description:", data)
    # Output to json
    data = pipeline_description.to_json()
    with open('example_pipeline.json', 'w') as f:
        f.write(data)
        print(data)

#     yaml = pipeline_description.to_yaml()
#     with open('example_pipeline.yml', 'w') as f:
#         f.write(yaml)
    # print(yaml)
    #print("KKKKK", data1)
    #print("DICT: ", dict_hyper)
    sys.stdout.flush()
    sys.stdout = default_stdout
    return pipeline_description
#    return dict_hyper

import sys
import argparse
import os
import pandas as pd

from tods import generate_dataset, load_pipeline, evaluate_pipeline

from PyQt5.QtWidgets import QMessageBox, QWidget

def run_pipeline(pipepline_info, stdout=None):
    
    default_stdout = sys.stdout
    if stdout is not None:
        sys.stdout = stdout

    # this_path = os.path.dirname(os.path.abspath(__file__))

    dataset_folder = pipepline_info[0].hyperparameter['dataset_folder']
    if dataset_folder is None:
        tmp_QWidget = QWidget()
        QMessageBox.warning(tmp_QWidget, 'Attention!', 'You must choose a dataset folder!')
        del(tmp_QWidget)

    elif not os.path.exists(os.path.join(dataset_folder, 'datasetDoc.json')) \
            or not os.path.exists(os.path.join(dataset_folder, 'tables', 'learningData.csv')):
        tmp_QWidget = QWidget()
        QMessageBox.warning(tmp_QWidget, 'Attention!', 'No dataset in the folder!')
        del (tmp_QWidget)

    else:
        dataset_info = dataset_description(os.path.join(dataset_folder, 'datasetDoc.json'))
        dataset_fullname = os.path.join(dataset_folder, 'tables', 'learningData.csv')
        table_path = dataset_fullname
        target_index = dataset_info['ground_truth_index'] # what column is the target, up to revised!!!
        pipeline_path = './example_pipeline.json'
        metric = 'F1_MACRO' # F1 on both label 0 and 1

        print(target_index)

        # Read data and generate dataset
        df = pd.read_csv(table_path)
        dataset = generate_dataset(df, target_index)
        print(df)

        # Load the default pipeline
        pipeline = load_pipeline(pipeline_path)
        # # Run the pipeline
        pipeline_result = evaluate_pipeline(dataset, pipeline, metric)
        print(pipeline_result)
        print(pipeline_result.scores)

    sys.stdout.flush()
    sys.stdout = default_stdout


import json

def dataset_description(description_fname):

    dataset_info = {}
    with open(description_fname, 'r') as f:
        description = json.loads(f.read())
        # print(description['dataResources'][0]['columns'][7]['colName'])
        for column_index, column in enumerate(description['dataResources'][0]['columns']):
            if column['colName'] == 'ground_truth':
                # print(column_index)
                dataset_info['ground_truth_index'] = column_index
                return dataset_info

