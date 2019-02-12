# Copyright 2018 The TensorFlow Authors. All Rights Reserved.
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
"""Helper functions for running models in a distributed setting."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import string
import tensorflow as tf


def get_distribution_strategy(distribute_strategy="default",
                              num_gpus=0,
                              all_reduce_alg=None):
  """Return a DistributionStrategy for running the model.

  Args:
    distribute_strategy: a string specify which distribution strategy to use.
      Accepted values are 'off', 'default', 'one_device', 'mirrored',
      'parameter_server', 'collective', case insensitive. 'off' means not to use
      Distribution Strategy; 'default' means to choose from `MirroredStrategy`
      or `OneDeviceStrategy` according to the number of GPUs."
    num_gpus: Number of GPUs to run this model.
    all_reduce_alg: Optional. Specify which algorithm to use when performing
      all-reduce. See tf.contrib.distribute.AllReduceCrossDeviceOps for
      available algorithms. If None, DistributionStrategy will choose based on
      device topology.

  Returns:
    tf.distribute.DistibutionStrategy object.
  Raises:
    ValueError: if distribute_strategy is 'off' or 'one_device' and num_gpus is
      larger than 1
  """
  distribute_strategy = distribute_strategy.lower()
  if distribute_strategy == "off":
    if num_gpus > 1:
      raise ValueError("When {} GPUs are specified, distribute_strategy flag "
                       "cannot be set to 'off'.".format(num_gpus))
    return None

  if (distribute_strategy == "one_device" or
      (distribute_strategy == "default" and num_gpus <= 1)):
    if num_gpus == 0:
      return tf.contrib.distribute.OneDeviceStrategy("device:CPU:0")
    else:
      if num_gpus > 1:
        raise ValueError("`OneDeviceStrategy` can not be used for more than "
                         "one device.")
      return tf.contrib.distribute.OneDeviceStrategy("device:GPU:0")

  if distribute_strategy == "mirrored" or not distribute_strategy:
    devices = ["device:GPU:%d" % i for i in range(num_gpus)]
    if all_reduce_alg:
      return tf.distribute.MirroredStrategy(
          devices=devices,
          cross_device_ops=tf.contrib.distribute.AllReduceCrossDeviceOps(
              all_reduce_alg, num_packs=2))
    else:
      return tf.distribute.MirroredStrategy(devices=devices)

  if distribute_strategy == "collective":
    return tf.contrib.distribute.CollectiveAllReduceStrategy(
        num_gpus_per_worker=num_gpus)

  if distribute_strategy == "parameter_server":
    return tf.contrib.distribute.ParameterServerStrategy(
        num_gpus_per_worker=num_gpus)

  raise ValueError(
      "Uncognized Distribution Strategy: %r" % distribute_strategy)


def per_device_batch_size(batch_size, num_gpus):
  """For multi-gpu, batch-size must be a multiple of the number of GPUs.


  Note that distribution strategy handles this automatically when used with
  Keras. For using with Estimator, we need to get per GPU batch.

  Args:
    batch_size: Global batch size to be divided among devices. This should be
      equal to num_gpus times the single-GPU batch_size for multi-gpu training.
    num_gpus: How many GPUs are used with DistributionStrategies.

  Returns:
    Batch size per device.

  Raises:
    ValueError: if batch_size is not divisible by number of devices
  """
  if num_gpus <= 1:
    return batch_size

  remainder = batch_size % num_gpus
  if remainder:
    err = ("When running with multiple GPUs, batch size "
           "must be a multiple of the number of available GPUs. Found {} "
           "GPUs with a batch size of {}; try --batch_size={} instead."
          ).format(num_gpus, batch_size, batch_size - remainder)
    raise ValueError(err)
  return int(batch_size / num_gpus)

# The `SyntheticDataset` is a temporary solution for generating synthetic data
# directly on devices. It is only useful for Keras with Distribution
# Strategies. We will have better support in `tf.data` or Distribution Strategy
# later.
class SyntheticDataset(object):
  """A dataset that generates synthetic data on each device."""

  def __init__(self, dataset, split_by=1):
    self._input_data = {}
    # dataset.take(1) doesn't have GPU kernel.
    with tf.device("device:CPU:0"):
      tensor = tf.data.experimental.get_single_element(dataset.take(1))
    flat_tensor = tf.nest.flatten(tensor)
    variable_data = []
    self._initializers = []
    for t in flat_tensor:
      rebatched_t = tf.split(t, num_or_size_splits=split_by, axis=0)[0]
      assert rebatched_t.shape.is_fully_defined(), rebatched_t.shape
      v = tf.get_local_variable(self.random_name(), initializer=rebatched_t)  # pylint: disable=cell-var-from-loop
      variable_data.append(v)
      self._initializers.append(v.initializer)
    self._input_data = tf.nest.pack_sequence_as(tensor, variable_data)

  def get_next(self):
    return self._input_data

  def initialize(self):
    if tf.executing_eagerly():
      return tf.no_op()
    else:
      return self._initializers

  def random_name(self, size=10, chars=string.ascii_uppercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def _monkey_patch_dataset_method(strategy):
  """Monkey-patch `strategy`'s `make_dataset_iterator` method."""
  def make_dataset_iterator(self, dataset):
    tf.logging.info("Using pure synthetic data.")
    with self.scope():
      if self.extended._global_batch_size:  # pylint: disable=protected-access
        return SyntheticDataset(dataset, self.num_replicas_in_sync)
      else:
        return SyntheticDataset(dataset)

  strategy.org_make_dataset_iterator = strategy.make_dataset_iterator
  strategy.make_dataset_iterator = make_dataset_iterator


def _undo_monkey_patch_dataset_method(strategy):
  if hasattr(strategy, "org_make_dataset_iterator"):
    strategy.make_dataset_iterator = strategy.org_make_dataset_iterator


def set_up_synthetic_data():
  _monkey_patch_dataset_method(tf.distribute.MirroredStrategy)
  _monkey_patch_dataset_method(tf.contrib.distribute.MirroredStrategy)
  _monkey_patch_dataset_method(tf.contrib.distribute.OneDeviceStrategy)


def undo_set_up_synthetic_data():
  _undo_monkey_patch_dataset_method(tf.distribute.MirroredStrategy)
  _undo_monkey_patch_dataset_method(tf.contrib.distribute.MirroredStrategy)
  _undo_monkey_patch_dataset_method(tf.contrib.distribute.OneDeviceStrategy)
