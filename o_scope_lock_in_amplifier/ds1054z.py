import logging
import time
from typing import Optional

import numpy as np  # type: ignore
import pyvisa
from tqdm.auto import trange

from o_scope_lock_in_amplifier.oscilloscope_utils import (
    AcquisitionData,
    OscilloscopeChannels,
    OScope,
    allowed_vals,
)

logger = logging.getLogger("o_scope_lock_in_amplifier")


class DS1054z(OScope):
    def __init__(
        self,
        conn_str: str = "auto",
        ref_channel: OscilloscopeChannels = OscilloscopeChannels.CHANNEL_1,
        acquisition_channel: OscilloscopeChannels = OscilloscopeChannels.CHANNEL_2,
    ) -> None:
        super().__init__(ref_channel, acquisition_channel)

        self.rm = pyvisa.ResourceManager()
        if conn_str == "auto":
            for r in self.rm.list_resources():
                if r.startswith("USB"):
                    conn_str = r
                    break
        if conn_str == "auto":
            raise RuntimeError(
                f"Could not find a USB Device! Try passing a conn_string; e.x. for IP TCPIP::<ip address>::inst0::INSTR\nFound:\n\t{'\n\t'.join(self.rm.list_resources())}"
            )

        self.scope: pyvisa.resources.usb.USBInstrument = self.rm.open_resource(  # type: ignore
            conn_str
        )
        self.idn = self.scope.query("*IDN?")

        self.ref_channel = ref_channel
        self.acquisition_channel = acquisition_channel

        self.setup_capture(memory_depth=6_000)

        logger.debug(f"Connected to {self.idn}")

    @allowed_vals(memory_depth=[6_000, 60_000, 600_000, 6_000_000, 12_000_000])
    def setup_capture(
        self,
        memory_depth: int = 12_000_000,
    ) -> None:
        self.scope.write(":RUN")
        time.sleep(0.25)
        # Disable all non-selected channels, and enable the selected ones
        for channel in OscilloscopeChannels:
            if channel in (self.ref_channel, self.acquisition_channel):
                # Enable selected channels
                self.scope.write(f":CHANnel{channel.value}:DISPlay ON")
            else:
                # Disable non-selected channels
                self.scope.write(f":CHANnel{channel.value}:DISPlay OFF")

        self.scope.write(f":ACQuire:MDEPth {memory_depth}")
        time.sleep(0.1)
        self.scope.write(":WAVeform:FORMat BYTE")
        time.sleep(0.1)
        self.scope.write(":WAVeform:MODE NORMal")
        time.sleep(0.1)
        self.scope.write(":TRIG:SWE SING")
        time.sleep(0.1)
        total_points = int(self.scope.query(":ACQuire:MDEPth?"))

        assert total_points == memory_depth

    def read_waveform_in_batches(
        self, channel: OscilloscopeChannels, max_points_per_read: int = 125000
    ) -> np.ndarray:
        logger.debug(f"Getting data for channel {channel}")

        # Stop the oscilloscope to read from internal memory
        self.scope.write(":STOP")

        # Get the total memory depth (number of points)
        total_points = int(self.scope.query(":ACQuire:MDEPth?"))

        # Set the source to the given channel
        self.scope.write(f":WAVeform:SOURce CHANnel{channel.value}")

        # Retrieve the scaling factors for voltage conversion
        voltage_increment = float(self.scope.query(":WAVeform:YINCrement?"))
        voltage_origin = float(self.scope.query(":WAVeform:YORigin?"))
        voltage_reference = int(self.scope.query(":WAVeform:YREFerence?"))
        logger.debug(f"\t{voltage_origin=}")
        logger.debug(f"\t{voltage_increment=}")
        logger.debug(f"\t{voltage_reference=}")

        if voltage_reference == 4294967295:
            raise RuntimeError("Empty Data! No data in memory.")

        # Initialize data storage for waveform data
        all_waveform_data = []

        # Calculate the number of batches (ceiling division)
        num_batches = (total_points + max_points_per_read - 1) // max_points_per_read

        # Read waveform data in batches
        for batch in trange(num_batches, desc=f"Reading {channel}"):
            start_point = batch * max_points_per_read + 1
            stop_point = min((batch + 1) * max_points_per_read, total_points)

            # Set the start and stop points for the current batch
            self.scope.write(f":WAVeform:STARt {start_point}")
            self.scope.write(f":WAVeform:STOP {stop_point}")

            # Read the raw data from the current batch
            raw_waveform_data = self.scope.query_binary_values(
                ":WAVeform:DATA?", datatype="B", is_big_endian=True
            )

            # Convert the raw data to voltage using the scaling factors
            voltage_data = [
                (d - voltage_reference) * voltage_increment - voltage_origin
                for d in raw_waveform_data
            ]

            # Append the voltage data to the waveform data list
            all_waveform_data.extend(voltage_data)

        # Convert the list of voltage data to a NumPy array and return it
        return np.array(all_waveform_data)

    def get_data(self) -> AcquisitionData:
        self.scope.write(":RUN")
        self.scope.write(":TRIG:SWE SING")
        self.scope.write(":TFOR")
        while (stat := self.scope.query(":TRIG:STAT?").strip()) != "STOP":
            logger.debug(f":TRIG:STAT? = {stat}")
            if stat == "WAIT":
                self.scope.write(":TFOR")
            time.sleep(0.1)

        ref_dat = self.read_waveform_in_batches(self.ref_channel)
        aqu_dat = self.read_waveform_in_batches(self.acquisition_channel)
        time_increment = float(self.scope.query(":WAVeform:XINCrement?"))
        time_origin = float(self.scope.query(":WAVeform:XORigin?"))

        logger.info(f"Got {time_increment * len(ref_dat)} sec of data")

        return AcquisitionData(ref_dat, time_increment, time_origin, aqu_dat)


if __name__ == "__main__":
    import matplotlib
    import matplotlib.pyplot as plt  # type: ignore

    matplotlib.use("qtagg")

    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.root.handlers:
        handler.addFilter(logging.Filter("o_scope_lock_in_amplifier"))

    s = DS1054z()
    s.setup_capture(memory_depth=6_000)
    r = s.get_data()

    r = s.get_data()
    # plt.plot(r.ref_dat)
    # plt.plot(r.aqu_dat)
    # plt.show()
