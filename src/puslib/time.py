import math
from enum import IntEnum
from datetime import datetime
from typing import SupportsBytes

import bitstring

from puslib.exceptions import InvalidTimeFormat

TAI_EPOCH = datetime(year=1958, month=1, day=1)  # International Atomic Time (TAI) epoch


class TimeCodeIdentification(IntEnum):
    TAI = 0b001
    AGENCY_DEFINED = 0b010


class _TimeFormat:
    def __init__(self, basic_unit_length, frac_unit_length, epoch=None, preamble=None):
        if not 1 <= basic_unit_length <= 7:
            raise InvalidTimeFormat("Basic time unit must be 1 to 7 octets")
        self.basic_unit_length = basic_unit_length
        if not 0 <= frac_unit_length <= 10:
            raise InvalidTimeFormat("Fractional time unit must be 0 to 10 octets")
        self.frac_unit_length = frac_unit_length
        self.epoch = epoch if epoch else TAI_EPOCH
        self.time_code_id = TimeCodeIdentification.AGENCY_DEFINED if epoch else TimeCodeIdentification.TAI
        self.preamble = preamble if preamble else self._pack_preamble()

    def __bytes__(self):
        return self.preamble

    def __len__(self):
        return len(self.preamble)

    def _pack_preamble(self):
        p_field_extension = 1 if self.basic_unit_length > 4 or self.frac_unit_length > 3 else 0
        basic_time_unit_num_octets = min(3, self.basic_unit_length - 1)
        basic_frac_unit_num_octets = min(3, self.frac_unit_length)
        basic_time_unit_additional_octet = max(0, self.basic_unit_length - 4)
        basic_frac_unit_additional_octet = max(0, self.frac_unit_length - 3)

        octet1 = p_field_extension << 7 | self.time_code_id << 4 | basic_time_unit_num_octets << 2 | basic_frac_unit_num_octets
        preamble = bytes([octet1])
        if p_field_extension:
            octet2 = basic_time_unit_additional_octet << 5 | basic_frac_unit_additional_octet << 2
            preamble += bytes([octet2])
        return preamble

    @classmethod
    def deserialize(cls, buffer):
        if len(buffer) < 2:
            raise ValueError("Buffer too small to contain CUC")
        octet1 = buffer[0]
        p_field_extension = octet1 >> 7
        basic_unit_length = ((octet1 >> 2) & 0b11) + 1
        if p_field_extension:
            octet2 = buffer[1]
            basic_unit_length += (octet2 >> 5) & 0b11
        frac_unit_length = (octet1 & 0b11) + (((octet2 >> 2) & 0b111) if p_field_extension else 0)
        epoch = (octet1 >> 4) & 0b111
        preamble = bytes([buffer[0]]) + (bytes([buffer[1]]) if p_field_extension else b'')
        return cls(basic_unit_length, frac_unit_length, epoch, preamble)


class CucTime:
    """Represents a CCSDS unsegmented time code (CUC) according to CCSDS 301.0-B.
    """
    def __init__(self, seconds: int = 0, fraction: int = 0, basic_unit_length: int = 4, frac_unit_length: int | None = 2, has_preamble: bool = True, epoch: datetime | None = None, preamble: SupportsBytes | None = None):
        """Create a CUC time instance.

        Keyword Arguments:
            seconds -- seconds since epoch (default: {0})
            fraction -- fraction of second (default: {0})
            basic_unit_length -- number of bytes to represent seconds (default: {4})
            frac_unit_length -- number of bytes to represent fraction (default: {2})
            has_preamble -- set to True if the CUC time has a preamble (default: {True})
            epoch -- epoch of time (default: {None})
            preamble -- ready-made preamble to use for this CUC time (default: {None})
        """
        self._format = _TimeFormat(basic_unit_length, frac_unit_length, epoch, preamble)
        self._has_preamble = has_preamble
        self._seconds = seconds
        self._fraction = fraction if self._format.frac_unit_length else None

    def __len__(self):
        return (len(self._format) if self._has_preamble else 0) + self._format.basic_unit_length + self._format.frac_unit_length

    def __float__(self):
        return self._seconds + (self._fraction / (2 ** (self._format.frac_unit_length * 8)))

    def __str__(self):
        return f"{float(self):.3f} seconds since epoch ({self._format.epoch})"

    def __bytes__(self):
        return (bytes(self._format) if self._has_preamble else b'') + (bitstring.pack(f'uintbe:{self._format.basic_unit_length * 8}', self._seconds).bytes) + (bitstring.pack(f'uintbe:{self._format.frac_unit_length * 8}', self._fraction).bytes if self._format.frac_unit_length else b'')

    @property
    def epoch(self) -> datetime:
        return self._format.epoch

    @property
    def seconds(self) -> int:
        return self._seconds

    @seconds.setter
    def seconds(self, val: int):
        max_val = (2 ** (self._format.basic_unit_length * 8)) - 1
        if isinstance(val, int) and 0 <= val <= max_val:
            self._seconds = val
        else:
            raise ValueError(f"Seconds must be an integer between 0 and {max_val}")

    @property
    def fraction(self) -> int:
        return self._fraction

    @fraction.setter
    def fraction(self, val: int):
        if self._format.frac_unit_length == 0:
            raise ValueError("CUC time configured without fraction part")
        max_val = (2 ** (self._format.frac_unit_length * 8)) - 1
        if isinstance(val, int) and 0 <= val <= max_val:
            self._fraction = val
        else:
            raise ValueError(f"Fraction must be an integer between 0 and {max_val}")

    @property
    def time_field(self) -> tuple[int, int]:
        """Return time as a pair of second and fraction.

        Returns:
            tuple with time components
        """
        return (self._seconds, self._fraction)

    def from_datetime(self, dt: datetime) -> float:
        """Set CUC time from a datetime.

        Arguments:
            dt -- timestamp

        Raises:
            ValueError: if timestamp is invalid

        Returns:
            seconds since epoch
        """
        if dt < self.epoch:
            raise ValueError("Cannot set CUC to before epoch")
        seconds_since_epoch = (dt - self.epoch).total_seconds()
        if self._format.frac_unit_length:
            fraction, seconds = math.modf(seconds_since_epoch)
            self._seconds = int(seconds)
            self._fraction = round(fraction * ((2 ** (self._format.frac_unit_length * 8)) - 1))
        else:
            self._seconds = round(seconds_since_epoch)
        return seconds_since_epoch

    def from_bytes(self, buffer: SupportsBytes):
        """Set CUC time from a byte array.

        Arguments:
            buffer -- byte array with a CUC binary format

        Raises:
            ValueError: if buffer is malformed according to current CUC time instance
        """
        preamble_size = len(self._format) if self._has_preamble else 0
        if len(buffer) < preamble_size + self._format.basic_unit_length + self._format.frac_unit_length:
            raise ValueError("Buffer too small to contain CUC")

        fraction_offset = preamble_size + self._format.basic_unit_length
        self._seconds = int.from_bytes(buffer[preamble_size:fraction_offset], byteorder='big')
        self._fraction = int.from_bytes(buffer[fraction_offset:fraction_offset + self._format.frac_unit_length], byteorder='big')

    @classmethod
    def deserialize(cls, buffer: SupportsBytes, has_preamble: bool = True, epoch: datetime | None = None, basic_unit_length: int | None = None, frac_unit_length: int | None = None) -> "CucTime":
        """Deserialize a binary coded CUC time to a CUC time object.

        Arguments:
            buffer -- byte array with a CUC binary format

        Keyword Arguments:
            has_preamble -- set to True if the CUC time has a preamble (default: {True})
            epoch -- epoch of time (default: {None})
            basic_unit_length -- number of bytes to represent seconds (default: {None})
            frac_unit_length -- number of bytes to represent fraction (default: {None})

        Raises:
            ValueError: if buffer is malformed or arguments contradictory

        Returns:
            CUC time object
        """
        if len(buffer) < 2:
            raise ValueError("Buffer too small to contain CUC")
        if not has_preamble and not (basic_unit_length and frac_unit_length):
            raise ValueError("If preamble not used CUC must be defined by the other arguments")
        if has_preamble:
            time_format = _TimeFormat.deserialize(buffer)
            basic_unit_length = time_format.basic_unit_length
            frac_unit_length = time_format.frac_unit_length
            preamble = bytes(time_format)
        else:
            preamble = None
        preamble_size = len(time_format) if has_preamble else 0
        if len(buffer) < preamble_size + basic_unit_length + frac_unit_length:
            raise ValueError("Buffer too small to contain CUC")

        fraction_offset = preamble_size + basic_unit_length
        seconds = int.from_bytes(buffer[preamble_size:fraction_offset], byteorder='big')
        fraction = int.from_bytes(buffer[fraction_offset:fraction_offset + frac_unit_length], byteorder='big')

        return cls(
            seconds=seconds,
            fraction=fraction,
            basic_unit_length=basic_unit_length,
            frac_unit_length=frac_unit_length,
            has_preamble=has_preamble,
            epoch=epoch,
            preamble=preamble)

    @classmethod
    def create(cls, seconds=0, fraction=0, basic_unit_length=4, frac_unit_length=2, has_preamble=True, epoch=None, preamble=None) -> "CucTime":
        """A factory method to create a CUC time instance.

        Keyword Arguments:
            seconds -- seconds since epoch (default: {0})
            fraction -- fraction of second (default: {0})
            basic_unit_length -- number of bytes to represent seconds (default: {4})
            frac_unit_length -- number of bytes to represent fraction (default: {2})
            has_preamble -- set to True if the CUC time has a preamble (default: {True})
            epoch -- epoch of time (default: {None})
            preamble -- ready-made preamble to use for this CUC time (default: {None})

        Returns:
            CUC time instance
        """
        cuc_time = cls(seconds, fraction, basic_unit_length, frac_unit_length, has_preamble, epoch, preamble)
        if seconds == 0 and fraction == 0:
            # dt_now = datetime.now(timezone.utc)
            dt_now = datetime.now()
            cuc_time.from_datetime(dt_now)
        return cuc_time
