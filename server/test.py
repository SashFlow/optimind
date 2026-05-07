from dotenv import load_dotenv
from livekit import api
from livekit.protocol.egress import ListEgressRequest
import asyncio

load_dotenv()


async def test_egress():
    lkapi = api.LiveKitAPI()
    egress = lkapi.egress

    response = await egress.list_egress(list=ListEgressRequest(active=False))
    print("Active egresses:", response)
    print("====================================")


if __name__ == "__main__":
    asyncio.run(test_egress())
