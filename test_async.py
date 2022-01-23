import asyncio
import pyaudio
import wave
from deepgram import Deepgram
from waiting import wait

from test_deepgram_stream import PATH_TO_FILE

with open(".env", "r") as f:
    DEEPGRAM_API_KEY = f.read().strip().split("=")[1]

chunk = 1024  # Record in chunks of 1024 samples
sample_format = pyaudio.paInt16  # 16 bits per sample
channels = 1
fs = 44100  # Record at 44100 samples per second

p = pyaudio.PyAudio()  # Create an interface to PortAudio

print('Recording')

stream = p.open(format=sample_format,
                channels=channels,
                rate=fs,
                frames_per_buffer=chunk,
                input=True)

seconds = 5


async def save_to_file(frames, filename):
    async with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))


async def record_audio(task_id=0):
    frames = []
    for _ in range(int(fs / chunk * seconds)):
        data = stream.read(chunk)
        frames.append(data)
    save_to_file(frames, f"output{task_id}.wav")


N_PROCESSES = 3

all_responses = {i: [] for i in range(N_PROCESSES)}
process_ready = {i: i > 0 for i in range(N_PROCESSES)}


async def get_transcript(task_id=0):
    PATH_TO_FILE = f"output{task_id}.wav"
    # Initializes the Deepgram SDK
    dg_client = Deepgram(DEEPGRAM_API_KEY)
    # Creates a websocket connection to Deepgram
    try:
        socket = await dg_client.transcription.live({'punctuate': True})
    except Exception as e:
        print(f'Could not open socket: {e}')
        return
    # Handle sending audio to the socket

    async def process_audio(connection):
        # Open the file
        with open(PATH_TO_FILE, 'rb') as audio:
            # Chunk up the audio to send
            CHUNK_SIZE_BYTES = 8192
            CHUNK_RATE_SEC = 0.001
            chunk = audio.read(CHUNK_SIZE_BYTES)
            print(type(chunk))
            while chunk:
                connection.send(chunk)
                await asyncio.sleep(CHUNK_RATE_SEC)
                chunk = audio.read(CHUNK_SIZE_BYTES)
        # Indicate that we've finished sending data
        await connection.finish()

    # Listen for the connection to close
    socket.register_handler(socket.event.CLOSE, lambda c: print(
        f'Connection closed with code {c}.'))
    # Print incoming transcription objects
    socket.register_handler(socket.event.TRANSCRIPT_RECEIVED,
                            lambda response: all_responses[task_id].append(response))

    # Send the audio to the socket
    await process_audio(socket)


async def task(task_id=0):
    print(f"Starting task {task_id}")
    process_ready[task_id] = False
    record_audio()
    process_ready[task_id] = True
    all_responses[task_id] = []
    asyncio.run(get_transcript(task_id))
    response = all_responses[task_id][:-1]
    response.sort(key=lambda dct: (dct['start'], dct['duration']))
    for r in response:
        words = r['channel']['alternatives'][0]['words']
        if len(words) > 0:
            print(f'{r["start"]:.3f} - {r["start"] + r["duration"]:.3f}: {words}')
    wait(lambda: process_ready[(task_id-1) %
         N_PROCESSES], timeout_seconds=seconds)
    task(task_id)


async def task0():
    task(0)


async def task1():
    asyncio.sleep(seconds)
    task(1)


async def task2():
    asyncio.sleep(seconds*2)
    task(2)


async def main():
    await asyncio.gather(task0(), task1(), task2())

asyncio.run(main())
