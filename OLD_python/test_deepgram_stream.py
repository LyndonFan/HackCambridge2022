from deepgram import Deepgram
import asyncio
import time

with open(".env", "r") as f:
    DEEPGRAM_API_KEY = f.read().strip().split("=")[1]

PATH_TO_FILE = 'test.m4a'


def get_transcription(PATH_TO_FILE):
    responses = []

    async def main():
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
                                lambda response: responses.append(response))

        # Send the audio to the socket
        await process_audio(socket)

    asyncio.run(main())
    responses = responses[:-1]
    responses.sort(key=lambda dct: (dct['start'], dct['duration']))
    for r in responses:
        words = r['channel']['alternatives'][0]['words']
        if len(words) > 0:
            print(f'{r["start"]:.3f} - {r["start"] + r["duration"]:.3f}: {words}')


time.sleep(6)
while True:
    with open("index.txt", "r") as f:
        index = int(f.read())
    PATH_TO_FILE = f"output{index}.wav"
    get_transcription(PATH_TO_FILE)
    time.sleep(5)
