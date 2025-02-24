import aioreactive as rx

from .globalhal import GlobalHal


class MqttHal(GlobalHal):

    async def subscribe(self, topic: str, rx_subscription: rx.AsyncSubject[dict]):
        pass

    async def unsubscribe(self, topic: str):
        pass

    async def publish(self, topic: str, payload: str):
        pass