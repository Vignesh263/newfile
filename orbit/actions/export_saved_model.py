# Copyright 2021 The Orbit Authors. All Rights Reserved.
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

"""Provides the `ExportSavedModel` action and associated helper classes."""

import re

from typing import Callable, Optional

import tensorflow as tf


def _id_key(filename):
  _, id_num = filename.rsplit('-', maxsplit=1)
  return int(id_num)


def _find_managed_files(base_name):
  r"""Returns all files matching '{base_name}-\d+', in sorted order."""
  managed_file_regex = re.compile(rf'{re.escape(base_name)}-\d+$')
  filenames = tf.io.gfile.glob(f'{base_name}-*')
  filenames = filter(managed_file_regex.match, filenames)
  return sorted(filenames, key=_id_key)


class _CounterIdFn:
  """Implements a counter-based ID function for `ExportFileManager`."""

  def __init__(self, base_name: str):
    managed_files = _find_managed_files(base_name)
    self.value = _id_key(managed_files[-1]) + 1 if managed_files else 0

  def __call__(self):
    output = self.value
    self.value += 1
    return output


class ExportFileManager:
  """Utility class that manages a group of files with a shared base name.

  For actions like SavedModel exporting, there are potentially many different
  file naming and cleanup strategies that may be desirable. This class provides
  a basic interface allowing SavedModel export to be decoupled from these
  details, and a default implementation that should work for many basic
  scenarios. Users may subclass this class to alter behavior and define more
  customized naming and cleanup strategies.
  """

  def __init__(self,
               base_name: str,
               max_to_keep: int = 5,
               next_id_fn: Optional[Callable[[], int]] = None):
    """Initializes the instance.

    Args:
      base_name: A shared base name for file names generated by this class.
      max_to_keep: The maximum number of files matching `base_name` to keep
        after each call to `cleanup`. The most recent (as determined by file
        modification time) `max_to_keep` files are preserved; the rest are
        deleted. If < 0, all files are preserved.
      next_id_fn: An optional callable that returns integer IDs to append to
        base name (formatted as `'{base_name}-{id}'`). The order of integers is
        used to sort files to determine the oldest ones deleted by `clean_up`.
        If not supplied, a default ID based on an incrementing counter is used.
        One common alternative maybe be to use the current global step count,
        for instance passing `next_id_fn=global_step.numpy`.
    """
    self._base_name = base_name
    self._max_to_keep = max_to_keep
    self._next_id_fn = next_id_fn or _CounterIdFn(base_name)

  @property
  def managed_files(self):
    """Returns all files managed by this instance, in sorted order.

    Returns:
      The list of files matching the `base_name` provided when constructing this
      `ExportFileManager` instance, sorted in increasing integer order of the
      IDs returned by `next_id_fn`.
    """
    return _find_managed_files(self._base_name)

  def clean_up(self):
    """Cleans up old files matching `{base_name}-*`.

    The most recent `max_to_keep` files are preserved.
    """
    if self._max_to_keep < 0:
      return

    for filename in self.managed_files[:-self._max_to_keep]:
      tf.io.gfile.rmtree(filename)

  def next_name(self) -> str:
    """Returns a new file name based on `base_name` and `next_id_fn()`."""
    return f'{self._base_name}-{self._next_id_fn()}'


class ExportSavedModel:
  """Action that exports the given model as a SavedModel."""

  def __init__(self,
               model: tf.Module,
               file_manager: ExportFileManager,
               signatures,
               options: Optional[tf.saved_model.SaveOptions] = None):
    """Initializes the instance.

    Args:
      model: The model to export.
      file_manager: An instance of `ExportFileManager` (or a subclass), that
        provides file naming and cleanup functionality.
      signatures: The signatures to forward to `tf.saved_model.save()`.
      options: Optional options to forward to `tf.saved_model.save()`.
    """
    self.model = model
    self.file_manager = file_manager
    self.signatures = signatures
    self.options = options

  def __call__(self, _):
    """Exports the SavedModel."""
    export_dir = self.file_manager.next_name()
    tf.saved_model.save(self.model, export_dir, self.signatures, self.options)
    self.file_manager.clean_up()
