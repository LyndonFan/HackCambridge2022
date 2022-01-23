import pyaudio
import wave
import time

chunk = 1024  # Record in chunks of 1024 samples
sample_format = pyaudio.paInt16  # 16 bits per sample
channels = 1
fs = 44100  # Record at 44100 samples per second
filename = "output.wav"

p = pyaudio.PyAudio()  # Create an interface to PortAudio

print('Recording')

stream = p.open(format=sample_format,
                channels=channels,
                rate=fs,
                frames_per_buffer=chunk,
                input=True)

frames = []  # Initialize array to store frames

seconds = 5

count = 0

# takes negligible amount of time


def save_to_file(frames, filename):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(sample_format))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()


while True:
    try:
        start_time = time.perf_counter()
        for _ in range(int(fs / chunk * seconds)):
            data = stream.read(chunk)
            frames.append(data)
        done_recording = time.perf_counter()
        save_to_file(frames, f"output{count}.wav")
        done_saving = time.perf_counter()
        print(f"Recording time: {done_recording - start_time}")
        print(f"Saving time: {done_saving - done_recording}")
        with open("index.txt", "w") as f:
            f.write(str(count))
        count += 1
        frames = []
    except:
        break

stream.stop_stream()
stream.close()
# Terminate the PortAudio interface
p.terminate()

print('Finished recording')

# Save the recorded data as a WAV file
wf = wave.open(filename, 'wb')
wf.setnchannels(channels)
wf.setsampwidth(p.get_sample_size(sample_format))
wf.setframerate(fs)
wf.writeframes(b''.join(frames))
wf.close()
