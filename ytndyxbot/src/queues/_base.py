import asyncio

from pyrogram.types import Message

from ..helpers import _message


class QueueItem:
    def __init__(self, priority, task, future, msg=None, url=None):
        self.priority = priority
        self.task = task
        self.future = future
        self.msg = msg
        self.url = url

    def __lt__(self, other):
        return self.priority < other.priority


class DownloadQueue:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DownloadQueue, cls).__new__(cls)
            cls._instance.dl_queue = asyncio.PriorityQueue()
            cls._instance.Semaphore = asyncio.Semaphore(4)
        return cls._instance

    async def add(
        self, message: Message, priority: int, task: asyncio.Task, url: str
    ) -> asyncio.Future:
        future = asyncio.Future()
        msg = await _message.reply_text(message, f"🚀 Queue download\n{url}")
        item = QueueItem(priority, task, future, msg, url)
        await self.dl_queue.put(item)
        return future

    async def start(self) -> None:
        while True:
            asyncio.create_task(self.process_dl())
            await asyncio.sleep(1)

    async def process_dl(self) -> None:
        async with self.Semaphore:
            if not self.dl_queue.empty():
                item = await self.dl_queue.get()
                try:
                    await _message.edit_text(item.msg, f"🚀 Downloading\n{item.url}")
                    result = await item.task
                    item.future.set_result(result)
                except Exception as e:
                    if not item.future.cancelled():
                        item.future.set_exception(e)
                finally:
                    await item.msg.delete()
                    self.dl_queue.task_done()


class AfterDownloadQueue:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AfterDownloadQueue, cls).__new__(cls)
            cls._instance.after_dl_queue = asyncio.PriorityQueue()
            cls._instance.semaphore = asyncio.Semaphore(1)
        return cls._instance

    async def add(
        self, message: Message, priority: int, task: asyncio.Task, url: str
    ) -> asyncio.Future:
        future = asyncio.Future()
        msg = await _message.reply_text(
            message, f"🎞️ Queued extraction of metadata, thumbnails...\n{url}"
        )
        item = QueueItem(priority, task, future, msg, url)
        await self.after_dl_queue.put(item)
        return future

    async def start(self) -> None:
        while True:
            async with self.semaphore:
                if not self.after_dl_queue.empty():
                    item = await self.after_dl_queue.get()
                    try:
                        await _message.edit_text(
                            item.msg,
                            f"🎞️ Extracting metadata, thumbnails...\n{item.url}",
                        )
                        result = await item.task
                        item.future.set_result(result)
                    except Exception as e:
                        if not item.future.cancelled():
                            item.future.set_exception(e)
                    finally:
                        await item.msg.delete()
                        self.after_dl_queue.task_done()
            await asyncio.sleep(1)


class SenderMediaQueue:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SenderMediaQueue, cls).__new__(cls)
            cls._instance.sender_media_queue = asyncio.PriorityQueue()
            cls._instance.semaphore = asyncio.Semaphore(1)
        return cls._instance

    async def add(self, priority: int, task: asyncio.Task) -> asyncio.Future:
        future = asyncio.Future()
        item = QueueItem(priority, task, future)
        await self.sender_media_queue.put(item)
        return future

    async def start(self) -> None:
        while True:
            async with self.semaphore:
                if not self.sender_media_queue.empty():
                    item = await self.sender_media_queue.get()
                    try:
                        result = await item.task
                        item.future.set_result(result)
                    except Exception as e:
                        if not item.future.cancelled():
                            item.future.set_exception(e)
                    finally:
                        self.sender_media_queue.task_done()
            await asyncio.sleep(1)
