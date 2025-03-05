from collections import namedtuple

import pytest

from puslib.packet import CcsdsSpacePacket
from puslib.packet import PusTcPacket
from puslib.packet import PusTmPacket
from puslib.packet import PacketType
from puslib.packet import AckFlag
from puslib.time import CucTime

APID = 0x10
SEQ_COUNT_OR_NAME = 0x50
PUS_SERVICE = 8
PUS_SUBSERVICE = 1
TC_SOURCE = 0x02
DATA = bytes.fromhex('DEADBEEF')

CcsdsPacketArgs = namedtuple('CcsdsPacketArgs', ['packet_version_number', 'packet_type', 'secondary_header_flag', 'apid', 'seq_flags', 'seq_count_or_name', 'data', 'has_pec'])


@pytest.mark.parametrize("args", [
    CcsdsPacketArgs(None, PacketType.TC, None, APID, None, SEQ_COUNT_OR_NAME, b'', True),
    CcsdsPacketArgs(None, PacketType.TC, None, APID, None, SEQ_COUNT_OR_NAME, b'', False),
    CcsdsPacketArgs(0, PacketType.TM, True, APID, 0b11, SEQ_COUNT_OR_NAME, DATA, True),
    CcsdsPacketArgs(0, PacketType.TM, False, APID, 0b11, SEQ_COUNT_OR_NAME, DATA, False),
])
def test_create_ccsds_packet(args):
    args_to_pass = {k: v for k, v in args._asdict().items() if v is not None}

    packet = CcsdsSpacePacket.create(**args_to_pass)
    assert packet.header.packet_version_number == args.packet_version_number if args.packet_version_number else 1
    assert packet.header.packet_type == args.packet_type
    assert packet.packet_type == args.packet_type
    assert packet.header.secondary_header_flag == args.secondary_header_flag if args.secondary_header_flag else True
    assert packet.header.apid == args.apid
    assert packet.apid == args.apid
    assert packet.header.seq_flags == args.seq_flags if args.seq_flags else 0b11
    assert packet.header.seq_count_or_name == args.seq_count_or_name
    assert packet.payload == args.data
    assert len(packet) == 6 + (len(args.data) if args.data else 0) + (2 if args.has_pec else 0)


TcPacketArgs = namedtuple('TcPacketArgs', ['apid', 'name', 'pus_version', 'ack_flags', 'service_type', 'service_subtype', 'source', 'data', 'has_pec'])


@pytest.mark.parametrize("args", [
    TcPacketArgs(APID, SEQ_COUNT_OR_NAME, 1, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, None, None, True),
    TcPacketArgs(APID, SEQ_COUNT_OR_NAME, 2, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, None, True),
    TcPacketArgs(APID, SEQ_COUNT_OR_NAME, 2, AckFlag.ACCEPTANCE | AckFlag.COMPLETION, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, DATA, True),
])
def test_tc_packet_create(args):
    args_to_pass = {k: v for k, v in args._asdict().items() if v is not None}

    packet = PusTcPacket.create(**args_to_pass)
    assert packet.name == args.name
    assert packet.secondary_header.pus_version == args.pus_version
    assert packet.secondary_header.ack_flags == args.ack_flags
    assert packet.secondary_header.service_type == args.service_type
    assert packet.secondary_header.service_subtype == args.service_subtype
    assert packet.secondary_header.source == args.source


@pytest.mark.parametrize("args, length", [
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, None, None, False), 9),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, None, b'', True), 11),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, b'', False), 10),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, b'', True), 12),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, DATA, False), 14),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, DATA, True), 16),
])
def test_tc_packet_length(args, length):
    args_to_pass = {k: v for k, v in args._asdict().items() if v is not None}
    packet = PusTcPacket.create(**args_to_pass)
    assert len(packet) == length


@pytest.mark.parametrize("args, acks_activated, acks_deactivated", [
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.NONE, PUS_SERVICE, PUS_SUBSERVICE, None, None, False), (), (AckFlag.ACCEPTANCE, AckFlag.START_OF_EXECUTION, AckFlag.PROGRESS, AckFlag.COMPLETION)),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE | AckFlag.COMPLETION, PUS_SERVICE, PUS_SUBSERVICE, None, b'', True), (AckFlag.ACCEPTANCE, AckFlag.COMPLETION), (AckFlag.START_OF_EXECUTION, AckFlag.PROGRESS)),
])
def test_tc_ack(args, acks_activated, acks_deactivated):
    args_to_pass = {k: v for k, v in args._asdict().items() if v is not None}
    packet = PusTcPacket.create(**args_to_pass)
    for ack in acks_activated:
        assert packet.ack(ack)
    for ack in acks_deactivated:
        assert not packet.ack(ack)


@pytest.mark.parametrize("args, binary", [
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, None, b'', False), bytes.fromhex('1810c0500002110801')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, None, b'', True), bytes.fromhex('1810c05000041108017e6c')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, b'', False), bytes.fromhex('1810c050000311080102')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, b'', True), bytes.fromhex('1810c050000511080102794a')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, DATA, False), bytes.fromhex('1810c050000711080102deadbeef')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, DATA, True), bytes.fromhex('1810c050000911080102deadbeef1a29')),
])
def test_tc_packet_serialize(args, binary):
    args_to_pass = {k: v for k, v in args._asdict().items() if v is not None}
    packet = PusTcPacket.create(**args_to_pass)
    buffer = packet.serialize()
    assert len(packet) == len(buffer)
    assert len(buffer) == len(binary)
    assert buffer == binary
    assert bytes(packet) == binary


@pytest.mark.parametrize("args, binary", [
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, None, b'', False), bytes.fromhex('1810c0500002210801')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, None, b'', True), bytes.fromhex('1810c0500004210801bbc9')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, b'', False), bytes.fromhex('1810c050000321080102')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, b'', True), bytes.fromhex('1810c05000052108010255a3')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, DATA, False), bytes.fromhex('1810c050000721080102deadbeef')),
    (TcPacketArgs(APID, SEQ_COUNT_OR_NAME, None, AckFlag.ACCEPTANCE, PUS_SERVICE, PUS_SUBSERVICE, TC_SOURCE, DATA, True), bytes.fromhex('1810c050000921080102deadbeef5cf5')),
])
def test_tc_packet_deserialize(args, binary):
    packet = PusTcPacket.deserialize(binary, has_source_field=True if args.source else False, has_pec=True if args.has_pec else False)
    assert packet.apid == args.apid
    assert packet.name == args.name
    assert packet.secondary_header.pus_version == (args.pus_version if args.pus_version else 2)
    assert packet.secondary_header.ack_flags == args.ack_flags
    assert packet.service == args.service_type
    assert packet.subservice == args.service_subtype
    assert packet.source == args.source
    assert packet.app_data == args.data
    assert packet.has_pec == args.has_pec

    buffer = packet.serialize()
    assert len(buffer) == len(binary)
    assert buffer == binary


PUS_SERVICE = 130
PUS_SUBSERVICE = 4
MSG_TYPE_COUNTER = 0x13
TM_DESTINATION = 0x02
TIME = CucTime(100, 10000, 4, 2)
DATA = bytes.fromhex('DEADBEEF')

TmPacketArgs = namedtuple('TmPacketArgs', ['apid', 'seq_count', 'pus_version', 'spacecraft_time_ref_status', 'service_type', 'service_subtype', 'msg_type_counter', 'destination', 'time', 'data', 'has_pec'])


@pytest.mark.parametrize("args", [
    TmPacketArgs(APID, SEQ_COUNT_OR_NAME, 1, None, PUS_SERVICE, PUS_SUBSERVICE, None, None, TIME, b'', True),
    TmPacketArgs(APID, SEQ_COUNT_OR_NAME, 2, 1, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, DATA, True),
])
def test_tm_packet_create(args):
    args_to_pass = {k: v for k, v in args._asdict().items() if v is not None}

    packet = PusTmPacket.create(**args_to_pass)
    assert packet.seq_count == args.seq_count
    assert packet.secondary_header.pus_version == args.pus_version
    assert packet.secondary_header.spacecraft_time_ref_status == (args.spacecraft_time_ref_status if args.spacecraft_time_ref_status else 0)
    assert packet.secondary_header.service_type == args.service_type
    assert packet.secondary_header.service_subtype == args.service_subtype
    assert packet.secondary_header.msg_type_counter == args.msg_type_counter
    assert packet.secondary_header.destination == args.destination
    assert packet.secondary_header.time == args.time
    assert packet.source_data == args.data


@pytest.mark.parametrize("args, length", [
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, None, None, TIME, None, False), 16),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, None, TIME, None, False), 17),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, None, False), 18),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, DATA, False), 22),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, DATA, True), 24),
])
def test_tm_packet_length(args, length):
    args_to_pass = {k: v for k, v in args._asdict().items() if v is not None}
    packet = PusTmPacket.create(**args_to_pass)
    assert len(packet) == length


@pytest.mark.parametrize("args, binary", [
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, None, None, TIME, None, False), bytes.fromhex('0810c0500009108204') + bytes(TIME)),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, None, TIME, None, False), bytes.fromhex('0810c050000a10820413') + bytes(TIME)),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, 1, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, None, False), bytes.fromhex('0810c050000b1182041302') + bytes(TIME)),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, 1, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, DATA, False), bytes.fromhex('0810c050000f1182041302') + bytes(TIME) + DATA),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, 1, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, DATA, True), bytes.fromhex('0810c05000111182041302') + bytes(TIME) + DATA + bytes.fromhex('9ee2')),
])
def test_tm_packet_serialize(args, binary):
    args_to_pass = {k: v for k, v in args._asdict().items() if v is not None}
    packet = PusTmPacket.create(**args_to_pass)
    buffer = packet.serialize()
    assert len(packet) == len(buffer)
    assert len(buffer) == len(binary)
    assert buffer == binary
    assert bytes(packet) == binary


@pytest.mark.parametrize("args, binary", [
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, None, None, TIME, b'', False), bytes.fromhex('0810c0500009108204') + bytes(TIME)),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, None, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, None, TIME, b'', False), bytes.fromhex('0810c050000a10820413') + bytes(TIME)),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, 1, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, b'', False), bytes.fromhex('0810c050000b1182041302') + bytes(TIME)),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, 1, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, DATA, False), bytes.fromhex('0810c050000f1182041302') + bytes(TIME) + DATA),
    (TmPacketArgs(APID, SEQ_COUNT_OR_NAME, None, 1, PUS_SERVICE, PUS_SUBSERVICE, MSG_TYPE_COUNTER, TM_DESTINATION, TIME, DATA, True), bytes.fromhex('0810c05000111182041302') + bytes(TIME) + DATA + bytes.fromhex('9ee2')),
])
def test_tm_packet_deserialize(args, binary):
    packet = PusTmPacket.deserialize(binary, has_type_counter_field=True if args.msg_type_counter else False, has_destination_field=True if args.destination else False, cuc_time=TIME, has_pec=True if args.has_pec else False)
    assert packet.apid == args.apid
    assert packet.seq_count == args.seq_count
    assert packet.secondary_header.pus_version == (args.pus_version if args.pus_version else 1)
    assert packet.secondary_header.spacecraft_time_ref_status == (args.spacecraft_time_ref_status if args.spacecraft_time_ref_status else 0)
    assert packet.service == args.service_type
    assert packet.subservice == args.service_subtype
    assert packet.counter == args.msg_type_counter
    assert packet.destination == args.destination
    assert packet.time == args.time
    assert packet.source_data == args.data
    assert len(packet.source_data) == len(args.data)
    assert packet.has_pec == args.has_pec

    buffer = packet.serialize()
    assert len(buffer) == len(binary)
    assert buffer == binary
