# Freqlayer

## Overview
RyugeLotus Audio Scalpel is a precision, memory-based audio frequency isolation tool designed for targeted spectral analysis and real-time bandpass filtering. It operates entirely in RAM to ensure zero disk fragmentation and immediate auditory feedback.

Standard commercial equalizers and audio filters introduce roll-off curves and phase smoothing to prioritize acoustic comfort. 
It bypasses traditional filtering aesthetics by directly manipulating FFT bins.
Frequencies outside the defined threshold are mathematically eliminated with an absolute brickwall cut. There is zero easing, roll-off, or acoustic smoothing applied, ensuring raw, surgical isolation of the targeted spectrum without accommodating human auditory comfort.

## Core Features
* **Playback Control**: Press `Space` to toggle Play / Pause.
* **Frequency Adjustment**: Drag the boundary lines with the mouse to dynamically adjust the lower and upper frequency limits.
* **Instant Region Creation**: Hold `Ctrl` and drag the mouse across the graphical interface to instantly draw and isolate a specific listening region.
* **Tri-Tier Spectral Ruler**: The visual interface provides three distinct reference scales for absolute precision:
    * **Octaves / Notes** (e.g., C1, C4, C7)
    * **Frequency Bands** (e.g., SUB, BASS, HIGH MID)
    * **Hertz** (e.g., 20, 1k, 10k)

## Requirements & Limitations
* **Supported Formats**: On Windows platforms, this application strictly supports **.WAV** audio files only.
