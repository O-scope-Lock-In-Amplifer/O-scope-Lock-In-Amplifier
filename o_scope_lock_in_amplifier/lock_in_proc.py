"""
lock_in_amplifier.py

A Python module to perform lock-in amplification on acquisition data using FFT.
It extracts the fundamental frequency from the reference data, demodulates the
acquired data to obtain amplitude and phase, applies a low-pass filter.

This module is designed with a clean API suitable for integration with a GUI.

Author: Your Name
Date: YYYY-MM-DD
"""

import time

import numpy as np
from matplotlib import pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.signal import butter, filtfilt

from o_scope_lock_in_amplifier.oscilloscope_utils import AcquisitionData


def extract_fundamental_frequency(ref_dat: np.ndarray, time_increment: float) -> float:
    """
    Extracts the fundamental frequency from the reference data using FFT.

    Parameters:
        ref_dat (np.ndarray): Reference voltage data.
        time_increment (float): Time increment between samples (s).

    Returns:
        float: Fundamental frequency (Hz).
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
    fundamental_freq = freqs[peak_idx]

    return fundamental_freq


def generate_reference_signals(
    freq: float, N: int, time_increment: float
) -> (np.ndarray, np.ndarray):
    """
    Generates cosine and sine reference signals at the given frequency with zero phase.

    Parameters:
        freq (float): Frequency of the reference signals (Hz).
        N (int): Number of samples.
        time_increment (float): Time increment between samples (s).

    Returns:
        tuple: (cosine_signal, sine_signal)
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

    Parameters:
        signal (np.ndarray): Input signal.
        cutoff (float): Cutoff frequency of the filter (Hz).
        fs (float): Sampling frequency (Hz).
        order (int): Order of the filter.

    Returns:
        np.ndarray: Filtered signal.
    """
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    # Design Butterworth filter
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    # Apply filter with padding to reduce edge artifacts
    padlen = min(3 * (max(len(a), len(b)) - 1), len(signal) - 1)
    filtered_signal = filtfilt(b, a, signal, padlen=padlen)
    return filtered_signal


def perform_lock_in(
    ampl_data: AcquisitionData, low_pass_cutoff: float, filter_order: int = 5
) -> dict:
    """
    Performs lock-in amplification on the provided acquisition data.

    Parameters:
        ampl_data (AcquisitionData): The acquisition data.
        low_pass_cutoff (float): Cutoff frequency for the low-pass filter (Hz).
        filter_order (int): Order of the Butterworth low-pass filter.

    Returns:
        dict: Contains filtered amplitude and phase signals, and the recovered output.
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
    I = aqu_dat * cos_ref
    Q = aqu_dat * sin_ref

    # Apply low-pass filter to I and Q
    I_filtered = low_pass_filter(I, low_pass_cutoff, fs, order=filter_order)
    Q_filtered = low_pass_filter(Q, low_pass_cutoff, fs, order=filter_order)

    # Compute amplitude and phase
    amplitude = (
        np.sqrt(I_filtered**2 + Q_filtered**2) * 2
    )  # Multiply by 2 due to demodulation scaling
    phase = np.arctan2(Q_filtered, I_filtered)

    # Correct phase offset due to zero phase reference
    # Since we set the reference phase to zero, the recovered phase might have an offset
    # Compute the phase difference between the actual reference data and the zero-phase cosine reference
    ref_phase = np.arctan2(np.mean(ref_dat * sin_ref), np.mean(ref_dat * cos_ref))
    phase_corrected = phase - ref_phase

    # Unwrap phase to prevent discontinuities
    phase_corrected = np.unwrap(phase_corrected)

    return {
        "time": t,
        "amplitude": amplitude,
        "phase": phase_corrected,
        "fundamental_freq": fundamental_freq,
    }


# Plotting functions
def plot_reference_signal(t: np.ndarray, ref_dat: np.ndarray, cos_ref: np.ndarray):
    """
    Plots the reference data and cosine reference signal.

    Parameters:
        t (np.ndarray): Time array.
        ref_dat (np.ndarray): Reference voltage data.
        cos_ref (np.ndarray): Cosine reference signal.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(t, ref_dat, label="Reference Data")
    plt.plot(t, cos_ref, label="Cosine Reference Signal", alpha=0.7)
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.title("Reference Data and Cosine Reference Signal")
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_acquired_data(t: np.ndarray, aqu_dat: np.ndarray):
    """
    Plots the acquired data.

    Parameters:
        t (np.ndarray): Time array.
        aqu_dat (np.ndarray): Acquired voltage data.
    """
    plt.figure(figsize=(12, 4))
    plt.plot(t, aqu_dat, label="Acquired Data", alpha=0.5)
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.title("Acquired Data")
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_recovered_signals(t: np.ndarray, amplitude: np.ndarray, phase: np.ndarray):
    """
    Plots the recovered amplitude and phase signals.

    Parameters:
        t (np.ndarray): Time array.
        amplitude (np.ndarray): Recovered amplitude.
        phase (np.ndarray): Recovered phase.
    """
    # Plot recovered amplitude
    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.plot(t, amplitude, label="Recovered Amplitude", color="m")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (V)")
    plt.title("Recovered Amplitude Signal")
    plt.legend()
    plt.grid(True)

    # Plot recovered phase
    plt.subplot(2, 1, 2)
    plt.plot(t, np.degrees(phase), label="Recovered Phase (Corrected)", color="c")
    plt.xlabel("Time (s)")
    plt.ylabel("Phase (degrees)")
    plt.title("Recovered Phase Signal")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# Example usage
if __name__ == "__main__":
    from o_scope_lock_in_amplifier import DS1054z

    s = DS1054z()
    time.sleep(0.25)
    s.setup_capture(memory_depth=6_000_000)
    time.sleep(0.25)
    acquisition_data = s.get_data()

    # Perform lock-in amplification
    results = perform_lock_in(
        ampl_data=acquisition_data,
        low_pass_cutoff=5.0,  # Cutoff frequency in Hz
        filter_order=4,
    )

    # Unpack results
    t = results["time"]
    amplitude = results["amplitude"]
    phase = results["phase"]
    fundamental_freq = results["fundamental_freq"]

    # Generate reference signals for plotting
    N = len(t)
    time_increment = t[1] - t[0]
    _, sin_ref = generate_reference_signals(fundamental_freq, N, time_increment)

    # Plotting
    plot_reference_signal(t, acquisition_data.ref_dat, sin_ref)
    plot_acquired_data(t, acquisition_data.aqu_dat)
    plot_recovered_signals(t, amplitude, phase)

    # Print recovered amplitude and phase at the end of the data
    print(f"Recovered Amplitude: {np.mean(amplitude[len(amplitude)//2:])} V")
    print(f"Recovered Phase: {np.mean(phase[len(phase)//2:]):.3f} degrees")
