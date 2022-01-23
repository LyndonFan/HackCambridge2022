import asyncio


async def func():
    print('func')
    await asyncio.sleep(1)
    print('func2')
    return 42


async def main():
    print('main')
    response = await func()
    print(response)

if __name__ == '__main__':
    asyncio.run(main())
