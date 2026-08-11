import numpy as np
import soundfile as sf
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal
import io

class AudioEngine(QObject):
    progress_updated = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.filepath = None
        self.data = None
        self.sr = 44100
        self.current_frame = 0
        self.stream = None
        self.is_playing = False
        
        self.min_freq = 100
        self.max_freq = 1000
        
        self.chunk_size = 4096
        self.overlap = self.chunk_size // 2
        self.window = np.hanning(self.chunk_size)
        self.buffer = np.zeros((self.overlap, 2), dtype=np.float32)

    def load_file(self, filepath):
        try:
            self.filepath = filepath
            with open(filepath, 'rb') as f:
                file_bytes = f.read()
            
            self.data, self.sr = sf.read(io.BytesIO(file_bytes), dtype='float32')
            
            if self.data.ndim == 1:
                self.data = np.column_stack((self.data, self.data))
                
            self.current_frame = 0
            self.buffer.fill(0)
            
            if self.stream:
                self.stream.stop()
                self.stream.close()
                
            self.stream = sd.OutputStream(
                samplerate=self.sr,
                channels=2,
                blocksize=self.overlap,
                callback=self._audio_callback
            )
            self.play()
        except Exception:
            self.data = None

    def set_filter(self, min_freq, max_freq):
        self.min_freq = min_freq
        self.max_freq = max_freq

    def seek(self, ratio):
        if self.data is None:
            return
        target_frame = int(ratio * len(self.data))
        self.current_frame = target_frame - (target_frame % self.overlap)
        self.buffer.fill(0)

    def play(self):
        if self.stream and not self.is_playing:
            self.stream.start()
            self.is_playing = True

    def pause(self):
        if self.stream and self.is_playing:
            self.stream.stop()
            self.is_playing = False

    def _audio_callback(self, outdata, frames, time, status):
        if self.data is None or self.current_frame + self.chunk_size > len(self.data):
            outdata.fill(0)
            self.is_playing = False
            raise sd.CallbackStop()

        chunk = self.data[self.current_frame : self.current_frame + self.chunk_size]
        windowed = chunk * self.window[:, np.newaxis]
        
        fft_data = np.fft.rfft(windowed, axis=0)
        freqs = np.fft.rfftfreq(self.chunk_size, 1 / self.sr)
        
        mask = (freqs >= self.min_freq) & (freqs <= self.max_freq)
        fft_data[~mask] = 0
        
        filtered_chunk = np.fft.irfft(fft_data, n=self.chunk_size, axis=0)
        
        out = filtered_chunk[:self.overlap] + self.buffer
        self.buffer = filtered_chunk[self.overlap:]
        
        outdata[:] = out
        self.current_frame += self.overlap
        
        ratio = self.current_frame / len(self.data)
        self.progress_updated.emit(ratio)