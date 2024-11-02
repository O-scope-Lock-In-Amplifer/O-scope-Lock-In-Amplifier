from typing import cast

from numpy import ndarray
import numpy as np
from scipy.fft import fft, fftfreq  # type: ignore
from scipy.signal import butter, lfilter  # type: ignore

from o_scope_lock_in_amplifier.oscilloscope_utils import AcquisitionData


def extract_fundamental_frequency(ref_dat: np.ndarray, time_increment: float) -> float:
    """
    Extracts the fundamental frequency from the reference data using FFT.
    """
    N = len(ref_dat)
    fft_vals = fft(ref_dat)
    freqs = fftfreq(N, d=time_increment)

    # Only consider positive frequencies
    pos_mask = freqs > 0
    freqs = freqs[pos_mask]
    fft_vals = fft_vals[pos_mask]

    magnitudes = np.abs(fft_vals)

    # Find the index of the peak in the FFT magnitude spectrum
    peak_idx = np.argmax(magnitudes)
    fundamental_freq = float(freqs[peak_idx])  # Ensure it's a float

    return fundamental_freq


def generate_reference_signals(
    freq: float, N: int, time_increment: float
) -> tuple[ndarray, ndarray]:
    """
    Generates cosine and sine reference signals at the given frequency with zero phase.
    """
    t = np.arange(N) * time_increment
    cosine_signal = np.cos(2 * np.pi * freq * t)
    sine_signal = np.sin(2 * np.pi * freq * t)
    return cosine_signal, sine_signal


def low_pass_filter(
    signal: np.ndarray, cutoff: float, fs: float, order: int = 5
) -> np.ndarray:
    """
    Applies a Butterworth low-pass filter to the signal.
    """
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    # padlen = min(3 * (max(len(a), len(b)) - 1), len(signal) - 1)
    filtered_signal = cast(np.ndarray, lfilter(b, a, signal))
    return filtered_signal


def perform_lock_in(
    ampl_data: AcquisitionData, low_pass_cutoff: float, filter_order: int = 5
) -> dict:
    """
    Performs lock-in amplification on the provided acquisition data.
    """
    ref_dat = ampl_data.ref_dat
    aqu_dat = ampl_data.aqu_dat
    time_increment = ampl_data.time_increment
    time_origin = ampl_data.time_origin

    N = len(ref_dat)
    fs = 1.0 / time_increment  # Sampling frequency

    # Time array
    t = time_origin + np.arange(N) * time_increment

    # Extract fundamental frequency from reference data
    fundamental_freq = extract_fundamental_frequency(ref_dat, time_increment)
    print(f"Fundamental Frequency: {fundamental_freq:.2f} Hz")

    # Generate reference cosine and sine signals with zero phase
    cos_ref, sin_ref = generate_reference_signals(fundamental_freq, N, time_increment)

    # Demodulate the acquired data
    I = aqu_dat * cos_ref  # noqa: E741
    Q = aqu_dat * sin_ref

    # Apply low-pass filter to I and Q
    I_filtered = low_pass_filter(I, low_pass_cutoff, fs, order=filter_order)
    Q_filtered = low_pass_filter(Q, low_pass_cutoff, fs, order=filter_order)

    # plt.plot(I, label="I")
    # plt.plot(Q, label="Q")
    # plt.plot(I_filtered, label="I_filtered")
    # plt.plot(Q_filtered, label="Q_filtered")
    # plt.legend()
    # plt.show()

    # Compute amplitude and phase
    amplitude = (
        np.sqrt(I_filtered**2 + Q_filtered**2) * 2
    )  # Multiply by 2 due to demodulation scaling
    phase = np.arctan2(Q_filtered, I_filtered)

    # Correct phase offset due to zero phase reference
    ref_phase = np.arctan2(np.mean(ref_dat * sin_ref), np.mean(ref_dat * cos_ref))
    phase_corrected = phase - ref_phase

    # Unwrap phase to prevent discontinuities
    phase_corrected = phase_corrected

    return {
        "time": t,
        "amplitude": amplitude,
        "phase": phase_corrected,
        "fundamental_freq": fundamental_freq,
    }
