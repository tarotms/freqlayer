# freqlayer

A lightweight, hardware-inspired desktop utility for real-time audio frequency isolation, surgical EQ inspection, and spectral energy analysis.

---

## Overview

**freqlayer** allows audio engineers, producers, and sound designers to isolate and audition specific frequency bands in real time. Built with a Weighted Overlap-Add (WOLA) synthesis engine and raised-cosine filtering, it prevents clicks, pops, and time-domain aliasing when sweeping filters across the spectrum.

---

## Features

* **Artifact-Free Filtering**: Weighted Overlap-Add (WOLA) architecture with square-root Hann windowing ensures continuous phase and click-free real-time audio playback.
* **Variable Feathering (Bandwidth Rolloff)**:
  * Continuous rolloff adjustment from $0.0001\text{ Hz}$ to $2000\text{ Hz}$ using raised-cosine transitions.
  * Prevents brickwall truncation and Gibbs ringing artifacts.
  * **Middle-click** the knob to quickly reset to default ($50.0\text{ Hz}$).
* **High-Resolution Thermal Spectrogram**:
  * 16,384-point analysis FFT providing fine resolution in the sub-bass and low-frequency range ($20\text{ Hz} - 200\text{ Hz}$).
  * Logarithmically interpolated real-time energy curve with thermal gradient rendering.
  * Inactive/attenuated frequency regions are smoothly attenuated to dark gray using alpha-mask blending.
* **Acoustic Engineering Band Bar**:
  * Direct access to standard frequency ranges: **SUB**, **BASS**, **LOW-MID**, **MID**, **HIGH-MID**, **PRS** (Presence), and **TREBLE**.
  * Hover illumination, single-click band selection, and multi-band click-and-drag range expansion.
* **Format Support**: Drag-and-drop playback for `.wav`, `.mp3`, `.flac`, `.aiff`, and `.ogg` files.
* **Interactive Timeline**: Draggable scrub bar with discrete elapsed and total duration readouts (`MM:SS / MM:SS`).

---

## Controls

| Action | Input |
| :--- | :--- |
| **Play / Pause** | `Spacebar` |
| **Import Audio** | Drag & drop an audio file onto the application window |
| **Adjust Frequency Bounds** | Click and drag the left or right turquoise cursor lines |
| **Pan Filter Band** | Click and drag horizontally inside the active passband |
| **Select Single Band** | Click any top band button (`SUB` through `TREBLE`) |
| **Select Multiple Bands** | Click and drag across the top band buttons |
| **Adjust Feathering** | Click and drag vertically on the `FEATHER` knob |
| **Reset Feathering** | Middle-click the `FEATHER` knob ($50\text{ Hz}$) |
| **Seek Playback** | Click or drag on the bottom progress bar |

---

## Setup & Running

### Requirements
* Python 3.10+
* PortAudio

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/tarotms/freqlayer.git
   cd freqlayer
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv .env
   .env\Scripts\activate

   # Linux / macOS
   python3 -m venv .env
   source .env/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install PyQt6 soundfile sounddevice numpy miniaudio
   ```

4. Launch the application:
   ```bash
   python main.py
   ```

---

## Building Standalone Executable (Windows)

To compile a self-contained, single-file executable (`~45 MB`) with dependencies pruned:

```bash
# Ensure PyInstaller is installed in the local environment
.env\Scripts\python.exe -m pip install pyinstaller

# Build portable executable
.env\Scripts\python.exe -m PyInstaller --noconfirm --clean --noconsole ^
  --name "freqlayer 1.1" ^
  --icon="icon.ico" ^
  --add-data "icon.ico;." ^
  --collect-binaries sounddevice ^
  --collect-binaries soundfile ^
  --collect-all miniaudio ^
  --exclude-module torch ^
  --exclude-module torchvision ^
  --exclude-module torchaudio ^
  --exclude-module cuda ^
  --exclude-module PyQt6.QtWebEngineCore ^
  --exclude-module PyQt6.QtWebEngineWidgets ^
  --exclude-module PyQt6.QtQml ^
  --exclude-module PyQt6.QtQuick ^
  --exclude-module PyQt6.Qt3DCore ^
  --onefile main.py
```

The output file will be generated in `dist/freqlayer 1.1.exe`.

---

## License

This project is licensed under the [MIT License](LICENSE).
