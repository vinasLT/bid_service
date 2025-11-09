import asyncio
import json
import uuid
from datetime import datetime, UTC

from aio_pika import connect_robust, Message, ExchangeType, DeliveryMode
from aio_pika.abc import AbstractRobustExchange

from app.config import settings


class RabbitMQPublisher:
    def __init__(self, exchange_type: ExchangeType = ExchangeType.TOPIC):
        self.url = settings.RABBITMQ_URL
        self.exchange_name = settings.RABBITMQ_EXCHANGE_NAME
        self.exchange_type = exchange_type
        self.connection = None
        self.channel = None
        self.exchange: AbstractRobustExchange | None = None

    async def connect(self):
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name,
            type=self.exchange_type,
            durable=True
        )

    async def publish(self, routing_key: str, payload: dict):
        if self.exchange is None:
            await self.connect()
        message_body = json.dumps({
            "type": routing_key,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": str(uuid.uuid4())
        }).encode()
        message = Message(
            message_body,
            content_type="application/json",
            correlation_id=str(uuid.uuid4()),
            delivery_mode=DeliveryMode.PERSISTENT

        )
        await self.exchange.publish(message, routing_key=routing_key, )

    async def close(self):
        if self.connection:
            await self.connection.close()


if __name__ == "__main__":
    async def main():
        publisher = RabbitMQPublisher()
        await publisher.connect()
        payload = {"user_uuid": str(uuid.uuid4()),
                   'code': '123456',
                   'destination': 'email',
                   'first_name': 'John',
                   'last_name': 'Doe',
                   'email': 'peyrovskaaa@gmail.com',
                   'expire_minutes': 15,
                   'phone_number': '32452937423'}
        await publisher.publish(routing_key="notification.auth.send_code", payload=payload)
        await publisher.close()

    asyncio.run(main())
