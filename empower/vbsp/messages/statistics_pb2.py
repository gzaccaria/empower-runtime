# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: statistics.proto

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


import empower.vbsp.messages.configs_pb2 as configs__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='statistics.proto',
  package='',
  syntax='proto2',
  serialized_pb=_b('\n\x10statistics.proto\x1a\rconfigs.proto\"\x84\x01\n\x0crrc_meas_req\x12\x0c\n\x04rnti\x18\x01 \x02(\r\x12\x16\n\x03rat\x18\x02 \x02(\x0e\x32\t.rat_type\x12\x11\n\x06measId\x18\x03 \x02(\x05:\x01\x30\x12\x1b\n\x05m_obj\x18\x04 \x01(\x0b\x32\x0c.meas_object\x12\x1e\n\x06r_conf\x18\x05 \x01(\x0b\x32\x0e.report_config\")\n\rplmn_identity\x12\x0b\n\x03mnc\x18\x01 \x01(\r\x12\x0b\n\x03mcc\x18\x02 \x01(\r\"H\n\x14\x63\x65ll_global_id_EUTRA\x12\x1f\n\x07plmn_id\x18\x01 \x01(\x0b\x32\x0e.plmn_identity\x12\x0f\n\x07\x63\x65ll_id\x18\x02 \x01(\r\"y\n\x16\x45UTRA_cgi_measurements\x12\"\n\x03\x63gi\x18\x01 \x01(\x0b\x32\x15.cell_global_id_EUTRA\x12\x1a\n\x12tracking_area_code\x18\x02 \x01(\r\x12\x1f\n\x07plmn_id\x18\x03 \x03(\x0b\x32\x0e.plmn_identity\"3\n\x15\x45UTRA_ref_signal_meas\x12\x0c\n\x04rsrp\x18\x01 \x01(\x05\x12\x0c\n\x04rsrq\x18\x02 \x01(\x05\"\x82\x01\n\x12\x45UTRA_measurements\x12\x14\n\x0cphys_cell_id\x18\x01 \x01(\r\x12)\n\x08\x63gi_meas\x18\x02 \x01(\x0b\x32\x17.EUTRA_cgi_measurements\x12+\n\x0bmeas_result\x18\x03 \x01(\x0b\x32\x16.EUTRA_ref_signal_meas\"C\n\x18neigh_cells_measurements\x12\'\n\nEUTRA_meas\x18\x01 \x03(\x0b\x32\x13.EUTRA_measurements\"\xa7\x01\n\rrrc_meas_repl\x12\x0c\n\x04rnti\x18\x01 \x02(\r\x12!\n\x06status\x18\x02 \x02(\x0e\x32\x11.stats_req_status\x12\x0e\n\x06measId\x18\x03 \x01(\x05\x12\x12\n\nPCell_rsrp\x18\x04 \x01(\x05\x12\x12\n\nPCell_rsrq\x18\x05 \x01(\x05\x12-\n\nneigh_meas\x18\x06 \x01(\x0b\x32\x19.neigh_cells_measurements\"V\n\x08rrc_meas\x12\x1c\n\x03req\x18\x01 \x01(\x0b\x32\r.rrc_meas_reqH\x00\x12\x1e\n\x04repl\x18\x02 \x01(\x0b\x32\x0e.rrc_meas_replH\x00\x42\x0c\n\nrrc_meas_m*\x19\n\x08rat_type\x12\r\n\tRAT_EUTRA\x10\x00*8\n\x10stats_req_status\x12\x11\n\rSREQS_SUCCESS\x10\x00\x12\x11\n\rSREQS_FAILURE\x10\x01')
  ,
  dependencies=[configs__pb2.DESCRIPTOR,])
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

_RAT_TYPE = _descriptor.EnumDescriptor(
  name='rat_type',
  full_name='rat_type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='RAT_EUTRA', index=0, number=0,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=923,
  serialized_end=948,
)
_sym_db.RegisterEnumDescriptor(_RAT_TYPE)

rat_type = enum_type_wrapper.EnumTypeWrapper(_RAT_TYPE)
_STATS_REQ_STATUS = _descriptor.EnumDescriptor(
  name='stats_req_status',
  full_name='stats_req_status',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='SREQS_SUCCESS', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SREQS_FAILURE', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=950,
  serialized_end=1006,
)
_sym_db.RegisterEnumDescriptor(_STATS_REQ_STATUS)

stats_req_status = enum_type_wrapper.EnumTypeWrapper(_STATS_REQ_STATUS)
RAT_EUTRA = 0
SREQS_SUCCESS = 0
SREQS_FAILURE = 1



_RRC_MEAS_REQ = _descriptor.Descriptor(
  name='rrc_meas_req',
  full_name='rrc_meas_req',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='rnti', full_name='rrc_meas_req.rnti', index=0,
      number=1, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='rat', full_name='rrc_meas_req.rat', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='measId', full_name='rrc_meas_req.measId', index=2,
      number=3, type=5, cpp_type=1, label=2,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='m_obj', full_name='rrc_meas_req.m_obj', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='r_conf', full_name='rrc_meas_req.r_conf', index=4,
      number=5, type=11, cpp_type=10, label=1,
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
  serialized_start=36,
  serialized_end=168,
)


_PLMN_IDENTITY = _descriptor.Descriptor(
  name='plmn_identity',
  full_name='plmn_identity',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='mnc', full_name='plmn_identity.mnc', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='mcc', full_name='plmn_identity.mcc', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=170,
  serialized_end=211,
)


_CELL_GLOBAL_ID_EUTRA = _descriptor.Descriptor(
  name='cell_global_id_EUTRA',
  full_name='cell_global_id_EUTRA',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='plmn_id', full_name='cell_global_id_EUTRA.plmn_id', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cell_id', full_name='cell_global_id_EUTRA.cell_id', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=213,
  serialized_end=285,
)


_EUTRA_CGI_MEASUREMENTS = _descriptor.Descriptor(
  name='EUTRA_cgi_measurements',
  full_name='EUTRA_cgi_measurements',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cgi', full_name='EUTRA_cgi_measurements.cgi', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='tracking_area_code', full_name='EUTRA_cgi_measurements.tracking_area_code', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='plmn_id', full_name='EUTRA_cgi_measurements.plmn_id', index=2,
      number=3, type=11, cpp_type=10, label=3,
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
  serialized_start=287,
  serialized_end=408,
)


_EUTRA_REF_SIGNAL_MEAS = _descriptor.Descriptor(
  name='EUTRA_ref_signal_meas',
  full_name='EUTRA_ref_signal_meas',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='rsrp', full_name='EUTRA_ref_signal_meas.rsrp', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='rsrq', full_name='EUTRA_ref_signal_meas.rsrq', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=410,
  serialized_end=461,
)


_EUTRA_MEASUREMENTS = _descriptor.Descriptor(
  name='EUTRA_measurements',
  full_name='EUTRA_measurements',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='phys_cell_id', full_name='EUTRA_measurements.phys_cell_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cgi_meas', full_name='EUTRA_measurements.cgi_meas', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='meas_result', full_name='EUTRA_measurements.meas_result', index=2,
      number=3, type=11, cpp_type=10, label=1,
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
  serialized_start=464,
  serialized_end=594,
)


_NEIGH_CELLS_MEASUREMENTS = _descriptor.Descriptor(
  name='neigh_cells_measurements',
  full_name='neigh_cells_measurements',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='EUTRA_meas', full_name='neigh_cells_measurements.EUTRA_meas', index=0,
      number=1, type=11, cpp_type=10, label=3,
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
  serialized_start=596,
  serialized_end=663,
)


_RRC_MEAS_REPL = _descriptor.Descriptor(
  name='rrc_meas_repl',
  full_name='rrc_meas_repl',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='rnti', full_name='rrc_meas_repl.rnti', index=0,
      number=1, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='status', full_name='rrc_meas_repl.status', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='measId', full_name='rrc_meas_repl.measId', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='PCell_rsrp', full_name='rrc_meas_repl.PCell_rsrp', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='PCell_rsrq', full_name='rrc_meas_repl.PCell_rsrq', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='neigh_meas', full_name='rrc_meas_repl.neigh_meas', index=5,
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
  serialized_start=666,
  serialized_end=833,
)


_RRC_MEAS = _descriptor.Descriptor(
  name='rrc_meas',
  full_name='rrc_meas',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='req', full_name='rrc_meas.req', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='repl', full_name='rrc_meas.repl', index=1,
      number=2, type=11, cpp_type=10, label=1,
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
    _descriptor.OneofDescriptor(
      name='rrc_meas_m', full_name='rrc_meas.rrc_meas_m',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=835,
  serialized_end=921,
)

_RRC_MEAS_REQ.fields_by_name['rat'].enum_type = _RAT_TYPE
_RRC_MEAS_REQ.fields_by_name['m_obj'].message_type = configs__pb2._MEAS_OBJECT
_RRC_MEAS_REQ.fields_by_name['r_conf'].message_type = configs__pb2._REPORT_CONFIG
_CELL_GLOBAL_ID_EUTRA.fields_by_name['plmn_id'].message_type = _PLMN_IDENTITY
_EUTRA_CGI_MEASUREMENTS.fields_by_name['cgi'].message_type = _CELL_GLOBAL_ID_EUTRA
_EUTRA_CGI_MEASUREMENTS.fields_by_name['plmn_id'].message_type = _PLMN_IDENTITY
_EUTRA_MEASUREMENTS.fields_by_name['cgi_meas'].message_type = _EUTRA_CGI_MEASUREMENTS
_EUTRA_MEASUREMENTS.fields_by_name['meas_result'].message_type = _EUTRA_REF_SIGNAL_MEAS
_NEIGH_CELLS_MEASUREMENTS.fields_by_name['EUTRA_meas'].message_type = _EUTRA_MEASUREMENTS
_RRC_MEAS_REPL.fields_by_name['status'].enum_type = _STATS_REQ_STATUS
_RRC_MEAS_REPL.fields_by_name['neigh_meas'].message_type = _NEIGH_CELLS_MEASUREMENTS
_RRC_MEAS.fields_by_name['req'].message_type = _RRC_MEAS_REQ
_RRC_MEAS.fields_by_name['repl'].message_type = _RRC_MEAS_REPL
_RRC_MEAS.oneofs_by_name['rrc_meas_m'].fields.append(
  _RRC_MEAS.fields_by_name['req'])
_RRC_MEAS.fields_by_name['req'].containing_oneof = _RRC_MEAS.oneofs_by_name['rrc_meas_m']
_RRC_MEAS.oneofs_by_name['rrc_meas_m'].fields.append(
  _RRC_MEAS.fields_by_name['repl'])
_RRC_MEAS.fields_by_name['repl'].containing_oneof = _RRC_MEAS.oneofs_by_name['rrc_meas_m']
DESCRIPTOR.message_types_by_name['rrc_meas_req'] = _RRC_MEAS_REQ
DESCRIPTOR.message_types_by_name['plmn_identity'] = _PLMN_IDENTITY
DESCRIPTOR.message_types_by_name['cell_global_id_EUTRA'] = _CELL_GLOBAL_ID_EUTRA
DESCRIPTOR.message_types_by_name['EUTRA_cgi_measurements'] = _EUTRA_CGI_MEASUREMENTS
DESCRIPTOR.message_types_by_name['EUTRA_ref_signal_meas'] = _EUTRA_REF_SIGNAL_MEAS
DESCRIPTOR.message_types_by_name['EUTRA_measurements'] = _EUTRA_MEASUREMENTS
DESCRIPTOR.message_types_by_name['neigh_cells_measurements'] = _NEIGH_CELLS_MEASUREMENTS
DESCRIPTOR.message_types_by_name['rrc_meas_repl'] = _RRC_MEAS_REPL
DESCRIPTOR.message_types_by_name['rrc_meas'] = _RRC_MEAS
DESCRIPTOR.enum_types_by_name['rat_type'] = _RAT_TYPE
DESCRIPTOR.enum_types_by_name['stats_req_status'] = _STATS_REQ_STATUS

rrc_meas_req = _reflection.GeneratedProtocolMessageType('rrc_meas_req', (_message.Message,), dict(
  DESCRIPTOR = _RRC_MEAS_REQ,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:rrc_meas_req)
  ))
_sym_db.RegisterMessage(rrc_meas_req)

plmn_identity = _reflection.GeneratedProtocolMessageType('plmn_identity', (_message.Message,), dict(
  DESCRIPTOR = _PLMN_IDENTITY,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:plmn_identity)
  ))
_sym_db.RegisterMessage(plmn_identity)

cell_global_id_EUTRA = _reflection.GeneratedProtocolMessageType('cell_global_id_EUTRA', (_message.Message,), dict(
  DESCRIPTOR = _CELL_GLOBAL_ID_EUTRA,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:cell_global_id_EUTRA)
  ))
_sym_db.RegisterMessage(cell_global_id_EUTRA)

EUTRA_cgi_measurements = _reflection.GeneratedProtocolMessageType('EUTRA_cgi_measurements', (_message.Message,), dict(
  DESCRIPTOR = _EUTRA_CGI_MEASUREMENTS,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:EUTRA_cgi_measurements)
  ))
_sym_db.RegisterMessage(EUTRA_cgi_measurements)

EUTRA_ref_signal_meas = _reflection.GeneratedProtocolMessageType('EUTRA_ref_signal_meas', (_message.Message,), dict(
  DESCRIPTOR = _EUTRA_REF_SIGNAL_MEAS,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:EUTRA_ref_signal_meas)
  ))
_sym_db.RegisterMessage(EUTRA_ref_signal_meas)

EUTRA_measurements = _reflection.GeneratedProtocolMessageType('EUTRA_measurements', (_message.Message,), dict(
  DESCRIPTOR = _EUTRA_MEASUREMENTS,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:EUTRA_measurements)
  ))
_sym_db.RegisterMessage(EUTRA_measurements)

neigh_cells_measurements = _reflection.GeneratedProtocolMessageType('neigh_cells_measurements', (_message.Message,), dict(
  DESCRIPTOR = _NEIGH_CELLS_MEASUREMENTS,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:neigh_cells_measurements)
  ))
_sym_db.RegisterMessage(neigh_cells_measurements)

rrc_meas_repl = _reflection.GeneratedProtocolMessageType('rrc_meas_repl', (_message.Message,), dict(
  DESCRIPTOR = _RRC_MEAS_REPL,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:rrc_meas_repl)
  ))
_sym_db.RegisterMessage(rrc_meas_repl)

rrc_meas = _reflection.GeneratedProtocolMessageType('rrc_meas', (_message.Message,), dict(
  DESCRIPTOR = _RRC_MEAS,
  __module__ = 'statistics_pb2'
  # @@protoc_insertion_point(class_scope:rrc_meas)
  ))
_sym_db.RegisterMessage(rrc_meas)


# @@protoc_insertion_point(module_scope)