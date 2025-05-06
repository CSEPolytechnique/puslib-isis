from functools import partial

from puslib import time
from puslib.packet import PusTcPacket
from puslib.parameter import UInt8Parameter, UInt16Parameter
from puslib.pus_policy import PusPolicy
from puslib import get_policy, set_policy


def test_factory_functions():
    cuc_time = get_policy().CucTime()
    assert isinstance(cuc_time, time.CucTime)
    assert cuc_time.seconds > 0

    cuc_time = get_policy().CucTime(1, 2)
    assert cuc_time.seconds == 1
    assert cuc_time.fraction == 2

    tm_packet = get_policy().PusTmPacket(time=cuc_time)
    assert tm_packet.secondary_header.pus_version == 1



    tc_packet = get_policy().PusTcPacket()
    assert tc_packet.secondary_header.pus_version == 1
    assert len(tc_packet) == 11




def test_set_policy():
    class Policy1(PusPolicy):
        def __init__(self):
            super().__init__()
            self.request_verification.failure_code_type = UInt8Parameter

        def PusTcPacket(self, *args, **kwargs):
            func = partial(PusTcPacket.create,
                           pus_version=1,
                           source=None)
            return func(*args, **kwargs)

    policy = Policy1()
    set_policy(policy)
    assert isinstance(get_policy().request_verification.failure_code_type(), UInt8Parameter)

    tc_packet = get_policy().PusTcPacket()
    assert tc_packet.secondary_header.pus_version == 1

    class Policy2(PusPolicy):
        def __init__(self):
            super().__init__()
            self.request_verification.failure_code_type = UInt16Parameter

        def PusTcPacket(self, *args, **kwargs):
            func = partial(PusTcPacket.create,
                           pus_version=2,
                           source=None)
            return func(*args, **kwargs)

    policy = Policy2()
    set_policy(policy)
    assert isinstance(get_policy().request_verification.failure_code_type(), UInt16Parameter)

    tc_packet = get_policy().PusTcPacket()
    assert tc_packet.secondary_header.pus_version == 2
