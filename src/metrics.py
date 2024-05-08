from typing import Generator
from prometheus_client import Counter, Histogram, Gauge


ws_connections = Gauge(
    "ws_connections", "Количество подлкючений по вебсокету")

ws_messages = Counter(
    "ws_messages", "Количество сообщений по вебсокету"
)


def get_range(start: float = 0.150, stop: int = 0.750, step: float = 0.050) -> Generator[float, None, None]:
    while start < stop:
        yield round(start, 3)
        start += step


ws_time_to_process = Histogram("ws_time_to_process", "Время на выполнение запроса",
                               buckets=(*list(get_range()), float('inf')))
