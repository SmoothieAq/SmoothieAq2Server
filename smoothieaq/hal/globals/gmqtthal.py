import json
import logging
from typing import Optional

import aioreactive as rx
import gmqtt

from .xMqttHal import XMqttHal

log = logging.getLogger(__name__)


def on_connect(client, flags, rc, properties):
    log.info("connect")


def on_disconnect(client, packet, exc=None):
    log.info("disconnect")


def on_subscribe(client, mid, qos, properties):
    log.info(f"subscribe {mid}")


class GmqttHal(XMqttHal):

    def __init__(self) -> None:
        super().__init__()
        self.client: Optional[gmqtt.Client] = None

    async def on_message(self, client, topic, payload, qos, properties):
        log.debug(f"message {payload}")
        rx_subject: Optional[rx.AsyncSubject[dict]] = self._find(topic)
        if rx_subject:
            await rx_subject.asend(json.loads(payload.decode()))
        return 0

    async def global_start(self):
        self.client = gmqtt.Client("SmoothieAq")
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_subscribe = on_subscribe
        self.client.on_message = self.on_message
        await self.client.connect(self.host or "smoothieaq.local")

    async def global_stop(self):
        await self.client.disconnect()

    async def _subscribe(self, topic: str, rx_subscription: rx.AsyncSubject[dict]):
        self.client.subscribe(topic)

    async def _unsubscribe(self, topic: str):
        self.client.unsubscribe(topic)

    async def _publish(self, topic: str, payload: dict):
        self.client.publish(topic, payload)
