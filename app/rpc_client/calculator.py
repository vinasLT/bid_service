import os
import sys
from typing import Sequence

import grpc

from app.config import settings
from app.rpc_client.base_client import BaseRpcClient, T

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gen', 'python'))

from app.rpc_client.gen.python.calculator.v1 import calculator_pb2, calculator_pb2_grpc


class CalculatorRpcClient(BaseRpcClient[calculator_pb2_grpc.CalculatorServiceStub]):
    def __init__(self):
        super().__init__(server_url=settings.RPC_CALCULATOR_URL)

    async def __aenter__(self):
        await self.connect()
        return self

    def _create_stub(self, channel: grpc.aio.Channel) -> T:
        return calculator_pb2_grpc.CalculatorServiceStub(channel)

    async def get_calculator_with_data(
        self,
        *,
        price: int,
        auction: str,
        vehicle_type: str,
        location: str,
        fee_type: str | None = None,
        destination: str | None = None,
    ) -> calculator_pb2.GetCalculatorWithDataResponse:
        request = calculator_pb2.GetCalculatorWithDataRequest(
            price=price,
            auction=auction,
            vehicle_type=vehicle_type,
            location=location,
        )

        if fee_type is not None:
            request.fee_type = fee_type
        if destination is not None:
            request.destination = destination

        return await self._execute_request(self.stub.GetCalculatorWithData, request)

    async def get_calculator_with_ids(
        self,
        *,
        price: int,
        auction: str,
        vehicle_type: str,
        fee_type_id: int | None = None,
        destination_id: int | None = None,
        location_id: int | None = None,
    ) -> calculator_pb2.GetCalculatorWithIdsResponse:
        request = calculator_pb2.GetCalculatorWithIdsRequest(
            price=price,
            auction=auction,
            vehicle_type=vehicle_type,
        )

        if fee_type_id is not None:
            request.fee_type_id = fee_type_id
        if destination_id is not None:
            request.destination_id = destination_id
        if location_id is not None:
            request.location_id = location_id

        return await self._execute_request(self.stub.GetCalculatorWithIds, request)

    async def get_calculator_with_data_batch(
        self,
        requests: Sequence[calculator_pb2.GetCalculatorBatchRequest],
    ) -> calculator_pb2.GetCalculatorWithDataBatchResponse:
        request = calculator_pb2.GetCalculatorWithDataBatchRequest(data=requests)
        return await self._execute_request(self.stub.GetCalculatorWithDataBatch, request)

    async def get_calculator_without_data(
        self,
        *,
        price: int,
        auction: str,
        lot_id: str,
    ) -> calculator_pb2.GetCalculatorWithoutDataResponse:
        request = calculator_pb2.GetCalculatorWithoutDataRequest(
            price=price,
            auction=auction,
            lot_id=lot_id,
        )
        return await self._execute_request(self.stub.GetCalculatorWithoutData, request)


class DetailedInfoService(BaseRpcClient[calculator_pb2_grpc.DetailedInfoServiceStub]):
    def __init__(self, server_url: str | None = None):
        # Detailed info endpoints are part of the calculator service
        super().__init__(server_url=server_url or settings.RPC_CALCULATOR_URL)

    async def __aenter__(self):
        await self.connect()
        return self

    def _create_stub(self, channel: grpc.aio.Channel) -> T:
        return calculator_pb2_grpc.DetailedInfoServiceStub(channel)

    async def get_detailed_location(
        self,
        *,
        location_id: int,
    ) -> calculator_pb2.GetDetailedLocationResponse:
        request = calculator_pb2.GetDetailedLocationRequest(id=location_id)
        return await self._execute_request(self.stub.GetDetailedLocation, request)

    async def get_detailed_terminal(
        self,
        *,
        terminal_id: int,
    ) -> calculator_pb2.GetDetailedTerminalResponse:
        request = calculator_pb2.GetDetailedTerminalRequest(id=terminal_id)
        return await self._execute_request(self.stub.GetDetailedTerminal, request)

    async def get_detailed_destination(
        self,
        *,
        destination_id: int,
    ) -> calculator_pb2.GetDetailedDestinationResponse:
        request = calculator_pb2.GetDetailedDestinationRequest(id=destination_id)
        return await self._execute_request(self.stub.GetDetailedDestination, request)

    async def get_detailed_fee_type(
        self,
        *,
        fee_type_id: int,
    ) -> calculator_pb2.GetDetailedFeeTypeResponse:
        request = calculator_pb2.GetDetailedFeeTypeRequest(id=fee_type_id)
        return await self._execute_request(self.stub.GetDetailedFeeType, request)
