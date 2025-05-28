"""
Adapter for PicoScope 6000E series USB oscilloscopes.

This adapter uses Marcus Engineering's open-source ps6000a wrapper for the
PicoScope API, available here:

https://github.com/Marcus-Engineering/ps6000a

Type ignores should be removed once ps6000a package can actually be installed
through normal means (it's not on pip right now).
"""

from dataclasses import dataclass
import logging
import time

import numpy as np
from ps6000a.buffers import Buffer  # type: ignore
from ps6000a.constants import (  # type: ignore
    PicoBandwidthLimiter,
    PicoChannel,
    PicoConnectProbeRange,
    PicoCoupling,
    PicoDeviceResolution,
    PicoInfo,
    PicoRatioMode,
    PicoStatus,
    PicoThresholdDirection,
)
from ps6000a.exceptions import PicoHandleError  # type: ignore
from ps6000a.ps6000a import PS6000A  # type: ignore

from o_scope_lock_in_amplifier.oscilloscope_utils import (
    AcquisitionData,
    OscilloscopeChannels,
    OScope,
)

logger = logging.getLogger("o_scope_lock_in_amplifier")

_GLOBAL_PS_SEG = 0


def _lia_chan_to_ps_chan(chan: OscilloscopeChannels) -> PicoChannel:
    if chan == OscilloscopeChannels.CHANNEL_1:
        return PicoChannel.CHANNEL_A
    elif chan == OscilloscopeChannels.CHANNEL_2:
        return PicoChannel.CHANNEL_B
    elif chan == OscilloscopeChannels.CHANNEL_3:
        return PicoChannel.CHANNEL_C
    elif chan == OscilloscopeChannels.CHANNEL_4:
        return PicoChannel.CHANNEL_D
    else:
        raise ValueError(f"No PS mapping for abstract channel: {chan}")


@dataclass
class _PsParams:
    ref_channel: PicoChannel
    sig_channel: PicoChannel
    ref_range: PicoConnectProbeRange
    sig_range: PicoConnectProbeRange
    ref_buf: Buffer
    sig_buf: Buffer
    resolution: PicoDeviceResolution
    samples: int
    timebase: int
    interval: float


class PS6000E(OScope):
    def __init__(
        self,
        ref_channel: OscilloscopeChannels = OscilloscopeChannels.CHANNEL_1,
        acquisition_channel: OscilloscopeChannels = OscilloscopeChannels.CHANNEL_3,
        resolution: PicoDeviceResolution = PicoDeviceResolution.DR_12BIT,
    ) -> None:
        super().__init__(ref_channel, acquisition_channel)

        self._ps = PS6000A()
        if not self._ps.open_unit(None, resolution):
            print("Device not connected.")
            exit(-1)
        if self._ps.last_status != PicoStatus.OK:
            print(f"Result of open_unit is {self._ps.last_status.name}.")
            exit(-1)
        if self._ps.raw_handle is None or self._ps.raw_handle <= 0:
            print("Could not find/open scope.")
            exit(-1)

        self._resolution = resolution
        self._ref_channel = _lia_chan_to_ps_chan(ref_channel)
        self._sig_channel = _lia_chan_to_ps_chan(acquisition_channel)
        self._setup: _PsParams | None = None

        self._ps.set_channel_off(PicoChannel.CHANNEL_A)
        self._ps.set_channel_off(PicoChannel.CHANNEL_B)
        self._ps.set_channel_off(PicoChannel.CHANNEL_C)
        self._ps.set_channel_off(PicoChannel.CHANNEL_D)

        self.idn = (
            f"PS {self._ps.get_unit_info(PicoInfo.VARIANT_INFO)} "
            f"SN {self._ps.get_unit_info(PicoInfo.BATCH_AND_SERIAL)}"
        )
        logger.debug(f"Connected to {self.idn}")

    def setup_capture(
        self,
        memory_depth: int = 1_000_000,
        sample_rate: int = 1_000_000,
        ref_range: PicoConnectProbeRange = PicoConnectProbeRange.X1_PROBE_10V,
        sig_range: PicoConnectProbeRange = PicoConnectProbeRange.X1_PROBE_10V,
    ) -> None:
        self._ps.set_channel_on(
            channel=self._ref_channel,
            coupling=PicoCoupling.AC,
            range_=ref_range,
            analog_offset=0,
            bandwidth=PicoBandwidthLimiter.BW_FULL,
        )
        self._ps.set_channel_on(
            channel=self._sig_channel,
            coupling=PicoCoupling.AC,
            range_=sig_range,
            analog_offset=0,
            bandwidth=PicoBandwidthLimiter.BW_FULL,
        )
        # DISABLE trigger (set free running)
        self._ps.set_simple_trigger(
            enable=False,
            source=self._ref_channel,
            threshold=0,
            direction=PicoThresholdDirection.NONE,
            delay=0,
            auto_trigger_micro_seconds=0,
        )

        ref_buf = self._ps.get_data_buffer(
            channel=self._ref_channel,
            n_samples=memory_depth,
            data_type=self._resolution.min_type,
            segment=_GLOBAL_PS_SEG,
            down_sample_ratio_mode=PicoRatioMode.RAW,
            clear_others=True,
        )
        sig_buf = self._ps.get_data_buffer(
            channel=self._sig_channel,
            n_samples=memory_depth,
            data_type=self._resolution.min_type,
            segment=_GLOBAL_PS_SEG,
            down_sample_ratio_mode=PicoRatioMode.RAW,
            clear_others=False,
        )
        chan_flags = self._ref_channel.flag | self._sig_channel.flag
        timebase, interval = self._ps.nearest_sample_interval_stateless(
            chan_flags, 1 / sample_rate, self._resolution
        )
        logger.info(f"Actual sample rate: {1 / interval:.3f} Hz")

        self._setup = _PsParams(
            ref_channel=self._ref_channel,
            sig_channel=self._sig_channel,
            ref_range=ref_range,
            sig_range=sig_range,
            ref_buf=ref_buf,
            sig_buf=sig_buf,
            resolution=self._resolution,
            samples=memory_depth,
            timebase=timebase,
            interval=interval,
        )

    def get_data(self) -> AcquisitionData:
        if self._setup is None:
            raise RuntimeError("Run setup_capture first!!")

        self._ps.run_block(
            0, self._setup.samples, self._setup.timebase, _GLOBAL_PS_SEG, None
        )

        t0 = time.perf_counter()
        while not self._ps.is_ready():
            time.sleep(0.1)
            if (time.perf_counter() - t0) > (
                self._setup.interval * self._setup.samples * 3 + 5.0
            ):
                self._ps.close_unit()
                raise RuntimeError("Capture timed out.")

        _, ovf = self._ps.get_values(
            0, self._setup.samples, 1, PicoRatioMode.RAW, _GLOBAL_PS_SEG
        )
        logger.debug(f"Buffers acquired in {time.perf_counter() - t0:.6f}s")

        return AcquisitionData(
            ref_dat=np.array(self._setup.ref_buf.buffer)
            / self._setup.resolution.min_type.max
            * self._setup.ref_range.full_scale,
            aqu_dat=np.array(self._setup.sig_buf.buffer)
            / self._setup.resolution.min_type.max
            * self._setup.sig_range.full_scale,
            time_increment=self._setup.interval,
            time_origin=0.0,
        )

    def release(self) -> None:
        try:
            self._ps.close_unit()
        except PicoHandleError:
            pass

    def __del__(self) -> None:
        self.release()


if __name__ == "__main__":
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("qtagg")

    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.root.handlers:
        handler.addFilter(logging.Filter("o_scope_lock_in_amplifier"))

    s = PS6000E()
    s.setup_capture()
    r = s.get_data()

    r = s.get_data()
    s.release()

    plt.plot(r.ref_dat)
    plt.plot(r.aqu_dat)
    plt.show()
