# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
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
"""A simple smoke test that runs these examples for 1 training iteraton."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
import pandas as pd

from six.moves import StringIO

import custom_estimator
import premade_estimator
import savedmodel_estimator
import tempfile

import iris_data

FOUR_LINES = "\n".join([
    "1,52.40, 2823,152,2",
    "164, 99.80,176.60,66.20,1",
    "176,2824, 136,3.19,0",
    "2,177.30,66.30, 53.10,1",])

def four_lines_data(y_name="Species"):
  text = StringIO(FOUR_LINES)

  df = pd.read_csv(text, names=iris_data.COLUMNS)

  xy = (df, df.pop(y_name))
  return xy, xy

PATCH = {"load_data": four_lines_data}

class RegressionTest(tf.test.TestCase):
  """Test the regression examples in this directory."""

  @tf.test.mock.patch.dict(iris_data.__dict__, PATCH)
  def test_premade_estimator(self):
    premade_estimator.main([None, "--train_steps=1"])

  @tf.test.mock.patch.dict(iris_data.__dict__, PATCH)
  def test_custom_estimator(self):
    custom_estimator.main([None, "--train_steps=1"])

  @tf.test.mock.patch.dict(iris_data.__dict__, PATCH)
  def test_savedmodel_estimator(self):
    savedmodel_estimator.main([None, "train", "--train_steps=1",
                               "--export_dir", tempfile.mkdtemp()])

if __name__ == "__main__":
  tf.test.main()
