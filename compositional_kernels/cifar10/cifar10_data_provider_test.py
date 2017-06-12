# Copyright 2017 The TensorFlow Authors All Rights Reserved.
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

import os.path

import tensorflow as tf

from tensorflow.python.framework import test_util
from base import config
import cifar10_data_provider

class TestCIFAR10DataProvider(test_util.TensorFlowTestCase):

  def testDataProvider(self):
    cifar10_config = cifar10_data_provider.GetCifar10Config()
    cifar10_config.SetValue('base_data_dir',
                          os.path.join(os.path.dirname(__file__), 'datasets'))

    train_data_provider = cifar10_data_provider.CIFAR10_Input(cifar10_config,
                                                              'train')
    test_data_provider = cifar10_data_provider.CIFAR10_Input(cifar10_config,
                                                             'test')
    batch = 128
    with tf.Graph().as_default(), tf.Session('') as sess:
      _, images, labels = train_data_provider.ProvideData(batch)
      _, test_images, test_labels = test_data_provider.ProvideData(batch)
      tf.global_variables_initializer().run(session=sess)
      coord = tf.train.Coordinator()
      threads = tf.train.start_queue_runners(sess, coord)
      for i in range(50):
        images_np, labels_np, test_images_np, test_labels_np = sess.run(
            [images, labels, test_images, test_labels])
        self.assertEqual(images_np.shape, (batch, 24, 24, 6))
        self.assertEqual(labels_np.shape, (batch, 10))
        self.assertEqual(test_images_np.shape, (batch, 24, 24, 6))
        self.assertEqual(test_labels_np.shape, (batch, 10))
      coord.request_stop()
      coord.join(threads)

if __name__ == '__main__':
  tf.test.main()
