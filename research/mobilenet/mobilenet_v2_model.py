# Copyright 2020 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
"""MobileNet v2.

Adapted from tf.keras.applications.mobilenet_v2.MobileNetV2().

Architecture: https://arxiv.org/abs/1801.04381

The base model gives 72.2% accuracy on ImageNet, with 300MMadds,
3.4 M parameters.
"""

import logging
from typing import Tuple, Union, Text, Dict

import tensorflow as tf

from research.mobilenet import common_modules
from research.mobilenet.configs import archs

layers = tf.keras.layers

MobileNetV2Config = archs.MobileNetV2Config


def _inverted_res_block(inputs: tf.Tensor,
                        filters: int,
                        width_multiplier: float,
                        min_depth: int,
                        weight_decay: float,
                        stddev: float,
                        activation_name: Text = 'relu6',
                        normalization_name: Text = 'batch_norm',
                        normalization_params: Dict = {},
                        dilation_rate: int = 1,
                        expansion_size: int = 6,
                        regularize_depthwise: bool = False,
                        use_explicit_padding: bool = False,
                        residual=True,
                        kernel: Union[int, Tuple[int, int]] = (3, 3),
                        strides: Union[int, Tuple[int, int]] = 1,
                        block_id: int = 1
                        ) -> tf.Tensor:
  """Depthwise Convolution Block with expansion.

  Builds a composite convolution that has the following structure
  expansion (1x1) -> depthwise (kernel_size) -> projection (1x1)

  Args:
    inputs: Input tensor of shape [batch_size, height, width, channels]
    filters: the dimensionality of the output space
      (i.e. the number of output filters in the convolution).
    width_multiplier: controls the width of the network.
      - If `width_multiplier` < 1.0, proportionally decreases the number
            of filters in each layer.
      - If `width_multiplier` > 1.0, proportionally increases the number
            of filters in each layer.
      - If `width_multiplier` = 1, default number of filters from the paper
            are used at each layer.
      This is called `width multiplier (\alpha)` in the original paper.
    min_depth: Minimum depth value (number of channels) for all convolution ops.
      Enforced when width_multiplier < 1, and not an active constraint when
      width_multiplier >= 1.
    weight_decay: The weight decay to use for regularizing the model.
    stddev: The standard deviation of the trunctated normal weight initializer.
    activation_name: Name of the activation function
    normalization_name: Name of the normalization layer
    normalization_params: Parameters passed to normalization layer
    dilation_rate: an integer or tuple/list of 2 integers, specifying
      the dilation rate to use for dilated convolution.
      Can be a single integer to specify the same value for
      all spatial dimensions.
    expansion_size: the size of expansion, could be a constant or a callable.
      If latter it will be provided 'num_inputs' as an input. For forward
      compatibility it should accept arbitrary keyword arguments.
      Default will expand the input by factor of 6.
    regularize_depthwise: Whether or not apply regularization on depthwise.
    use_explicit_padding: Use 'VALID' padding for convolutions, but prepad
      inputs so that the output dimensions are the same as if 'SAME' padding
      were used.
    residual: whether to include residual connection between input
      and output.
    kernel: An integer or tuple/list of 2 integers, specifying the
      width and height of the 2D convolution window.
      Can be a single integer to specify the same value for
      all spatial dimensions.
    strides: An integer or tuple/list of 2 integers,
        specifying the strides of the convolution
        along the width and height.
        Can be a single integer to specify the same value for
        all spatial dimensions.
        Specifying any stride value != 1 is incompatible with specifying
        any `dilation_rate` value != 1.
    block_id: a unique identification designating the block number.

  Returns:
    Tensor of depth num_outputs
  """

  prefix = 'block_{}_'.format(block_id)
  filters = common_modules.width_multiplier_op_divisible(
    filters=filters,
    width_multiplier=width_multiplier,
    min_depth=min_depth)

  activation_fn = archs.get_activation_function()[activation_name]
  normalization_layer = archs.get_normalization_layer()[
    normalization_name]

  weights_init = tf.keras.initializers.TruncatedNormal(stddev=stddev)
  regularizer = tf.keras.regularizers.L1L2(l2=weight_decay)
  depth_regularizer = regularizer if regularize_depthwise else None

  # Expand
  in_channels = inputs.shape.as_list()[-1]
  expended_size = common_modules.expand_input_by_factor(
    num_inputs=in_channels,
    expansion_size=expansion_size)
  x = layers.Conv2D(filters=expended_size,
                    kernel_size=kernel,
                    strides=strides,
                    padding='SAME',
                    kernel_initializer=weights_init,
                    kernel_regularizer=regularizer,
                    use_bias=False,
                    name=prefix + 'expand')(inputs)

  x = normalization_layer(axis=-1,
                          name=prefix + 'expend_{}'.format(normalization_name),
                          **normalization_params)(x)
  x = layers.Activation(activation=activation_fn,
                        name=prefix + 'expand_{}'.format(activation_name))(x)

  # Depthwise
  padding = 'SAME'
  if use_explicit_padding:
    padding = 'VALID'
    x = common_modules.FixedPadding(
      kernel_size=kernel,
      name=prefix + 'pad')(x)

  x = layers.DepthwiseConv2D(kernel_size=kernel,
                             padding=padding,
                             depth_multiplier=1,
                             strides=strides,
                             kernel_initializer=weights_init,
                             kernel_regularizer=depth_regularizer,
                             dilation_rate=dilation_rate,
                             use_bias=False,
                             name=prefix + 'depthwise')(x)
  x = normalization_layer(axis=-1,
                          name=prefix + 'depthwise_{}'.format(
                            normalization_name),
                          **normalization_params)(x)
  x = layers.Activation(activation=activation_fn,
                        name=prefix + 'depthwise_{}'.format(activation_name))(x)

  # Project
  x = layers.Conv2D(filters=filters,
                    kernel_size=(1, 1),
                    padding='SAME',
                    strides=(1, 1),
                    kernel_initializer=weights_init,
                    kernel_regularizer=regularizer,
                    use_bias=False,
                    name=prefix + 'project')(x)
  x = normalization_layer(axis=-1,
                          name=prefix + 'project_{}'.format(normalization_name),
                          **normalization_params)(x)

  if (residual and
      # stride check enforces that we don't add residuals when spatial
      # dimensions are None
      strides == 1 and
      # Depth matches
      in_channels == filters):
    x = layers.Add(name=prefix + 'add')([inputs, x])
  return x


def mobilenet_v2_base(inputs: tf.Tensor,
                      config: MobileNetV2Config
                      ) -> tf.Tensor:
  """Build the base MobileNet architecture."""

  min_depth = config.min_depth
  width_multiplier = config.width_multiplier
  finegrain_classification_mode = config.finegrain_classification_mode
  weight_decay = config.weight_decay
  stddev = config.stddev
  regularize_depthwise = config.regularize_depthwise
  batch_norm_decay = config.batch_norm_decay
  batch_norm_epsilon = config.batch_norm_epsilon
  output_stride = config.output_stride
  use_explicit_padding = config.use_explicit_padding
  activation_name = config.activation_name
  normalization_name = config.normalization_name
  normalization_params = {
    'momentum': batch_norm_decay,
    'epsilon': batch_norm_epsilon
  }
  blocks = config.blocks

  if width_multiplier <= 0:
    raise ValueError('depth_multiplier is not greater than zero.')

  if output_stride is not None and output_stride not in [8, 16, 32]:
    raise ValueError('Only allowed output_stride values are 8, 16, 32.')

  if finegrain_classification_mode and width_multiplier < 1.0:
    blocks[-1].filters /= width_multiplier

  # The current_stride variable keeps track of the output stride of the
  # activations, i.e., the running product of convolution strides up to the
  # current network layer. This allows us to invoke atrous convolution
  # whenever applying the next convolution would result in the activations
  # having output stride larger than the target output_stride.
  current_stride = 1

  # The atrous convolution rate parameter.
  rate = 1

  net = inputs
  for i, block_def in enumerate(blocks):
    if output_stride is not None and current_stride == output_stride:
      # If we have reached the target output_stride, then we need to employ
      # atrous convolution with stride=1 and multiply the atrous rate by the
      # current unit's stride for use in subsequent layers.
      layer_stride = 1
      layer_rate = rate
      rate *= block_def.stride
    else:
      layer_stride = block_def.stride
      layer_rate = 1
      current_stride *= block_def.stride
    if block_def.block_type == archs.BlockType.Conv.value:
      if i == 0 or width_multiplier > 1.0:
        filters = common_modules.width_multiplier_op_divisible(
          filters=block_def.filters,
          width_multiplier=width_multiplier,
          min_depth=min_depth)
      else:
        filters = block_def.filters
      net = common_modules.conv2d_block(
        inputs=net,
        filters=filters,
        kernel=block_def.kernel,
        strides=block_def.stride,
        width_multiplier=1,
        min_depth=min_depth,
        weight_decay=weight_decay,
        stddev=stddev,
        use_explicit_padding=use_explicit_padding,
        activation_name=activation_name,
        normalization_name=normalization_name,
        normalization_params=normalization_params,
        block_id=i
      )
    elif block_def.block_type == archs.BlockType.InvertedResConv.value:
      use_rate = rate
      if layer_rate > 1 and block_def.kernel != (1, 1):
        # We will apply atrous rate in the following cases:
        # 1) When kernel_size is not in params, the operation then uses
        #   default kernel size 3x3.
        # 2) When kernel_size is in params, and if the kernel_size is not
        #   equal to (1, 1) (there is no need to apply atrous convolution to
        #   any 1x1 convolution).
        use_rate = layer_rate
      net = _inverted_res_block(
        inputs=net,
        filters=block_def.filters,
        kernel=block_def.kernel,
        strides=layer_stride,
        expansion_size=block_def.expansion_size,
        dilation_rate=use_rate,
        width_multiplier=width_multiplier,
        min_depth=min_depth,
        weight_decay=weight_decay,
        stddev=stddev,
        regularize_depthwise=regularize_depthwise,
        use_explicit_padding=use_explicit_padding,
        activation_name=activation_name,
        normalization_name=normalization_name,
        normalization_params=normalization_params,
        block_id=i
      )
    else:
      raise ValueError('Unknown block type {} for layer {}'.format(
        block_def.block_type, i))
  return net


def mobilenet_v2(input_shape: Tuple[int, int, int] = (224, 224, 3),
                 config: MobileNetV2Config = MobileNetV2Config()
                 ) -> tf.keras.models.Model:
  """Instantiates the MobileNet Model."""

  dropout_keep_prob = config.dropout_keep_prob
  num_classes = config.num_classes
  spatial_squeeze = config.spatial_squeeze
  model_name = config.name

  img_input = layers.Input(shape=input_shape, name='Input')
  x = mobilenet_v2_base(img_input, config)

  # Build top
  # Global average pooling.
  x = layers.GlobalAveragePooling2D(data_format='channels_last',
                                    name='top_GlobalPool')(x)
  x = layers.Reshape((1, 1, x.shape[1]))(x)

  # 1 x 1 x 1024
  x = layers.Dropout(rate=1 - dropout_keep_prob,
                     name='top_Dropout')(x)

  x = layers.Conv2D(filters=num_classes,
                    kernel_size=(1, 1),
                    padding='SAME',
                    name='top_Conv2d_1x1')(x)
  if spatial_squeeze:
    x = layers.Reshape(target_shape=(num_classes,),
                       name='top_SpatialSqueeze')(x)

  x = layers.Activation(activation='softmax',
                        name='top_Predictions')(x)

  return tf.keras.models.Model(inputs=img_input,
                               outputs=x,
                               name=model_name)


if __name__ == '__main__':
  logging.basicConfig(
    format='%(asctime)-15s:%(levelname)s:%(module)s:%(message)s',
    level=logging.INFO)
  model = mobilenet_v2()
  model.compile(
    optimizer='adam',
    loss=tf.keras.losses.categorical_crossentropy,
    metrics=[tf.keras.metrics.categorical_crossentropy])
  logging.info(model.summary())
