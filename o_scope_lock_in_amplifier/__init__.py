"""Turn your oscilloscope into a lock in amplifier with this one simple trick!."""

from ds1054z import DS1054z
import numpy as np  # type: ignore

scope_types = [
    DS1054z,
]
