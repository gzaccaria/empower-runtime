# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: control_delegation.proto

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
  name='control_delegation.proto',
  package='protocol',
  syntax='proto2',
  serialized_pb=_b('\n\x18\x63ontrol_delegation.proto\x12\x08protocol*<\n\x1bprp_control_delegation_type\x12\x1d\n\x19PRCDT_MAC_DL_UE_SCHEDULER\x10\x01')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

_PRP_CONTROL_DELEGATION_TYPE = _descriptor.EnumDescriptor(
  name='prp_control_delegation_type',
  full_name='protocol.prp_control_delegation_type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='PRCDT_MAC_DL_UE_SCHEDULER', index=0, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=38,
  serialized_end=98,
)
_sym_db.RegisterEnumDescriptor(_PRP_CONTROL_DELEGATION_TYPE)

prp_control_delegation_type = enum_type_wrapper.EnumTypeWrapper(_PRP_CONTROL_DELEGATION_TYPE)
PRCDT_MAC_DL_UE_SCHEDULER = 1


DESCRIPTOR.enum_types_by_name['prp_control_delegation_type'] = _PRP_CONTROL_DELEGATION_TYPE


# @@protoc_insertion_point(module_scope)
