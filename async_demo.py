import asyncio
from contextlib import suppress


class Periodic:
    def __init__(self, func, time):
        self.func = func
        self.time = time
        self.is_started = False
        self._task = None

    async def start(self):
        if not self.is_started:
            self.is_started = True
            # Start task to call func periodically:
            self._task = asyncio.ensure_future(self._run())

    async def stop(self):
        if self.is_started:
            self.is_started = False
            # Stop task and await it stopped:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def _run(self):
        while True:
            await asyncio.sleep(self.time)
            self.func()


async def main():
    p = Periodic(lambda: print('test'), 1)
    try:
        print('Start')
        await p.start()
        await asyncio.sleep(3.1)

        print('Stop')
        await p.stop()
        await asyncio.sleep(3.1)

        print('Start')
        await p.start()
        await asyncio.sleep(3.1)
    finally:
        await p.stop()  # we should stop task finally


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
