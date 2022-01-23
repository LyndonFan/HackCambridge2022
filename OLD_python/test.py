import asyncio
import asyncio
from multiprocessing import Process, Lock
import time


async def get_script(i):
    print(f'Starting script {i}')
    await asyncio.sleep(1)
    print(f'Finished script {i}')
    return i


def task(l, i):
    print(f'Starting task {i}')
    l.acquire()
    print(f'Task {i} acquired lock')
    time.sleep(3)
    l.release()
    print(f'Task {i} released lock, starting less important task')
    res = asyncio.run(get_script(i))
    print(f'Finished task {i}: {res}')
    task(l, i)


N_PROCESSES = 2


def main():
    lock = Lock()
    processes = [Process(target=task, args=(lock, i))
                 for i in range(N_PROCESSES)]
    for i in range(N_PROCESSES):
        processes[i].start()
    for i in range(N_PROCESSES):
        processes[i].join()


if __name__ == '__main__':
    main()
