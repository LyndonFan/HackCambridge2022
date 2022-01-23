import asyncio
import aiofiles
import pyaudio
import wave
from deepgram import Deepgram
from waiting import wait
from multiprocessing import Process, Lock
import sys

with open(".env", "r") as f:
    DEEPGRAM_API_KEY = f.read().strip().split("=")[1]

chunk = 1024  # Record in chunks of 1024 samples
sample_format = pyaudio.paInt16  # 16 bits per sample
channels = 1
fs = 44100  # Record at 44100 samples per second

p = pyaudio.PyAudio()  # Create an interface to PortAudio

stream = p.open(format=sample_format,
                channels=channels,
                rate=fs,
                frames_per_buffer=chunk,
                input=True)

seconds = 5


def save_to_file(frames, filename):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))


def record_audio(task_id=0):
    frames = []
    for _ in range(int(fs / chunk * seconds)):
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
    save_to_file(frames, f"output{task_id}.wav")


N_PROCESSES = 2
for i in range(N_PROCESSES):
    with open(f"output{i}.wav", "wb+") as f:
        f.write(b"")

dg_client = Deepgram(DEEPGRAM_API_KEY)

CHUNK_SIZE_BYTES = 8192
CHUNK_RATE_SEC = 0.001


async def get_transcript(task_id=0):
    PATH_TO_FILE = f"output{task_id}.wav"
    responses = []
    # Initializes the Deepgram SDK
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
            chunk = audio.read(CHUNK_SIZE_BYTES)
            print(type(chunk))
            count_chunks = 0
            assert connection.open
            while chunk:
                connection.send(chunk)
                print(f"Sent chunk {count_chunks}")
                sys.stdout.flush()
                await asyncio.sleep(CHUNK_RATE_SEC)
                chunk = audio.read(CHUNK_SIZE_BYTES)
                count_chunks += 1
        # Indicate that we've finished sending data
        await connection.finish()

    def handle(r):
        print(f"Got response {len(responses)}")
        sys.stdout.flush()
        responses.append(r)

    # Listen for the connection to close
    socket.register_handler(socket.event.CLOSE, lambda c: print(
        f'Connection closed with code {c}.'))
    # Print incoming transcription objects
    socket.register_handler(
        socket.event.TRANSCRIPT_RECEIVED, handle)

    # Send the audio to the socket
    await process_audio(socket)

    del socket
    return responses


def task(l, fl, task_id=0):
    l.acquire()
    print(f"Lock L acquired for recording {task_id}")
    fl[task_id].acquire()
    print(f"FLock {task_id} acquired for recording")
    print(f"Task {task_id} recording")
    record_audio()
    fl[task_id].release()
    print(f"FLock {task_id} released from recording")
    l.release()
    print(f"Lock L released from recording {task_id}")
    # print(f"Task {task_id} sending transcript")
    # response = asyncio.run(get_transcript(task_id))
    # response = response[:-1]
    # response.sort(key=lambda dct: (dct['start'], dct['duration']))
    # for r in response:
    #     words = r['channel']['alternatives'][0]['words']
    #     if len(words) > 0:
    #         print(f'{r["start"]:.3f} - {r["start"] + r["duration"]:.3f}: {words}')

    async def holder():
        await asyncio.sleep(3)
    asyncio.run(holder())
    task(l, fl, task_id)


def transcript_task(l, fl, current_id=0, initial=True):
    if initial:
        async def holder():
            await asyncio.sleep(seconds*1.5)
        asyncio.run(holder())
    fl[current_id].acquire()
    print(f"FLock {current_id} acquired for transcript")
    print(f"Sending transcript for {current_id}")
    response = asyncio.run(get_transcript(current_id))
    fl[current_id].release()
    response = response[:-1]
    response.sort(key=lambda dct: (dct['start'], dct['duration']))
    for r in response:
        words = r['channel']['alternatives'][0]['words']
        if len(words) > 0:
            print(f'{r["start"]:.3f} - {r["start"] + r["duration"]:.3f}: {words}')
    print(f"FLock {current_id} released from transcript")
    transcript_task(l, fl, (current_id+1) % N_PROCESSES, False)


def main():
    lock = Lock()
    flocks = [Lock() for i in range(N_PROCESSES)]
    processes = [Process(target=task, args=(lock, flocks, i))
                 for i in range(N_PROCESSES)]
    processes.append(Process(target=transcript_task, args=(lock, flocks)))
    for p in processes:
        p.start()
    for p in processes:
        p.join()


if __name__ == '__main__':
    main()
