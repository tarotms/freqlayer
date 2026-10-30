import io
import numpy as np
import sounddevice as sd
import soundfile as sf
from PyQt6.QtCore import QObject, pyqtSignal

class AudioEngine(QObject):
    progress_updated = pyqtSignal(float, float, float)
    spectrum_updated = pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self):
        super().__init__()
        self.filepath = None
        self.data = None
        self.sr = 44100
        self.current_frame = 0
        self.stream = None
        self.is_playing = False
        
        self.target_min_freq = 100.0
        self.target_max_freq = 2000.0
        self.target_feather_hz = 50.0
        
        self.cur_min_freq = 100.0
        self.cur_max_freq = 2000.0
        self.cur_feather_hz = 50.0

        # WOLA 架构：75% 重叠抑制时域混叠与块截断爆音
        self.n_fft = 4096
        self.hop_size = 1024
        self.window = np.sqrt(np.hanning(self.n_fft)).astype(np.float32)
        self.cola_factor = float(np.sum(self.window[::self.hop_size] ** 2))
        
        self.out_buffer = np.zeros((self.n_fft, 2), dtype=np.float32)

        # 16384 点独立 FFT 分析
        self.analysis_size = 16384
        self.analysis_window = np.hanning(self.analysis_size).astype(np.float32)
        self.analysis_buf = np.zeros(self.analysis_size, dtype=np.float32)

    def load_file(self, filepath):
        self.filepath = filepath
        data = None
        sr = 44100

        try:
            with open(filepath, 'rb') as f:
                file_bytes = f.read()
            data, sr = sf.read(io.BytesIO(file_bytes), dtype='float32')
        except Exception:
            try:
                import miniaudio
                decoded = miniaudio.decode(file_bytes, nchannels=2, sample_rate=44100, output_format=miniaudio.SampleFormat.FLOAT32)
                data = np.frombuffer(decoded.samples, dtype=np.float32).reshape(-1, 2)
                sr = decoded.sample_rate
            except Exception:
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(filepath)
                    sr = audio.frame_rate
                    samples = np.array(audio.get_array_of_samples())
                    if audio.sample_width == 2:
                        samples = samples.astype(np.float32) / 32768.0
                    elif audio.sample_width == 4:
                        samples = samples.astype(np.float32) / 2147483648.0
                    if audio.channels == 2:
                        data = samples.reshape(-1, 2)
                    else:
                        data = np.column_stack((samples, samples))
                except Exception:
                    self.data = None
                    return

        if data.ndim == 1:
            data = np.column_stack((data, data))

        self.data = np.ascontiguousarray(data, dtype=np.float32)
        self.sr = sr
        self.current_frame = 0
        self.out_buffer.fill(0)
        self.analysis_buf.fill(0)

        if self.stream:
            self.stream.stop()
            self.stream.close()

        self.stream = sd.OutputStream(
            samplerate=self.sr,
            channels=2,
            blocksize=self.hop_size,
            latency='high',
            callback=self._audio_callback
        )
        self.play()

    def set_filter(self, min_freq, max_freq, feather_hz=None):
        self.target_min_freq = float(min_freq)
        self.target_max_freq = float(max_freq)
        if feather_hz is not None:
            self.target_feather_hz = max(0.0001, float(feather_hz))

    def seek(self, ratio):
        if self.data is None:
            return
        target_frame = int(ratio * len(self.data))
        self.current_frame = target_frame - (target_frame % self.hop_size)
        self.out_buffer.fill(0)
        self.analysis_buf.fill(0)

    def play(self):
        if self.stream and not self.is_playing:
            self.stream.start()
            self.is_playing = True

    def pause(self):
        if self.stream and self.is_playing:
            self.stream.stop()
            self.is_playing = False

    def _audio_callback(self, outdata, frames, time_info, status):
        if self.data is None or self.current_frame + self.n_fft > len(self.data):
            outdata.fill(0)
            self.is_playing = False
            raise sd.CallbackStop()

        smooth_coeff = 0.25
        self.cur_min_freq += (self.target_min_freq - self.cur_min_freq) * smooth_coeff
        self.cur_max_freq += (self.target_max_freq - self.cur_max_freq) * smooth_coeff
        self.cur_feather_hz += (self.target_feather_hz - self.cur_feather_hz) * smooth_coeff

        chunk = self.data[self.current_frame : self.current_frame + self.n_fft]
        
        windowed = chunk * self.window[:, np.newaxis]
        fft_data = np.fft.rfft(windowed, axis=0)
        freqs_filter = np.fft.rfftfreq(self.n_fft, 1.0 / self.sr)

        f_low = self.cur_min_freq
        f_high = self.cur_max_freq
        feather = max(0.0001, self.cur_feather_hz)

        curve = np.zeros_like(freqs_filter, dtype=np.float32)
        pass_mask = (freqs_filter >= f_low) & (freqs_filter <= f_high)
        curve[pass_mask] = 1.0

        low_feather_mask = (freqs_filter >= (f_low - feather)) & (freqs_filter < f_low)
        if np.any(low_feather_mask):
            phase = (freqs_filter[low_feather_mask] - (f_low - feather)) / feather
            curve[low_feather_mask] = 0.5 * (1.0 - np.cos(np.pi * phase))

        high_feather_mask = (freqs_filter > f_high) & (freqs_filter <= (f_high + feather))
        if np.any(high_feather_mask):
            phase = (freqs_filter[high_feather_mask] - f_high) / feather
            curve[high_feather_mask] = 0.5 * (1.0 + np.cos(np.pi * phase))

        fft_data *= curve[:, np.newaxis]

        filtered_chunk = np.fft.irfft(fft_data, n=self.n_fft, axis=0)
        filtered_chunk *= self.window[:, np.newaxis]

        self.out_buffer += filtered_chunk
        outdata[:] = self.out_buffer[:self.hop_size] / self.cola_factor
        
        self.out_buffer = np.roll(self.out_buffer, -self.hop_size, axis=0)
        self.out_buffer[-self.hop_size:] = 0.0

        mono_block = 0.5 * (chunk[:self.hop_size, 0] + chunk[:self.hop_size, 1])
        self.analysis_buf = np.roll(self.analysis_buf, -self.hop_size)
        self.analysis_buf[-self.hop_size:] = mono_block

        spec_fft = np.fft.rfft(self.analysis_buf * self.analysis_window)
        spec_freqs = np.fft.rfftfreq(self.analysis_size, 1.0 / self.sr)
        spec_mag = np.abs(spec_fft) / (self.analysis_size / 2.0)
        spec_db = 20.0 * np.log10(np.maximum(spec_mag, 1e-5))

        self.spectrum_updated.emit(spec_freqs, spec_db)

        self.current_frame += self.hop_size
        current_sec = self.current_frame / float(self.sr)
        total_sec = len(self.data) / float(self.sr)
        ratio = self.current_frame / len(self.data)
        self.progress_updated.emit(ratio, current_sec, total_sec)