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
"""Preprocess dataset and construct any necessary artifacts."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import contextlib
import multiprocessing
import os
import pickle
import timeit
import typing

# pylint: disable=wrong-import-order
from absl import app as absl_app
from absl import flags
import numpy as np
import pandas as pd
import tensorflow as tf
# pylint: enable=wrong-import-order

from official.datasets import movielens
from official.utils.flags import core as flags_core


_CACHE_SUBDIR = "ncf_recommendation_cache"
_TRAIN_SHARD_SUBDIR = "training_shards"
_APPROX_PTS_PER_SHARD = 32000

# In both datasets, each user has at least 20 ratings.
_MIN_NUM_RATINGS = 20

# The number of negative examples attached with a positive example
# in training dataset.
_NUMBER_NEGATIVES = 999


class NCFDataset(object):
  """Container for training and testing data."""

  def __init__(self, cache_dir, test_data, num_users, num_items,
               num_data_readers, train_data=None, num_train_neg=None):
    # type: (str, typing.Tuple[dict, np.ndarray], int, int, int, dict) -> None
    """Assign values for recommendation dataset.

    The NCF pipeline makes use of both sharded files (training) and in-memory
    (testing) storage. This class contains various constants describing the
    data, as well as information needed to retrieve the training and testing
    values.

    Args:
      cache_dir: The root directory where all artifacts used during training and
        evaluation are stored.
      test_data: The NumPy arrays containing the data used for evaluation. This
        includes the real positive holdout example and the evaluation negatives.
        The positive example is the first example, followed by all negatives.
        (This structure is utilized elsewhere.)
      num_users: The number of users in the dataset. (train and test)
      num_items: The number of items (movies) in the dataset. (train and test)
      num_data_readers: The number of tf.data.Dataset instances to interleave
        during training.
      train_data: A dictionary containing the positive training examples. This
        field should be None during normal operation, but is useful for
        debugging.
    """

    self.cache_dir = cache_dir
    self.train_shard_dir = os.path.join(cache_dir, _TRAIN_SHARD_SUBDIR)
    self.num_data_readers = num_data_readers
    self.test_data = test_data
    true_ind = np.argwhere(test_data[1])[:, 0]
    assert true_ind.shape[0] == num_users

    # Ensure that the positive example comes before the negative examples
    # for a user.
    assert not any([i % (_NUMBER_NEGATIVES + 1) for i in true_ind])

    self.eval_true_items = {
        test_data[0][movielens.USER_COLUMN][i]:
            test_data[0][movielens.ITEM_COLUMN][i] for i in true_ind
    }
    self.eval_all_items = {}
    stride = _NUMBER_NEGATIVES + 1
    for i in range(num_users):
      user = test_data[0][movielens.USER_COLUMN][i * stride]
      items = test_data[0][movielens.ITEM_COLUMN][i * stride: (i + 1) * stride]
      self.eval_all_items[user] = items.tolist()
      assert len(self.eval_all_items[user]) == len(self.eval_all_items[user])

    self.num_users = num_users
    self.num_items = num_items

    # Used for testing the data pipeline. The actual training pipeline uses the
    # shards found in `self.train_shard_dir `
    self.train_data = train_data
    self.num_train_neg = num_train_neg


def _filter_index_sort(raw_rating_path):
  # type: (str) -> (pd.DataFrame, int, int)
  """Read in data CSV, and output structured data.

  This function reads in the raw CSV of positive items, and performs three
  preprocessing transformations:

  1)  Filter out all users who have not rated at least a certain number
      of items. (Typically 20 items)

  2)  Zero index the users and items such that the largest user_id is
      `num_users - 1` and the largest item_id is `num_items - 1`

  3)  Sort the dataframe by user_id, with timestamp as a secondary sort key.
      This allows the dataframe to be sliced by user in-place, and for the last
      item to be selected simply by calling the `-1` index of a user's slice.

  While all of these transformations are performed by Pandas (and are therefore
  single-threaded), they only take ~2 minutes, and the overhead to apply a
  MapReduce pattern to parallel process the dataset adds significant complexity
  for no computational gain. For a larger dataset parallelizing this
  preprocessing could yield speedups. (Also, this preprocessing step is only
  performed once for an entire run.

  Args:
    raw_rating_path: The path to the CSV which contains the raw dataset.

  Returns:
    A filtered, zero-index remapped, sorted dataframe, as well as the number
    of users and items in the processed dataset.
  """
  # type: (str) -> (pd.DataFrame, int, int)
  df = pd.read_csv(raw_rating_path)

  # Get the info of users who have more than 20 ratings on items
  grouped = df.groupby(movielens.USER_COLUMN)
  df = grouped.filter(lambda x: len(x) >= _MIN_NUM_RATINGS)

  original_users = df[movielens.USER_COLUMN].unique()
  original_items = df[movielens.ITEM_COLUMN].unique()

  # Map the ids of user and item to 0 based index for following processing
  tf.logging.info("Generating user_map and item_map...")
  user_map = {user: index for index, user in enumerate(original_users)}
  item_map = {item: index for index, item in enumerate(original_items)}

  df[movielens.USER_COLUMN] = df[movielens.USER_COLUMN].apply(
      lambda user: user_map[user])
  df[movielens.ITEM_COLUMN] = df[movielens.ITEM_COLUMN].apply(
      lambda item: item_map[item])

  num_users = len(original_users)
  num_items = len(original_items)

  assert num_users <= np.iinfo(np.int32).max
  assert num_items <= np.iinfo(np.uint16).max
  assert df[movielens.USER_COLUMN].max() == num_users - 1
  assert df[movielens.ITEM_COLUMN].max() == num_items - 1

  # This sort is used to shard the dataframe by user, and later to select
  # the last item for a user to be used in validation.
  tf.logging.info("Sorting by user, timestamp...")
  df.sort_values([movielens.USER_COLUMN, movielens.TIMESTAMP_COLUMN],
                 inplace=True)

  df = df.reset_index()  # The dataframe does not reconstruct indicies in the
                         # sort or filter steps.

  return df, num_users, num_items


def sample_with_exclusion(num_items, positive_set, n, replacement=True):
  # type: (int, typing.Iterable, int, bool) -> list
  """Vectorized negative sampling.

  This function samples from the positive set's conjugate, both with and
  without replacement.

  Performance:
    This algorithm generates a vector of candidate values based on the expected
    number needed such that at least k are not in the positive set, where k
    is the number of false negatives still needed. An additional factor of
    safety of 1.2 is used during the generation to minimize the chance of having
    to perform another generation cycle.

    While this approach generates more values than needed and then discards some
    of them, vectorized generation is inexpensive and turns out to be much
    faster than generating points one at a time. (And it defers quite a bit
    of work to NumPy which has much better multi-core utilization than native
    Python.)

  Args:
    num_items: The cardinality of the entire set of items.
    positive_set: The set of positive items which should not be included as
      negatives.
    n: The number of negatives to generate.
    replacement: Whether to sample with (True) or without (False) replacement.

  Returns:
    A list of generated negatives.
  """

  if not isinstance(positive_set, set):
    positive_set = set(positive_set)

  p = 1 - len(positive_set) /  num_items
  n_attempt = int(n * (1 / p) * 1.2)  # factor of 1.2 for safety

  # If sampling is performed with replacement, candidates are appended.
  # Otherwise, they should be added with a set union to remove duplicates.
  if replacement:
    negatives = []
  else:
    negatives = set()

  while len(negatives) < n:
    negative_candidates = np.random.randint(
        low=0, high=num_items, size=(n_attempt,))
    if replacement:
      negatives.extend(
          [i for i in negative_candidates if i not in positive_set]
      )
    else:
      negatives |= (set(negative_candidates) - positive_set)

  if not replacement:
    negatives = list(negatives)
    np.random.shuffle(negatives)  # list(set(...)) is not order guaranteed, but
                                  # in practice tends to be quite ordered.

  return negatives[:n]


def _train_eval_map_fn(shard, shard_id, cache_dir, num_items):
  # type: (typing.Dict(np.ndarray), int, str, int) -> typing.Dict(np.ndarray)
  """Split training and testing data and generate testing negatives.

  This function is called as part of a multiprocessing map. The principle
  input is a shard, which contains a sorted array of users and corresponding
  items for each user, where items have already been sorted in ascending order
  by timestamp. (Timestamp is not passed to avoid the serialization cost of
  sending it to the map function.)

  For each user, all but the last item is written into a pickle file which the
  training data producer can consume on as needed. The last item for a user
  is a validation point; for each validation point a number of negatives are
  generated (typically 999). The validation data is returned by this function,
  as it is held in memory for the remainder of the run.

  Args:
    shard: A dict containing the user and item arrays.
    shard_id: The id of the shard provided. This is used to number the training
      shard pickle files.
    cache_dir: The directory where training shard files should be written.
    num_items: The cardinality of the item set, which determines the set from
      which validation negatives should be drawn.

  Returns:
    A dict containing the evaluation data for a given shard.
  """

  users = shard[movielens.USER_COLUMN]
  items = shard[movielens.ITEM_COLUMN]

  # This produces index boundaries which can be used to slice by user.
  delta = users[1:] - users[:-1]
  boundaries = ([0] + (np.argwhere(delta)[:, 0] + 1).tolist() +
                [users.shape[0]])

  train_blocks = []
  test_blocks = []
  test_positives = []
  for i in range(len(boundaries) - 1):
    # This is simply a vector of repeated values such that the shard could be
    # represented compactly with a tuple of tuples:
    #   ((user_id, items), (user_id, items), ...)
    # rather than:
    #   user_id_vector, item_id_vector
    # However the additional nested structure significantly increases the
    # serialization and deserialization cost such that it is not worthwhile.
    block_user = users[boundaries[i]:boundaries[i+1]]
    assert len(set(block_user)) == 1

    block_items = items[boundaries[i]:boundaries[i+1]]
    train_blocks.append((block_user[:-1], block_items[:-1]))

    test_negatives = sample_with_exclusion(
        num_items=num_items, positive_set=set(block_items), n=_NUMBER_NEGATIVES,
        replacement=False)
    test_blocks.append((
        block_user[0] * np.ones((_NUMBER_NEGATIVES + 1,), dtype=np.int32),
        np.array([block_items[-1]] + test_negatives, dtype=np.uint16)
    ))
    test_positives.append((block_user[0], block_items[-1]))

  train_users = np.concatenate([i[0] for i in train_blocks])
  train_items = np.concatenate([i[1] for i in train_blocks])

  train_shard_fname = "train_positive_shard_{}.pickle".format(
      str(shard_id).zfill(5))
  train_shard_fpath = os.path.join(
      cache_dir, _TRAIN_SHARD_SUBDIR, train_shard_fname)

  with tf.gfile.Open(train_shard_fpath, "wb") as f:
    pickle.dump({
        movielens.USER_COLUMN: train_users,
        movielens.ITEM_COLUMN: train_items,
    }, f)

  test_users = np.concatenate([i[0] for i in test_blocks])
  test_items = np.concatenate([i[1] for i in test_blocks])
  assert test_users.shape == test_items.shape
  assert test_items.shape[0] % (_NUMBER_NEGATIVES + 1) == 0

  return {
      movielens.USER_COLUMN: test_users,
      movielens.ITEM_COLUMN: test_items,
  }


def generate_train_eval_data(df, approx_num_shards, cache_dir, num_items):
  # type: (pd.DataFrame, int, str, int) -> (typing.Dict[np.ndarray], np.ndarray)
  """Construct training and evaluation datasets.

  This function manages dataset construction and validation that the
  transformations have produced correct results. The particular logic of
  transforming the data is performed in _train_eval_map_fn().

  Args:
    df: The dataframe containing the entire dataset. It is essential that this
      dataframe be produced by _filter_index_sort(), as subsequent
      transformations rely on `df` having particular structure.
    approx_num_shards: The approximate number of similarly sized shards to
      construct from `df`. The MovieLens has severe imbalances where some users
      have interacted with many items; this is common among datasets involving
      user data. Rather than attempt to aggressively balance shard size, this
      function simply allows shards to "overflow" which can produce a number of
      shards which is less than `approx_num_shards`. This small degree of
      imbalance does not impact performance; however it does mean that one
      should not expect approx_num_shards to be the ACTUAL number of shards.
    cache_dir: The root directory for artifacts. Training shards are written
      to a subdir of cache_dir.
    num_items: The cardinality of the item set.

  Returns:
    A tuple containing the validation data.
  """

  num_rows = len(df)
  approximate_partitions = np.linspace(
      0, num_rows, approx_num_shards + 1).astype("int")
  start_ind, end_ind = 0, 0
  shards = []

  for i in range(1, approx_num_shards + 1):
    end_ind = approximate_partitions[i]
    while (end_ind < num_rows and df[movielens.USER_COLUMN][end_ind - 1] ==
           df[movielens.USER_COLUMN][end_ind]):
      end_ind += 1

    if end_ind <= start_ind:
      continue  # imbalance from prior shard.

    df_shard = df[start_ind:end_ind]
    user_shard = df_shard[movielens.USER_COLUMN].values.astype(np.int32)
    item_shard = df_shard[movielens.ITEM_COLUMN].values.astype(np.uint16)

    shards.append({
        movielens.USER_COLUMN: user_shard,
        movielens.ITEM_COLUMN: item_shard,
    })

    start_ind = end_ind
  assert end_ind == num_rows
  approx_num_shards = len(shards)

  tf.logging.info("Splitting train and test data and generating {} test "
                  "negatives per user...".format(_NUMBER_NEGATIVES))
  tf.gfile.MakeDirs(os.path.join(cache_dir, _TRAIN_SHARD_SUBDIR))
  map_args = [(shards[i], i, cache_dir, num_items)
              for i in range(approx_num_shards)]
  ctx = multiprocessing.get_context("spawn")
  with contextlib.closing(ctx.Pool(multiprocessing.cpu_count())) as pool:
    test_shards = pool.starmap(_train_eval_map_fn, map_args)

  tf.logging.info("Merging test shards...")
  test_users = np.concatenate([i[movielens.USER_COLUMN] for i in test_shards])
  test_items = np.concatenate([i[movielens.ITEM_COLUMN] for i in test_shards])

  assert test_users.shape == test_items.shape
  assert test_items.shape[0] % (_NUMBER_NEGATIVES + 1) == 0

  test_labels = np.zeros(shape=test_users.shape)
  test_labels[0::(_NUMBER_NEGATIVES + 1)] = 1

  return ({
      movielens.USER_COLUMN: test_users,
      movielens.ITEM_COLUMN: test_items,
  }, test_labels)


def construct_cache(dataset, data_dir, num_data_readers, num_neg, debug):
  # type: (str, str, int, int, bool) -> NCFDataset
  """Load and digest data CSV into a usable form.

  Args:
    dataset: The name of the dataset to be used.
    data_dir: The root directory of the dataset.
    num_data_readers: The number of parallel processes which will request
      data during training.
    num_neg: The number of negative examples per positive example to generate
      during training.
    debug: Whether this function is being called in a debug context. This will
      cause it to store the training data in memory, which is unnecessary for
      training but can be used to test the data pipeline.
  """
  pts_per_epoch = movielens.NUM_RATINGS[dataset] * (1 + num_neg)
  num_data_readers = num_data_readers or int(multiprocessing.cpu_count() / 2)
  approx_num_shards = int(pts_per_epoch // _APPROX_PTS_PER_SHARD) or 1

  st = timeit.default_timer()
  cache_dir = os.path.join(data_dir, _CACHE_SUBDIR, dataset)
  if tf.gfile.Exists(cache_dir):
    tf.gfile.DeleteRecursively(cache_dir)
  tf.gfile.MakeDirs(cache_dir)

  raw_rating_path = os.path.join(data_dir, dataset, movielens.RATINGS_FILE)
  df, num_users, num_items = _filter_index_sort(raw_rating_path)

  test_data = generate_train_eval_data(
      df=df, approx_num_shards=approx_num_shards, cache_dir=cache_dir,
      num_items=num_items)
  del approx_num_shards  # value may have changed.

  train_data = None
  num_train_neg = None
  if debug:
    users = df[movielens.USER_COLUMN].values
    items = df[movielens.ITEM_COLUMN].values
    train_ind = np.argwhere(np.equal(users[:-1], users[1:]))[:, 0]
    train_data = {
        movielens.USER_COLUMN: users[train_ind],
        movielens.ITEM_COLUMN: items[train_ind],
    }
    num_train_neg = num_neg

  ncf_dataset = NCFDataset(cache_dir=cache_dir, test_data=test_data,
                           num_items=num_items, num_users=num_users,
                           num_data_readers=num_data_readers,
                           train_data=train_data, num_train_neg=num_train_neg)
  run_time = timeit.default_timer() - st
  tf.logging.info("Cache construction complete. Time: {:.1f} sec."
                  .format(run_time))
  return ncf_dataset


def run(dataset, data_dir, num_data_readers=None, num_neg=4, debug=False):
  movielens.download(dataset=dataset, data_dir=data_dir)
  return construct_cache(dataset=dataset, data_dir=data_dir,
                         num_data_readers=num_data_readers, num_neg=num_neg,
                         debug=debug)
