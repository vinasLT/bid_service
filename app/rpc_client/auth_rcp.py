import os
import sys

import grpc

from app.config import settings
from app.rpc_client.base_client import BaseRpcClient, T

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gen', 'python'))

from app.rpc_client.gen.python.auth.v1 import auth_pb2_grpc, auth_pb2


class AuthRcp(BaseRpcClient[auth_pb2_grpc.AuthServiceStub]):
    def __init__(self):
        super().__init__(server_url=settings.RPC_AUTH_URL)

    async def __aenter__(self):
        await self.connect()
        return self

    def _create_stub(self, channel: grpc.aio.Channel) -> T:
        return auth_pb2_grpc.AuthServiceStub(channel)

    async def get_user(self, user_uuid: str) -> auth_pb2.GetUserResponse:
        request = auth_pb2.GetUserRequest(user_uuid=user_uuid)
        return await self._execute_request(self.stub.GetUser, request)
