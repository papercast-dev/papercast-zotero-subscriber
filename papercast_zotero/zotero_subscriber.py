import json
from typing import Any, AsyncIterable, Dict, List

import requests
import time
from papercast_zotero.zotero_types import ZoteroOutput
from pyzotero import zotero
from websockets.client import connect

from papercast.base import BaseSubscriber
from papercast.production import Production
from papercast.types import PDFFile


class ZoteroSubscriber(BaseSubscriber):
    output_types = {"zotero_output": ZoteroOutput, "pdf": PDFFile}

    def __init__(
        self,
        api_key: str,
        library_id: str,
        library_type: str,
        pdf_dir: str,
        file_timeout: int = 60,
    ) -> None:
        super().__init__()
        self.url = "wss://stream.zotero.org"
        self.api_key = api_key
        self.user_id = library_id
        self.library_type = library_type
        self.pdf_dir = pdf_dir
        self.file_timeout = file_timeout
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

    def _download_file(self, zotero_output: ZoteroOutput):
        if zotero_output.key is None:
            raise ValueError("zotero_output.key is None")

        self.logger.info(
            f"Querying Zotero for {zotero_output.key} for file download..."
        )
        response = requests.get(
            f"https://api.zotero.org/users/{self.user_id}/items/{zotero_output.key}",
            headers={"Zotero-API-Key": self.api_key},
        )

        time.sleep(self.file_timeout)

        if not response.status_code == 200:
            print(response.status_code)
            raise ValueError(f"Unexpected response code: {response.status_code}")

        response_json = response.json()

        file_url = None

        try:
            file_url = response_json["links"]["attachment"]["href"] + "/file"
        except KeyError:
            self.logger.warning(
                f"Could not find file attachment for {zotero_output.key}. Skipping."
            )

        if file_url:
            self.logger.info(f"Downloading {zotero_output.key}...")
            response = requests.get(
                file_url,
                headers={"Zotero-API-Key": self.api_key},  # type: ignore
            )
            outpath = f"{self.pdf_dir}/{zotero_output.key}.pdf"
            with open(outpath, "wb") as f:
                f.write(response.content)

            return outpath

        else:
            return None

    def _process_message(self, message) -> Production:
        message = json.loads(message)
        if message["event"] == "topicUpdated":
            print("Received Zotero update.")

            items = self.zot.top(limit=1)
            if not len(items) == 1:
                raise ValueError("Expected one item.")

            item = items[0]
            zotero_output = ZoteroOutput(**item)  # type: ignore
            production = Production(zotero_output=zotero_output)

            try:
                pdf_path = self._download_file(zotero_output)

                if pdf_path:
                    setattr(production, "pdf", PDFFile(pdf_path))

            except Exception as e:
                self.logger.error(e)

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

    import os

    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("PAPERCAST_ZOTERO_API_KEY", None)
    user_id = os.getenv("PAPERCAST_ZOTERO_USER_ID", None)

    subscriber = ZoteroSubscriber(api_key, user_id, "user")  # type: ignore

    import asyncio

    asyncio.run(print_output(subscriber))
