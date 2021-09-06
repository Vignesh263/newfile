# Copyright 2019 The TensorFlow Authors All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Core model definition of YAMNet."""

import csv

import numpy as np
import tensorflow as tf
from tensorflow.keras import Model, layers

import features as features_lib


def _batch_norm(name, params):
  return layers.BatchNormalization(
      name=name,
      center=params.batchnorm_center,
      scale=params.batchnorm_scale,
      epsilon=params.batchnorm_epsilon)


def _conv(name, kernel, stride, filters, params):
  return [
      layers.Conv2D(name='{}/conv'.format(name),
                    filters=filters,
                    kernel_size=kernel,
                    strides=stride,
                    padding=params.conv_padding,
                    use_bias=False,
                    activation=None),
      _batch_norm('{}/conv/bn'.format(name), params),
      layers.ReLU(name='{}/relu'.format(name)),
  ]


def _separable_conv(name, kernel, stride, filters, params):
  return [
      layers.DepthwiseConv2D(name='{}/depthwise_conv'.format(name),
                             kernel_size=kernel,
                             strides=stride,
                             depth_multiplier=1,
                             padding=params.conv_padding,
                             use_bias=False,
                             activation=None),
      _batch_norm('{}/depthwise_conv/bn'.format(name), params),
      layers.ReLU(name='{}/depthwise_conv/relu'.format(name)),
      layers.Conv2D(name='{}/pointwise_conv'.format(name),
                    filters=filters,
                    kernel_size=(1, 1),
                    strides=1,
                    padding=params.conv_padding,
                    use_bias=False,
                    activation=None),
      _batch_norm('{}/pointwise_conv/bn'.format(name), params),
      layers.ReLU(name='{}/pointwise_conv/relu'.format(name)),
  ]


_YAMNET_LAYER_DEFS = [
    # (layer_function, kernel, stride, num_filters)
    (_conv,           [3, 3], 2,   32),
    (_separable_conv, [3, 3], 1,   64),
    (_separable_conv, [3, 3], 2,  128),
    (_separable_conv, [3, 3], 1,  128),
    (_separable_conv, [3, 3], 2,  256),
    (_separable_conv, [3, 3], 1,  256),
    (_separable_conv, [3, 3], 2,  512),
    (_separable_conv, [3, 3], 1,  512),
    (_separable_conv, [3, 3], 1,  512),
    (_separable_conv, [3, 3], 1,  512),
    (_separable_conv, [3, 3], 1,  512),
    (_separable_conv, [3, 3], 1,  512),
    (_separable_conv, [3, 3], 2, 1024),
    (_separable_conv, [3, 3], 1, 1024),
]

class YAMNetBase(tf.keras.Model):
  """Define the core YAMNet mode in Keras."""

  def __init__(self, params):
    super().__init__()
    self._params = params

    self.stack = []
    for (
          i, (layer_fun, kernel, stride, filters)
        ) in enumerate(_YAMNET_LAYER_DEFS):
      new_layers = layer_fun('layer{}'.format(i + 1), kernel, stride, filters,
                             params)
      self.stack.extend(new_layers)
    self.pool = layers.GlobalAveragePooling2D()
    self.logits_from_embedding = layers.Dense(
        units=params.num_classes, use_bias=True)
    self.predictions_from_logits = layers.Activation(
        activation=params.classifier_activation)

  def call(self, features, training=False):
    # Shape: [batch, width, height] > [batch, width, height, 1]
    net = tf.expand_dims(features, axis=-1)

    for layer in self.stack:
      net = layer(net, training=training)

    embeddings = self.pool(net, training=training)

    logits = self.logits_from_embedding(embeddings, training=training)

    predictions = self.predictions_from_logits(logits, training=training)

    outputs = {
      'embeddings': embeddings,
      'logits': logits,
      'predictions': predictions,
    }
    return outputs


class YAMNetWaves(tf.keras.Model):
  """Defines the YAMNet waveform-to-class-scores model.

  Args:
    params: An instance of `params.Params` containing hyperparameters.
  """

  def __init__(self, params):
    super().__init__()
    self._params = params
    self._yamnet_base = YAMNetBase(params)

  @property
  def layers(self):
    return self._yamnet_base.layers

  def call(self, waveforms, training=False):
    """Runs the waveform-to-class-scores model.

    Args:
      waveforms: A tensor containing the input waverform(s) with shape
        `(samples,)` or `(batch, samples)`.

    Returns:
      A tuple of results (predictions, embeddings, log_mel_spectrograms). The
      results will have an outer `batch` axis if the `waveforms` input has
      a `batch` axis.

      predictions: (batch?, num_patches, num_classes) matrix of class scores per
        time frame
      embeddings: (batch?, num_patches, embedding size) matrix of embeddings per
        time frame
      log_mel_spectrogram: (batch?, num_spectrogram_frames, num_mel_bins)
        spectrogram feature matrix
    """
    waveforms_padded = features_lib.pad_waveform(waveforms, self._params)

    log_mel_spectrogram = features_lib.waveform_to_log_mel_spectrogram(waveforms_padded,
                                                                       self._params)

    patches = features_lib.waveform_to_patches(waveforms_padded, self._params)

    features = features_lib.waveform_to_log_mel_spectrogram(
        patches, self._params)

    # Reshape (a, b, width, height) > (a*b, width, height)
    features, batch_shape = flatten_outer_dims(features, item_dims=2)

    outputs = self._yamnet_base.call(features)

    outputs = {name: fold_batch(out, batch_shape)
               for name, out in outputs.items()}
    outputs['log_mel_spectrogram'] = log_mel_spectrogram

    return outputs

def flatten_outer_dims(x, item_dims):
  shape = tf.shape(x)
  batch_shape = shape[:-item_dims]
  item_shape = shape[-item_dims:]
  flattened_batch_shape = tf.concat([[-1], item_shape], axis=-1)
  x = tf.reshape(x, flattened_batch_shape)
  return x, batch_shape

def fold_batch(x, batch_shape):
  # The outputs have a different item_shape, you can't reuse the item_shape.
  # The first dimension is the batch everything else is the item.
  item_shape = tf.shape(x)[1:]
  new_shape = tf.concat([batch_shape, item_shape], axis=-1)
  return tf.reshape(x, new_shape)


def class_names(class_map_csv):
  """Read the class name definition file and return a list of strings."""
  if tf.is_tensor(class_map_csv):
    class_map_csv = class_map_csv.numpy()
  with open(class_map_csv) as csv_file:
    reader = csv.reader(csv_file)
    next(reader)   # Skip header
    return np.array([display_name for (_, _, display_name) in reader])
