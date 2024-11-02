"""Turn your oscilloscope into a lock in amplifier with this one simple trick!."""

from o_scope_lock_in_amplifier.ds1054z import DS1054z
from o_scope_lock_in_amplifier.ps6000e import PS6000E

scope_types = [
    DS1054z,
    PS6000E,
]
