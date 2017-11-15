#  Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Example of DNNClassifier for Iris plant dataset."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys

import numpy as np
import pandas as pd
import tensorflow as tf

try:
    from grpc.beta import implementations
    from tensorflow_serving.apis import prediction_service_pb2
    from tensorflow_serving.apis import predict_pb2
except ImportError:
    pass

import iris_data

parser = argparse.ArgumentParser()

subparser = parser.add_subparsers(dest='sub_command')

DEFAULT_NPY_PATH = "inputs.npy"
train_parser = subparser.add_parser(
    'train', help="Train and export export the model, "
                  "and save the test data into a .npy file")

train_parser.add_argument('--batch_size', default=100,
                          type=int, help='batch size')
train_parser.add_argument('--train_steps', default=200,
                          type=int, help='number of training steps')
train_parser.add_argument('--export_dir', type=str,
                          default="saved_model_exports",
                          help="Base directory to export the model to.")

predict_parser = subparser.add_parser(
    'prediction_client', description="Run the predictions using a "
                                     "tensorflow serving client.")
predict_parser.add_argument('--host', type=str, default='localhost',
                            help="The hostname of the model server.")
predict_parser.add_argument('--port', type=int, default=8500,
                            help="Model server port number.")


def dataset_input_fn(ds):
    return lambda: ds.make_one_shot_iterator().get_next()

def encode_float_dict(example_dict):
    """Serialize a {string:float} dict as a tf.train.Example."""
    # Convert each value into tf.train.Feature
    my_feature_dict = {}
    for key, value in example_dict.items():
        value = tf.train.FloatList(value=[value])
        my_feature_dict[key] = tf.train.Feature(float_list=value)

    # Convert the dict to a tf.train.Example.
    features = tf.train.Features(feature=my_feature_dict)
    example = tf.train.Example(features=features)

    # Return the example, serialize into a string.
    return example.SerializeToString()

def encode_examples(x):
    """Encode a series of examples as tf.train.Examples."""
    for index, row in pd.DataFrame(x).iterrows():
        yield encode_float_dict(dict(row))

def prediction_client(args):
    """Send the iris test data to the tensorflow_model_server."""
    # Give clear error messages.
    error_template = (
        "This sub command requires the `{package}` pip package "
        "please install it with: \n"
        "    pip install {package}")

    if 'implementations' not in globals():
        raise ImportError(error_template.format(package='grpcio'))
    if 'predict_pb2' not in globals():
        if sys.version_info >= (3,0):
            raise ImportError(
                "The tensorflow-serving-api package is not yet available"
                "for python3")
        else:
            raise ImportError(
                error_template.format(package='tensorflow-serving-api'))

    # Load and encode the data
    (train_x,train_y), (test_x, test_y) = iris_data.load_data()
    del train_x, train_y, test_y

    encoded_x = list(encode_examples(test_x))

    # Create a stub connected to host:port.
    channel = implementations.insecure_channel(args.host, args.port)
    stub = prediction_service_pb2.beta_create_PredictionService_stub(channel)

    # Create a prediction request.
    request = predict_pb2.PredictRequest()

    # Use the `predict` method of the model named `serve`.
    request.model_spec.name = 'serve'
    request.model_spec.signature_name = 'predict'

    # Calculate the class_ids and probabilities.
    request.output_filter.append('class_ids')
    request.output_filter.append('probabilities')

    # Attach the examples to the request.
    request.inputs['examples'].CopyFrom(tf.make_tensor_proto(encoded_x))

    # Send the request.
    timeout_seconds = 5.0
    future = stub.Predict.future(request, timeout_seconds)

    # Wait for the result.
    result = future.result()

    # Convert the result to a dictionary of numpy arrays.
    result = dict(result.outputs)
    result = {key: tf.make_ndarray(value) for key, value in result.items()}

    # Print the results
    print("\nClass_ids:")
    print(result['class_ids'])

    print("\nProbabilities for each class:")
    print(result['probabilities'])

def main(argv):
    """Parse argv, and dispatch to the apropriate sub-command."""
    args = parser.parse_args(argv[1:])
    if args.sub_command == "train":
        return train(args)
    else:
        assert args.sub_command == "prediction_client"
        return prediction_client(args)

def train(args):
    """Train a simple model and export it as a Saved Model"""
    # Fetch the datasets
    train_ds, test_ds = iris_data.datasets()

    # Feature columns describe the input: all columns are numeric.
    feature_columns = [tf.feature_column.numeric_column(col_name)
                       for col_name in iris_data.COLUMNS[:-1]]

    # Build 3 layer DNN with 10, 10 units respectively.
    classifier = tf.estimator.DNNClassifier(
        feature_columns=feature_columns,
        hidden_units=[10, 10],
        n_classes=3)

    # Train the Model.
    train_input = (
        train_ds
        .repeat()
        .shuffle(1000)
        .batch(args.batch_size))

    classifier.train(input_fn=dataset_input_fn(train_input),
                     steps=args.train_steps)

    # Build the receiver function.
    my_feature_spec = {}
    for key in iris_data.COLUMNS[:-1]:
        my_feature_spec[key] = tf.FixedLenFeature((), tf.float32)

    my_receiver = tf.estimator.export.build_parsing_serving_input_receiver_fn(
        my_feature_spec)

    # Build the Saved Model.
    savedmodel_path = classifier.export_savedmodel(
        export_dir_base=args.export_dir,
        serving_input_receiver_fn=my_receiver)

    print(u"\nModel exported to:\n    " + savedmodel_path.decode())

if __name__ == '__main__':
    tf.logging.set_verbosity(tf.logging.INFO)
    tf.app.run(main)
