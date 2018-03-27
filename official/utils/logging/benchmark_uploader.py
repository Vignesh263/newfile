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

"""Library to upload benchmark generated by BenchmarkLogger to remote repo.

This library require google cloud bigquery lib as dependency, which can be
installed with:
  > pip install --upgrade google-cloud-bigquery
"""

import argparse
import json
import os
import sys
import uuid

from google.cloud import bigquery

import tensorflow as tf # pylint: disable=g-bad-import-order

from official.utils.logging import logger


FLAGS = None


class BigQueryUploader(object):
  """Upload the benchmark and metric info to BigQuery."""

  def __init__(self, logging_dir, gcp_project=None, credentials=None):
    """Initialized BigQueryUploader with proper setting.

    Args:
      logging_dir: string, logging directory that contains the benchmark log.
      gcp_project: string, the name of the GCP project that the log will be
        uploaded to. The default project name will be detected from local
        environment if no value is provide.
      credentials: google.auth.credentials. The credential to access the
        BigQuery service. The default service account credential will be
        detected from local environment if no value is provided. Please use
        google.oauth2.service_account.Credentials to load credential from local
        file for the case that the test is run out side of GCP.
    """
    self._logging_dir = logging_dir
    self._bq_client = bigquery.Client(
        project=gcp_project, credentials=credentials)

  def upload_benchmark_run(self, dataset_name, table_name, run_id):
    expected_file = os.path.join(
        self._logging_dir, logger.BENCHMARK_RUN_LOG_FILE_NAME)
    with tf.gfile.GFile(expected_file) as f:
      benchmark_json = json.load(f)
      benchmark_json["model_id"] = run_id
      table_ref = self._bq_client.dataset(dataset_name).table(table_name)
      errors = self._bq_client.insert_rows_json(table_ref, [benchmark_json])
      if errors:
        tf.logging.error(
            "Failed to upload benchmark info to bigquery: {}".format(errors))

  def upload_metric(self, dataset_name, table_name, run_id):
    expected_file = os.path.join(
        self._logging_dir, logger.METRIC_LOG_FILE_NAME)
    with tf.gfile.GFile(expected_file) as f:
      lines = f.readlines()
      metrics = []
      for l in lines:
        if not l.strip(): continue
        metric = json.loads(l)
        metric["run_id"] = run_id
        metrics.append(metric)
      table_ref = self._bq_client.dataset(dataset_name).table(table_name)
      errors = self._bq_client.insert_rows_json(table_ref, metrics)
      if errors:
        tf.logging.error(
            "Failed to upload benchmark info to bigquery: {}".format(errors))


def main(unused_argv):
  if not FLAGS.benchmark_log_dir:
    print("Usage: benchmark_uploader.py --benchmark_log_dir=/some/dir")
    sys.exit(1)

  uploader = BigQueryUploader(
      FLAGS.benchmark_log_dir,
      gcp_project=FLAGS.gcp_project)
  run_id = str(uuid.uuid4())
  uploader.upload_benchmark_run(
      FLAGS.bigquery_data_set, FLAGS.bigquery_run_table, run_id)
  uploader.upload_metric(
      FLAGS.bigquery_data_set, FLAGS.bigquery_metric_table, run_id)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--benchmark_log_dir", "-bld", default=None,
      help="[default: %(default)s] The location of the benchmark logging.",
      metavar="<BLD>"
  )
  parser.add_argument(
      "--gcp_project", "-gp", default=None,
      help="The GCP project name where the benchmark will be uploaded.",
      metavar="<GP>"
  )
  parser.add_argument(
      "--bigquery_data_set", "-bds", default="test_benchmark",
      help="The Bigquery dataset name where the benchmark will be uploaded.",
      metavar="<BDS>"
  )
  parser.add_argument(
      "--bigquery_run_table", "-brt", default="benchmark_run",
      help="The Bigquery table name where the benchmark run information will be"
           " uploaded.",
      metavar="<BRT>"
  )
  parser.add_argument(
      "--bigquery_metric_table", "-bmt", default="benchmark_metric",
      help="The Bigquery table name where the benchmark metric information will"
           " be uploaded.",
      metavar="<BMT>"
  )
  FLAGS, unparsed = parser.parse_known_args()
  main(unused_argv=[sys.argv[0]] + unparsed)
