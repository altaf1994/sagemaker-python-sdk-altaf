# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Placeholder docstring"""
from __future__ import absolute_import

from typing import Union, Optional, List, Dict
from botocore import exceptions

from sagemaker.job import _Job
from sagemaker.session import Session
from sagemaker.inputs import BatchDataCaptureConfig
from sagemaker.workflow.entities import PipelineVariable
from sagemaker.workflow.pipeline_context import runnable_by_pipeline
from sagemaker.workflow import is_pipeline_variable
from sagemaker.utils import base_name_from_image, name_from_base


class Transformer(object):
    """A class for handling creating and interacting with Amazon SageMaker transform jobs."""

    JOB_CLASS_NAME = "transform-job"

    def __init__(
        self,
        model_name: Union[str, PipelineVariable],
        instance_count: Union[int, PipelineVariable],
        instance_type: Union[str, PipelineVariable],
        strategy: Optional[Union[str, PipelineVariable]] = None,
        assemble_with: Optional[Union[str, PipelineVariable]] = None,
        output_path: Optional[Union[str, PipelineVariable]] = None,
        output_kms_key: Optional[Union[str, PipelineVariable]] = None,
        accept: Optional[Union[str, PipelineVariable]] = None,
        max_concurrent_transforms: Optional[Union[int, PipelineVariable]] = None,
        max_payload: Optional[Union[int, PipelineVariable]] = None,
        tags: Optional[List[Dict[str, Union[str, PipelineVariable]]]] = None,
        env: Optional[Dict[str, Union[str, PipelineVariable]]] = None,
        base_transform_job_name: Optional[str] = None,
        sagemaker_session: Optional[Session] = None,
        volume_kms_key: Optional[Union[str, PipelineVariable]] = None,
    ):
        """Initialize a ``Transformer``.

        Args:
            model_name (str or PipelineVariable): Name of the SageMaker model being
                used for the transform job.
            instance_count (int or PipelineVariable): Number of EC2 instances to use.
            instance_type (str or PipelineVariable): Type of EC2 instance to use, for example,
                'ml.c4.xlarge'.
            strategy (str or PipelineVariable): The strategy used to decide how to batch records
                in a single request (default: None). Valid values: 'MultiRecord'
                and 'SingleRecord'.
            assemble_with (str or PipelineVariable): How the output is assembled (default: None).
                Valid values: 'Line' or 'None'.
            output_path (str or PipelineVariable): S3 location for saving the transform result. If
                not specified, results are stored to a default bucket.
            output_kms_key (str or PipelineVariable): Optional. KMS key ID for encrypting the
                transform output (default: None).
            accept (str or PipelineVariable): The accept header passed by the client to
                the inference endpoint. If it is supported by the endpoint,
                it will be the format of the batch transform output.
            max_concurrent_transforms (int or PipelineVariable): The maximum number of HTTP requests
                to be made to each individual transform container at one time.
            max_payload (int or PipelineVariable): Maximum size of the payload in a single HTTP
                request to the container in MB.
            tags (list[dict[str, str] or list[dict[str, PipelineVariable]]): List of tags for
                labeling a transform job (default: None). For more, see the SageMaker API
                documentation for `Tag <https://docs.aws.amazon.com/sagemaker/latest/dg/API_Tag.html>`_.
            env (dict[str, str] or dict[str, PipelineVariable]): Environment variables to be set
                for use during the transform job (default: None).
            base_transform_job_name (str): Prefix for the transform job when the
                :meth:`~sagemaker.transformer.Transformer.transform` method
                launches. If not specified, a default prefix will be generated
                based on the training image name that was used to train the
                model associated with the transform job.
            sagemaker_session (sagemaker.session.Session): Session object which
                manages interactions with Amazon SageMaker APIs and any other
                AWS services needed. If not specified, the estimator creates one
                using the default AWS configuration chain.
            volume_kms_key (str or PipelineVariable): Optional. KMS key ID for encrypting
                the volume attached to the ML compute instance (default: None).
        """
        self.model_name = model_name
        self.strategy = strategy
        self.env = env

        self.output_path = output_path
        self.output_kms_key = output_kms_key
        self.accept = accept
        self.assemble_with = assemble_with

        self.instance_count = instance_count
        self.instance_type = instance_type
        self.volume_kms_key = volume_kms_key

        self.max_concurrent_transforms = max_concurrent_transforms
        self.max_payload = max_payload
        self.tags = tags

        self.base_transform_job_name = base_transform_job_name
        self._current_job_name = None
        self.latest_transform_job = None
        self._reset_output_path = False

        self.sagemaker_session = sagemaker_session or Session()

    @runnable_by_pipeline
    def transform(
        self,
        data: Union[str, PipelineVariable],
        data_type: Union[str, PipelineVariable] = "S3Prefix",
        content_type: Optional[Union[str, PipelineVariable]] = None,
        compression_type: Optional[Union[str, PipelineVariable]] = None,
        split_type: Optional[Union[str, PipelineVariable]] = None,
        job_name: Optional[str] = None,
        input_filter: Optional[Union[str, PipelineVariable]] = None,
        output_filter: Optional[Union[str, PipelineVariable]] = None,
        join_source: Optional[Union[str, PipelineVariable]] = None,
        experiment_config: Optional[Dict[str, str]] = None,
        model_client_config: Optional[Dict[str, Union[str, PipelineVariable]]] = None,
        batch_data_capture_config: BatchDataCaptureConfig = None,
        wait: bool = True,
        logs: bool = True,
    ):
        """Start a new transform job.

        Args:
            data (str or PipelineVariable): Input data location in S3.
            data_type (str or PipelineVariable): What the S3 location defines (default: 'S3Prefix').
                Valid values:

                * 'S3Prefix' - the S3 URI defines a key name prefix. All objects with this prefix
                    will be used as inputs for the transform job.

                * 'ManifestFile' - the S3 URI points to a single manifest file listing each S3
                    object to use as an input for the transform job.

            content_type (str or PipelineVariable): MIME type of the input data (default: None).
            compression_type (str or PipelineVariable): Compression type of the input data, if
                compressed (default: None). Valid values: 'Gzip', None.
            split_type (str or PipelineVariable): The record delimiter for the input object
                (default: 'None'). Valid values: 'None', 'Line', 'RecordIO', and
                'TFRecord'.
            job_name (str): job name (default: None). If not specified, one will
                be generated.
            input_filter (str or PipelineVariable): A JSONPath to select a portion of the input to
                pass to the algorithm container for inference. If you omit the
                field, it gets the value '$', representing the entire input.
                For CSV data, each row is taken as a JSON array,
                so only index-based JSONPaths can be applied, e.g. $[0], $[1:].
                CSV data should follow the `RFC format <https://tools.ietf.org/html/rfc4180>`_.
                See `Supported JSONPath Operators
                <https://docs.aws.amazon.com/sagemaker/latest/dg/batch-transform-data-processing.html#data-processing-operators>`_
                for a table of supported JSONPath operators.
                For more information, see the SageMaker API documentation for
                `CreateTransformJob
                <https://docs.aws.amazon.com/sagemaker/latest/dg/API_CreateTransformJob.html>`_.
                Some examples: "$[1:]", "$.features" (default: None).
            output_filter (str or PipelineVariable): A JSONPath to select a portion of the
                joined/original output to return as the output.
                For more information, see the SageMaker API documentation for
                `CreateTransformJob
                <https://docs.aws.amazon.com/sagemaker/latest/dg/API_CreateTransformJob.html>`_.
                Some examples: "$[1:]", "$.prediction" (default: None).
            join_source (str or PipelineVariable): The source of data to be joined to the transform
                output. It can be set to 'Input' meaning the entire input record
                will be joined to the inference result. You can use OutputFilter
                to select the useful portion before uploading to S3. (default:
                None). Valid values: Input, None.
            experiment_config (dict[str, str]): Experiment management configuration.
                Optionally, the dict can contain three keys:
                'ExperimentName', 'TrialName', and 'TrialComponentDisplayName'.
                The behavior of setting these keys is as follows:
                * If `ExperimentName` is supplied but `TrialName` is not a Trial will be
                automatically created and the job's Trial Component associated with the Trial.
                * If `TrialName` is supplied and the Trial already exists the job's Trial Component
                will be associated with the Trial.
                * If both `ExperimentName` and `TrialName` are not supplied the trial component
                will be unassociated.
                * `TrialComponentDisplayName` is used for display in Studio.
                * Both `ExperimentName` and `TrialName` will be ignored if the Transformer instance
                is built with :class:`~sagemaker.workflow.pipeline_context.PipelineSession`.
                However, the value of `TrialComponentDisplayName` is honored for display in Studio.
            model_client_config (dict[str, str] or dict[str, PipelineVariable]): Model
                configuration. Dictionary contains two optional keys,
                'InvocationsTimeoutInSeconds', and 'InvocationsMaxRetries'.
                (default: ``None``).
            batch_data_capture_config (BatchDataCaptureConfig): Configuration object which
                specifies the configurations related to the batch data capture for the transform job
                (default: ``None``).
            wait (bool): Whether the call should wait until the job completes
                (default: ``True``).
            logs (bool): Whether to show the logs produced by the job.
                Only meaningful when wait is ``True`` (default: ``True``).
        Returns:
            None or pipeline step arguments in case the Transformer instance is built with
            :class:`~sagemaker.workflow.pipeline_context.PipelineSession`
        """
        local_mode = self.sagemaker_session.local_mode
        if not local_mode and not is_pipeline_variable(data) and not data.startswith("s3://"):
            raise ValueError("Invalid S3 URI: {}".format(data))

        if job_name is not None:
            self._current_job_name = job_name
        else:
            base_name = self.base_transform_job_name

            if base_name is None:
                base_name = (
                    "transform-job"
                    if is_pipeline_variable(self.model_name)
                    else self._retrieve_base_name()
                )

            self._current_job_name = name_from_base(base_name)

        if self.output_path is None or self._reset_output_path is True:
            self.output_path = "s3://{}/{}".format(
                self.sagemaker_session.default_bucket(), self._current_job_name
            )
            self._reset_output_path = True

        self.latest_transform_job = _TransformJob.start_new(
            self,
            data,
            data_type,
            content_type,
            compression_type,
            split_type,
            input_filter,
            output_filter,
            join_source,
            experiment_config,
            model_client_config,
            batch_data_capture_config,
        )

        if wait:
            self.latest_transform_job.wait(logs=logs)

    def delete_model(self):
        """Delete the corresponding SageMaker model for this Transformer."""
        self.sagemaker_session.delete_model(self.model_name)

    def _retrieve_base_name(self):
        """Placeholder docstring"""
        image_uri = self._retrieve_image_uri()

        if image_uri:
            return base_name_from_image(image_uri, default_base_name=Transformer.JOB_CLASS_NAME)

        return self.model_name

    def _retrieve_image_uri(self):
        """Placeholder docstring"""
        try:
            model_desc = self.sagemaker_session.sagemaker_client.describe_model(
                ModelName=self.model_name
            )

            primary_container = model_desc.get("PrimaryContainer")
            if primary_container:
                return primary_container.get("Image")

            containers = model_desc.get("Containers")
            if containers:
                return containers[0].get("Image")

            return None

        except exceptions.ClientError:
            raise ValueError(
                "Failed to fetch model information for %s. "
                "Please ensure that the model exists. "
                "Local instance types require locally created models." % self.model_name
            )

    def wait(self, logs=True):
        """Placeholder docstring"""
        self._ensure_last_transform_job()
        self.latest_transform_job.wait(logs=logs)

    def stop_transform_job(self, wait=True):
        """Stop latest running batch transform job."""
        self._ensure_last_transform_job()
        self.latest_transform_job.stop()
        if wait:
            self.latest_transform_job.wait()

    def _ensure_last_transform_job(self):
        """Placeholder docstring"""
        if self.latest_transform_job is None:
            raise ValueError("No transform job available")

    @classmethod
    def attach(cls, transform_job_name, sagemaker_session=None):
        """Attach an existing transform job to a new Transformer instance

        Args:
            transform_job_name (str): Name for the transform job to be attached.
            sagemaker_session (sagemaker.session.Session): Session object which
                manages interactions with Amazon SageMaker APIs and any other
                AWS services needed. If not specified, one will be created using
                the default AWS configuration chain.

        Returns:
            sagemaker.transformer.Transformer: The Transformer instance with the
            specified transform job attached.
        """
        sagemaker_session = sagemaker_session or Session()

        job_details = sagemaker_session.sagemaker_client.describe_transform_job(
            TransformJobName=transform_job_name
        )
        init_params = cls._prepare_init_params_from_job_description(job_details)
        transformer = cls(sagemaker_session=sagemaker_session, **init_params)
        transformer.latest_transform_job = _TransformJob(
            sagemaker_session=sagemaker_session, job_name=init_params["base_transform_job_name"]
        )

        return transformer

    @classmethod
    def _prepare_init_params_from_job_description(cls, job_details):
        """Convert the transform job description to init params.

        It can be handled by the class constructor.

        Args:
            job_details (dict): the returned job details from a
                describe_transform_job API call.

        Returns:
            dict: The transformed init_params
        """
        init_params = dict()

        init_params["model_name"] = job_details["ModelName"]
        init_params["instance_count"] = job_details["TransformResources"]["InstanceCount"]
        init_params["instance_type"] = job_details["TransformResources"]["InstanceType"]
        init_params["volume_kms_key"] = job_details["TransformResources"].get("VolumeKmsKeyId")
        init_params["strategy"] = job_details.get("BatchStrategy")
        init_params["assemble_with"] = job_details["TransformOutput"].get("AssembleWith")
        init_params["output_path"] = job_details["TransformOutput"]["S3OutputPath"]
        init_params["output_kms_key"] = job_details["TransformOutput"].get("KmsKeyId")
        init_params["accept"] = job_details["TransformOutput"].get("Accept")
        init_params["max_concurrent_transforms"] = job_details.get("MaxConcurrentTransforms")
        init_params["max_payload"] = job_details.get("MaxPayloadInMB")
        init_params["base_transform_job_name"] = job_details["TransformJobName"]

        return init_params


class _TransformJob(_Job):
    """Placeholder docstring"""

    @classmethod
    def start_new(
        cls,
        transformer,
        data,
        data_type,
        content_type,
        compression_type,
        split_type,
        input_filter,
        output_filter,
        join_source,
        experiment_config,
        model_client_config,
        batch_data_capture_config,
    ):
        """Placeholder docstring"""

        transform_args = cls._get_transform_args(
            transformer,
            data,
            data_type,
            content_type,
            compression_type,
            split_type,
            input_filter,
            output_filter,
            join_source,
            experiment_config,
            model_client_config,
            batch_data_capture_config,
        )

        transformer.sagemaker_session.transform(**transform_args)

        return cls(transformer.sagemaker_session, transformer._current_job_name)

    @classmethod
    def _get_transform_args(
        cls,
        transformer,
        data,
        data_type,
        content_type,
        compression_type,
        split_type,
        input_filter,
        output_filter,
        join_source,
        experiment_config,
        model_client_config,
        batch_data_capture_config,
    ):
        """Placeholder docstring"""

        config = _TransformJob._load_config(
            data, data_type, content_type, compression_type, split_type, transformer
        )
        data_processing = _TransformJob._prepare_data_processing(
            input_filter, output_filter, join_source
        )

        transform_args = config.copy()
        transform_args.update(
            {
                "job_name": transformer._current_job_name,
                "model_name": transformer.model_name,
                "strategy": transformer.strategy,
                "max_concurrent_transforms": transformer.max_concurrent_transforms,
                "max_payload": transformer.max_payload,
                "env": transformer.env,
                "experiment_config": experiment_config,
                "model_client_config": model_client_config,
                "tags": transformer.tags,
                "data_processing": data_processing,
                "batch_data_capture_config": batch_data_capture_config,
            }
        )

        return transform_args

    def wait(self, logs=True):
        if logs:
            self.sagemaker_session.logs_for_transform_job(self.job_name, wait=True)
        else:
            self.sagemaker_session.wait_for_transform_job(self.job_name)

    def stop(self):
        """Placeholder docstring"""
        self.sagemaker_session.stop_transform_job(name=self.job_name)

    @staticmethod
    def _load_config(data, data_type, content_type, compression_type, split_type, transformer):
        """Placeholder docstring"""
        input_config = _TransformJob._format_inputs_to_input_config(
            data, data_type, content_type, compression_type, split_type
        )

        output_config = _TransformJob._prepare_output_config(
            transformer.output_path,
            transformer.output_kms_key,
            transformer.assemble_with,
            transformer.accept,
        )

        resource_config = _TransformJob._prepare_resource_config(
            transformer.instance_count, transformer.instance_type, transformer.volume_kms_key
        )

        return {
            "input_config": input_config,
            "output_config": output_config,
            "resource_config": resource_config,
        }

    @staticmethod
    def _format_inputs_to_input_config(data, data_type, content_type, compression_type, split_type):
        """Placeholder docstring"""
        config = {"DataSource": {"S3DataSource": {"S3DataType": data_type, "S3Uri": data}}}

        if content_type is not None:
            config["ContentType"] = content_type

        if compression_type is not None:
            config["CompressionType"] = compression_type

        if split_type is not None:
            config["SplitType"] = split_type

        return config

    @staticmethod
    def _prepare_output_config(s3_path, kms_key_id, assemble_with, accept):
        """Placeholder docstring"""
        config = super(_TransformJob, _TransformJob)._prepare_output_config(s3_path, kms_key_id)

        if assemble_with is not None:
            config["AssembleWith"] = assemble_with

        if accept is not None:
            config["Accept"] = accept

        return config

    @staticmethod
    def _prepare_resource_config(instance_count, instance_type, volume_kms_key):
        """Placeholder docstring"""
        config = {"InstanceCount": instance_count, "InstanceType": instance_type}

        if volume_kms_key is not None:
            config["VolumeKmsKeyId"] = volume_kms_key

        return config

    @staticmethod
    def _prepare_data_processing(input_filter, output_filter, join_source):
        """Placeholder docstring"""
        config = {}

        if input_filter is not None:
            config["InputFilter"] = input_filter

        if output_filter is not None:
            config["OutputFilter"] = output_filter

        if join_source is not None:
            config["JoinSource"] = join_source

        if len(config) == 0:
            return None

        return config
