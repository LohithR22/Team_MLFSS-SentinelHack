"""WebSocket consumers for live event push."""
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class AlertConsumer(AsyncJsonWebsocketConsumer):
    """Subscribes the client to the 'alerts' group. The Alert Agent fires
    group_send with type='alert.event'; this consumer forwards the payload
    as JSON to the connected frontend."""

    group_name = 'alerts'

    async def connect(self) -> None:
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'hello': 'alerts-stream-connected'})

    async def disconnect(self, _code) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def alert_event(self, event: dict) -> None:
        await self.send_json(event['payload'])
