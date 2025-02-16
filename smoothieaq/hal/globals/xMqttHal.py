from itertools import zip_longest
from typing import Optional, Callable, Awaitable

import aioreactive as rx
from expression.collections import Map

from .mqtthal import MqttHal


def topic_split(topic: str) -> list[str]:
    if str(topic).startswith("$share/"):
        topic = topic.split("/", 2)[2]
    return topic.split("/")

def match(topic_parts: list[str], template_parts: list[str]) -> bool:
    for topic_part, part in zip_longest(topic_parts, template_parts):
        if part == "#" and not str(topic_part).startswith("$"):
            return True
        elif (topic_part is None or part not in {"+", topic_part}) or (
                part == "+" and topic_part.startswith("$")
        ):
            return False
        continue
    return len(template_parts) == len(topic_parts)


class XMqttHal(MqttHal):

    def __init__(self) -> None:
        super().__init__()
        self.host: Optional[str] = None
        self.subscriptions: dict[str, (list[str], rx.AsyncSubject[dict])] = {}
#        self.started: bool = False

#    def init(self, path: Optional[str], params: Map[str, str], error_handler: Callable[[str], Awaitable[None]] = None):
#        self.host = params['host']

    def _find(self, topic: str) -> Optional[rx.AsyncSubject[dict]]:
        topic_parts = topic_split(topic)
        for (template_parts, rx_subscription) in self.subscriptions.values():
            if match(topic_parts, template_parts):
                return rx_subscription
        return None

    async def _subscribe(self, topic: str, rx_subscription: rx.AsyncSubject[dict]):
        pass


    async def subscribe(self, topic: str, rx_subscription: rx.AsyncSubject[dict]):
        self.subscriptions[topic] = (topic_split(topic), rx_subscription)
        await self._subscribe(topic, rx_subscription)


    async def _unsubscribe(self, topic: str):
        pass

    async def unsubscribe(self, topic: str):
        del self.subscriptions[topic]
        await self._unsubscribe(topic)
        if not self.subscriptions:
            self.started = False
            await self.stop()

    async def _publish(self, topic: str, payload: dict):
        pass

    async def publish(self, topic: str, payload: dict):
        assert self.started
        await self._publish(topic, payload)
