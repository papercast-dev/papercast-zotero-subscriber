from websockets.client import connect
from typing import AsyncIterable, List, Dict, Any
import json
from papercast.base import BaseSubscriber
from papercast.production import Production
from papercast_zotero.zotero_types import ZoteroOutput

from pyzotero import zotero


class ZoteroSubscriber(BaseSubscriber):
    output_types = {"zotero_output": ZoteroOutput}

    def __init__(self, api_key: str, library_id: str, library_type: str) -> None:
        super().__init__()
        self.url = "wss://stream.zotero.org"
        self.api_key = api_key
        self.user_id = library_id
        self.library_type = library_type
        self.zot = zotero.Zotero(library_id, library_type, api_key)
        if self.library_type == "group":
            topic = f"/groups/{library_id}"
        elif self.library_type == "user":
            topic = f"/users/{library_id}"
        else:
            raise ValueError("library_type must be 'group' or 'user'")

        self.subscription_message = {
            "action": "createSubscriptions",
            "subscriptions": [
                {
                    "apiKey": api_key,
                    "topics": [topic],
                },
            ],
        }

    async def _subscribe_topic(self, socket):
        await socket.send(json.dumps(self.subscription_message))
        response = await socket.recv()
        response_data = json.loads(response)

        if response_data["event"] == "subscriptionsCreated":
            errors = response_data.get("errors", [])

            if len(errors) > 0:
                raise ValueError(f"Error(s) creating subscriptions: {errors}")
        else:
            raise ValueError(f"Unexpected response: {response_data}")

    def _process_message(self, message) -> Production:
        message = json.loads(message)
        if message["event"] == "topicUpdated":
            print("Received Zotero update.")
            items = self.zot.top(limit=1)
            if not len(items) == 1:
                raise ValueError("Expected one item.")
            item = items[0]
            zotero_output = ZoteroOutput(**item) # type: ignore
            production = Production(zotero_output=zotero_output)
            return production

        else:
            raise ValueError(f"Unexpected message: {message}")

    async def subscribe(self) -> AsyncIterable[Production]:
        print("Connecting to Zotero websocket...")
        socket = await connect(self.url)
        _ = await socket.recv()
        print("Connected to Zotero websocket.")
        await self._subscribe_topic(socket)
        print("Subscribed to Zotero websocket.")
        async for message in socket:
            yield self._process_message(message)


if __name__ == "__main__":

    async def print_output(subscriber):
        async for production in subscriber.subscribe():
            print(production)

    from dotenv import load_dotenv
    import os

    load_dotenv()

    api_key = os.getenv("PAPERCAST_ZOTERO_API_KEY", None)
    user_id = os.getenv("PAPERCAST_ZOTERO_USER_ID", None)

    subscriber = ZoteroSubscriber(api_key, user_id, "user")  # type: ignore

    import asyncio

    asyncio.run(print_output(subscriber))
