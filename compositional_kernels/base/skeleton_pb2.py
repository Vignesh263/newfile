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

# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: skeleton.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='skeleton.proto',
  package='',
  syntax='proto2',
  serialized_pb=_b('\n\x0eskeleton.proto\"D\n\x08Skeleton\x12\x1a\n\x05input\x18\x01 \x01(\x0b\x32\x0b.InputLayer\x12\x1c\n\x06hidden\x18\x02 \x03(\x0b\x32\x0c.HiddenLayer\"9\n\nInputLayer\x12\x16\n\x0e\x64imension_size\x18\x01 \x03(\x05\x12\x13\n\x08\x63hannels\x18\x02 \x01(\x05:\x01\x31\"\xec\x01\n\x0bHiddenLayer\x12\x1b\n\x03\x64im\x18\x01 \x03(\x0b\x32\x0e.DimensionSpec\x12$\n\x07padding\x18\x02 \x01(\x0e\x32\x0c.PaddingType:\x05VALID\x12,\n\x08operator\x18\x03 \x01(\x0e\x32\r.OperatorType:\x0b\x43ONVOLUTION\x12\x13\n\x0breplication\x18\x04 \x01(\x05\x12)\n\nactivation\x18\x05 \x01(\x0e\x32\x0f.ActivationType:\x04RELU\x12,\n\x11\x61\x63tivation_params\x18\x06 \x01(\x0b\x32\x11.ActivationParams\"Q\n\rDimensionSpec\x12\r\n\x05width\x18\x01 \x01(\x05\x12\x11\n\x06stride\x18\x02 \x01(\x05:\x01\x31\x12\x1e\n\x0f\x66ully_connected\x18\x03 \x01(\x08:\x05\x66\x61lse\"7\n\x10\x41\x63tivationParams\x12\x14\n\x0c\x63oefficients\x18\x01 \x03(\x01\x12\r\n\x05scale\x18\x02 \x01(\x01*?\n\x0cOperatorType\x12\x0f\n\x0b\x43ONVOLUTION\x10\x00\x12\x0c\n\x08MAX_POOL\x10\x01\x12\x10\n\x0c\x41VERAGE_POOL\x10\x02*_\n\x0e\x41\x63tivationType\x12\x08\n\x04RELU\x10\x00\x12\x0c\n\x08IDENTITY\x10\x01\x12\x0f\n\x0b\x45XPONENTIAL\x10\x02\x12\x0e\n\nPOLYNOMIAL\x10\x03\x12\x08\n\x04SINE\x10\x04\x12\n\n\x06\x43OSINE\x10\x05*\"\n\x0bPaddingType\x12\t\n\x05VALID\x10\x00\x12\x08\n\x04SAME\x10\x01')
)

_OPERATORTYPE = _descriptor.EnumDescriptor(
  name='OperatorType',
  full_name='OperatorType',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='CONVOLUTION', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MAX_POOL', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='AVERAGE_POOL', index=2, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=526,
  serialized_end=589,
)
_sym_db.RegisterEnumDescriptor(_OPERATORTYPE)

OperatorType = enum_type_wrapper.EnumTypeWrapper(_OPERATORTYPE)
_ACTIVATIONTYPE = _descriptor.EnumDescriptor(
  name='ActivationType',
  full_name='ActivationType',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='RELU', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='IDENTITY', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='EXPONENTIAL', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='POLYNOMIAL', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SINE', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='COSINE', index=5, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=591,
  serialized_end=686,
)
_sym_db.RegisterEnumDescriptor(_ACTIVATIONTYPE)

ActivationType = enum_type_wrapper.EnumTypeWrapper(_ACTIVATIONTYPE)
_PADDINGTYPE = _descriptor.EnumDescriptor(
  name='PaddingType',
  full_name='PaddingType',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='VALID', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SAME', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=688,
  serialized_end=722,
)
_sym_db.RegisterEnumDescriptor(_PADDINGTYPE)

PaddingType = enum_type_wrapper.EnumTypeWrapper(_PADDINGTYPE)
CONVOLUTION = 0
MAX_POOL = 1
AVERAGE_POOL = 2
RELU = 0
IDENTITY = 1
EXPONENTIAL = 2
POLYNOMIAL = 3
SINE = 4
COSINE = 5
VALID = 0
SAME = 1



_SKELETON = _descriptor.Descriptor(
  name='Skeleton',
  full_name='Skeleton',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='input', full_name='Skeleton.input', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hidden', full_name='Skeleton.hidden', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=18,
  serialized_end=86,
)


_INPUTLAYER = _descriptor.Descriptor(
  name='InputLayer',
  full_name='InputLayer',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='dimension_size', full_name='InputLayer.dimension_size', index=0,
      number=1, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='channels', full_name='InputLayer.channels', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=88,
  serialized_end=145,
)


_HIDDENLAYER = _descriptor.Descriptor(
  name='HiddenLayer',
  full_name='HiddenLayer',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='dim', full_name='HiddenLayer.dim', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='padding', full_name='HiddenLayer.padding', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='operator', full_name='HiddenLayer.operator', index=2,
      number=3, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='replication', full_name='HiddenLayer.replication', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='activation', full_name='HiddenLayer.activation', index=4,
      number=5, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='activation_params', full_name='HiddenLayer.activation_params', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=148,
  serialized_end=384,
)


_DIMENSIONSPEC = _descriptor.Descriptor(
  name='DimensionSpec',
  full_name='DimensionSpec',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='width', full_name='DimensionSpec.width', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='stride', full_name='DimensionSpec.stride', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fully_connected', full_name='DimensionSpec.fully_connected', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=386,
  serialized_end=467,
)


_ACTIVATIONPARAMS = _descriptor.Descriptor(
  name='ActivationParams',
  full_name='ActivationParams',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='coefficients', full_name='ActivationParams.coefficients', index=0,
      number=1, type=1, cpp_type=5, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='scale', full_name='ActivationParams.scale', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=469,
  serialized_end=524,
)

_SKELETON.fields_by_name['input'].message_type = _INPUTLAYER
_SKELETON.fields_by_name['hidden'].message_type = _HIDDENLAYER
_HIDDENLAYER.fields_by_name['dim'].message_type = _DIMENSIONSPEC
_HIDDENLAYER.fields_by_name['padding'].enum_type = _PADDINGTYPE
_HIDDENLAYER.fields_by_name['operator'].enum_type = _OPERATORTYPE
_HIDDENLAYER.fields_by_name['activation'].enum_type = _ACTIVATIONTYPE
_HIDDENLAYER.fields_by_name['activation_params'].message_type = _ACTIVATIONPARAMS
DESCRIPTOR.message_types_by_name['Skeleton'] = _SKELETON
DESCRIPTOR.message_types_by_name['InputLayer'] = _INPUTLAYER
DESCRIPTOR.message_types_by_name['HiddenLayer'] = _HIDDENLAYER
DESCRIPTOR.message_types_by_name['DimensionSpec'] = _DIMENSIONSPEC
DESCRIPTOR.message_types_by_name['ActivationParams'] = _ACTIVATIONPARAMS
DESCRIPTOR.enum_types_by_name['OperatorType'] = _OPERATORTYPE
DESCRIPTOR.enum_types_by_name['ActivationType'] = _ACTIVATIONTYPE
DESCRIPTOR.enum_types_by_name['PaddingType'] = _PADDINGTYPE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Skeleton = _reflection.GeneratedProtocolMessageType('Skeleton', (_message.Message,), dict(
  DESCRIPTOR = _SKELETON,
  __module__ = 'skeleton_pb2'
  # @@protoc_insertion_point(class_scope:Skeleton)
  ))
_sym_db.RegisterMessage(Skeleton)

InputLayer = _reflection.GeneratedProtocolMessageType('InputLayer', (_message.Message,), dict(
  DESCRIPTOR = _INPUTLAYER,
  __module__ = 'skeleton_pb2'
  # @@protoc_insertion_point(class_scope:InputLayer)
  ))
_sym_db.RegisterMessage(InputLayer)

HiddenLayer = _reflection.GeneratedProtocolMessageType('HiddenLayer', (_message.Message,), dict(
  DESCRIPTOR = _HIDDENLAYER,
  __module__ = 'skeleton_pb2'
  # @@protoc_insertion_point(class_scope:HiddenLayer)
  ))
_sym_db.RegisterMessage(HiddenLayer)

DimensionSpec = _reflection.GeneratedProtocolMessageType('DimensionSpec', (_message.Message,), dict(
  DESCRIPTOR = _DIMENSIONSPEC,
  __module__ = 'skeleton_pb2'
  # @@protoc_insertion_point(class_scope:DimensionSpec)
  ))
_sym_db.RegisterMessage(DimensionSpec)

ActivationParams = _reflection.GeneratedProtocolMessageType('ActivationParams', (_message.Message,), dict(
  DESCRIPTOR = _ACTIVATIONPARAMS,
  __module__ = 'skeleton_pb2'
  # @@protoc_insertion_point(class_scope:ActivationParams)
  ))
_sym_db.RegisterMessage(ActivationParams)


# @@protoc_insertion_point(module_scope)
