from enum import IntEnum
from typing import SupportsBytes

from puslib import get_policy
from puslib.packet import AckFlag
from puslib.ident import PusIdent
from puslib.packet import PusTcPacket
from puslib.streams.stream import OutputStream
from puslib.services.service import PusService, PusServiceType
from puslib.services.error_codes import CommonErrorCode


class _SubService(IntEnum):
    SUCCESSFUL_ACCEPTANCE_VERIFICATION = 1
    FAILED_ACCEPTANCE_VERIFICATION = 2
    SUCCESSFUL_START_OF_EXECUTION_VERIFICATION = 3
    FAILED_START_OF_EXECUTION_VERIFICATION = 4
    SUCCESSFUL_PROGRESS_OF_EXECUTION_VERIFICATION = 5
    FAILED_PROGRESS_OF_EXECUTION_VERIFICATION = 6
    SUCCESSFUL_COMPLETION_OF_EXECUTION_VERIFICATION = 7
    FAILED_COMPLETION_OF_EXECUTION_VERIFICATION = 8


class RequestVerification(PusService):
    """PUS service 1: Request verification service."""

    def __init__(self, ident: PusIdent, tm_output_stream: OutputStream):
        """Create a PUS service instance.

        Arguments:
            ident -- PUS identifier
            tm_output_stream -- output stream
        """
        super().__init__(PusServiceType.REQUEST_VERIFICATION, ident=ident, tm_output_stream=tm_output_stream)

    def enqueue(self, tc_packet):
        raise RuntimeError("Request verification service (PUS 1) doesn't have a TC queue")

    def process(self):
        raise RuntimeError("Request verification service (PUS 1) doesn't have a TC queue")

    def accept(self, packet: PusTcPacket, success: bool = True, failure_code: CommonErrorCode | None = None, failure_data: SupportsBytes = None):
        """Generate acceptance verification report.

        Arguments:
            packet -- PUS TC packet

        Keyword Arguments:
            success -- true if acceptance successful, otherwise false (default: {True})
            failure_code -- failure code (default: {None})
            failure_data -- failure data (default: {None})
        """
        if not packet.ack(AckFlag.ACCEPTANCE):
            return
        self._generate_report(
            packet,
            _SubService.SUCCESSFUL_ACCEPTANCE_VERIFICATION if success else _SubService.FAILED_ACCEPTANCE_VERIFICATION,
            success,
            failure_code,
            failure_data)

    def start(self, packet: PusTcPacket, success: bool = True, failure_code: CommonErrorCode | None = None, failure_data: SupportsBytes = None):
        """Generate start of execution verification report.

        Arguments:
            packet -- PUS TC packet

        Keyword Arguments:
            success -- true if start of execution successful, otherwise false (default: {True})
            failure_code -- failure code (default: {None})
            failure_data -- failure data (default: {None})
        """
        if not packet.ack(AckFlag.START_OF_EXECUTION):
            return
        self._generate_report(
            packet,
            _SubService.SUCCESSFUL_START_OF_EXECUTION_VERIFICATION if success else _SubService.FAILED_START_OF_EXECUTION_VERIFICATION,
            success,
            failure_code,
            failure_data)

    def progress(self, packet: PusTcPacket, success: bool = True, failure_code: CommonErrorCode | None = None, failure_data: SupportsBytes = None):
        """Generate progress of execution verification report.

        Arguments:
            packet -- PUS TC packet

        Keyword Arguments:
            success -- true if progress of execution successful, otherwise false (default: {True})
            failure_code -- failure code (default: {None})
            failure_data -- failure data (default: {None})
        """
        if not packet.ack(AckFlag.PROGRESS):
            return
        self._generate_report(
            packet,
            _SubService.SUCCESSFUL_PROGRESS_OF_EXECUTION_VERIFICATION if success else _SubService.FAILED_PROGRESS_OF_EXECUTION_VERIFICATION,
            success,
            failure_code,
            failure_data)

    def complete(self, packet: PusTcPacket, success: bool = True, failure_code: CommonErrorCode | None = None, failure_data: SupportsBytes = None):
        """Generate completion of execution verification report.

        Arguments:
            packet -- PUS TC packet

        Keyword Arguments:
            success -- true if completion of executionn successful, otherwise false (default: {True})
            failure_code -- failure code (default: {None})
            failure_data -- failure data (default: {None})
        """
        if not packet.ack(AckFlag.COMPLETION):
            return
        self._generate_report(
            packet,
            _SubService.SUCCESSFUL_COMPLETION_OF_EXECUTION_VERIFICATION if success else _SubService.FAILED_COMPLETION_OF_EXECUTION_VERIFICATION,
            success,
            failure_code,
            failure_data)

    def _generate_report(self, packet: PusTcPacket, subservice: _SubService, success: bool, failure_code: CommonErrorCode | None, failure_data: SupportsBytes | None):
        payload = packet.request_id()
        if not success:
            if not failure_code:
                failure_code = CommonErrorCode.ILLEGAL_APP_DATA
            payload += failure_code.value.to_bytes(len(get_policy().request_verification.failure_code_type()), byteorder='big') + (failure_data if failure_data else b'')
        time = get_policy().CucTime()
        report = get_policy().PusTmPacket(
            apid=self._ident.apid,
            seq_count=self._ident.seq_count(),
            service_type=self._service_type.value,
            service_subtype=subservice,
            time=time,
            data=payload
        )
        self._tm_output_stream.write(report)
