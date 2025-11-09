import importlib
import sys
from typing import Optional, Union

import grpc

from app.config import settings
from app.rpc_client.base_client import BaseRpcClient, T

sys.modules.setdefault("payment", importlib.import_module("app.rpc_client.gen.python.payment"))

from app.rpc_client.gen.python.payment.v1 import stripe_pb2_grpc, stripe_pb2


class AccountRpcClient(BaseRpcClient[stripe_pb2_grpc.PaymentServiceStub]):
    def __init__(self):
        super().__init__(server_url=settings.RPC_PAYMENT_URL)

    async def __aenter__(self):
        await self.connect()
        return self

    def _create_stub(self, channel: grpc.aio.Channel) -> T:
        return stripe_pb2_grpc.PaymentServiceStub(channel)

    async def create_transaction(
            self,
            user_uuid: str,
            transaction_type: Union[stripe_pb2.TransactionType, str],
            amount: int,
            plan_id: Optional[int] = None,
    ) -> stripe_pb2.CreateNewTransactionResponse:
        request = stripe_pb2.CreateNewTransactionRequest(
            user_uuid=user_uuid,
            transaction_type=transaction_type,
            amount=amount,
        )
        if plan_id is not None:
            request.plan_id = plan_id

        return await self._execute_request(self.stub.CreateNewTransaction, request)

    async def get_account_info(
            self,
            user_uuid: str,
    ) -> stripe_pb2.GetUserAccountResponse:
        request = stripe_pb2.GetUserAccountRequest(
            user_uuid=user_uuid,
        )

        return await self._execute_request(self.stub.GetUserAccount, request)

    async def get_user_account(
            self,
            user_uuid: str,
    ) -> stripe_pb2.GetUserAccountResponse:
        return await self.get_account_info(user_uuid=user_uuid)
