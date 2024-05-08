import asyncio
import websockets
from collections import namedtuple
import math
import datetime
import random
from string import ascii_letters
import pandas


class TestCase:
    rooms = {
        1: []
    }

    stats_cls = namedtuple(
        "Stat", ['ttr', 'ttc', 'b_send', 'b_recv', 'time', 'user', 'chat'])

    def __init__(self,
                 users: int,
                 test_time_sec: int):
        self.users = users
        self.test_time_sec = test_time_sec
        self._set_loading(users)
        self.begin_time = datetime.datetime.now()
        self.stats = []

    def _set_loading(self, devices: int):
        chats_range = [i for i in range(1, math.ceil(devices / 2))]
        users_range = [i for i in range(devices, 1, -1)]

        for chat_id in chats_range:
            if chat_id in self.rooms:
                self.rooms[chat_id].append(users_range.pop())
            else:
                self.rooms[chat_id] = [users_range.pop(), users_range.pop()]

    async def test(self):
        await asyncio.gather(
            *[self._case(chat_id) for chat_id in self.rooms]
        )
        df = pandas.DataFrame(self.stats)
        df.to_excel(f"bochat_load_{self.users}_{self.test_time_sec}_h.xlsx")

    async def _case(self, chat_id):
        for user in self.rooms[chat_id]:
            async for stat in self._do(chat_id, user):
                self.stats.append(stat)

    def _get_message(self) -> str:
        return " ".join([
            "".join(
                [random.choice(ascii_letters)
                 for _ in range(random.randint(5, 10))]
            )
            for _ in range(random.randint(10, 20))
        ])

    async def _do(self, chat_id: int, user_id: int):
        message = self._get_message()

        connection_begin = datetime.datetime.now()
        async with websockets.connect(
            f"ws://77.232.128.27:8080/messages/connect?chat_id={chat_id}&user_id={user_id}&layer=1",
            timeout=1
        ) as ws:
            ttc = (datetime.datetime.now() -
                   connection_begin).total_seconds() * 1000
            while datetime.datetime.now().timestamp() < (self.begin_time + datetime.timedelta(seconds=self.test_time_sec)).timestamp():
                request_begin = datetime.datetime.now()
                await asyncio.wait_for(ws.send(message), timeout=1)
                response = await asyncio.wait_for(ws.recv(), timeout=20)
                ttr = (datetime.datetime.now() -
                       request_begin).total_seconds() * 1000

                yield self.stats_cls(
                    time=datetime.datetime.now().replace(microsecond=0),
                    user=user_id,
                    chat=chat_id,
                    ttr=ttr,
                    ttc=ttc,
                    b_recv=len(response),
                    b_send=len(message.encode('utf-8'))
                )


test_case = TestCase(users=25, test_time_sec=100)
asyncio.run(test_case.test())
