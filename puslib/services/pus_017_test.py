from puslib import get_pus_policy
from .service import PusService, PusServiceType


class Test(PusService):
    def __init__(self, ident, pus_service_1, tm_distributor):
        super().__init__(PusServiceType.TEST, ident, pus_service_1, tm_distributor)
        super()._register_sub_service(1, self.connection_test)

    def connection_test(self, packet):
        time = get_pus_policy().CucTime()
        report = get_pus_policy().PusTmPacket(
            apid=self._ident.apid,
            seq_count=self._ident.seq_count(),
            service_type=self._service_type.value,
            service_subtype=2,
            time=time
        )
        self._tm_distributor.send(report)
        return True
