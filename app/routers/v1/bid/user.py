from typing import Any

import grpc
from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Body
from fastapi.params import Depends
from rfc9457 import BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.core.utils import raise_rpc_problem
from app.database.crud import BidService
from app.database.db.session import get_async_db
from app.database.schemas.bid import BidCreate
from app.rpc_client.account import AccountRpcClient
from app.rpc_client.auction_api import ApiRpcClient
from app.schemas.bid import BidIn
from app.rpc_client.gen.python.payment.v1 import stripe_pb2
from app.services.rabbit_service import RabbitMQPublisher

user_bids_router = APIRouter()


def _get_proto_value(message, field_name: str):
    if not hasattr(message, field_name):
        return None
    value = getattr(message, field_name)
    if isinstance(value, str):
        return value.strip()
    return value


def _collect_lot_images(lot_data) -> str | None:
    images = list(lot_data.link_img_hd)
    if not images:
        images = list(lot_data.link_img_small)
    return ",".join(images) if images else None


def _build_bid_payload(lot_data) -> dict[str, Any]:
    engine_size = _get_proto_value(lot_data, "engine_size")
    cylinders = _get_proto_value(lot_data, "cylinders")
    return {
        "title": _get_proto_value(lot_data, "title"),
        "auction_date": _get_proto_value(lot_data, "auction_date"),
        "vin": _get_proto_value(lot_data, "vin"),
        "images": _collect_lot_images(lot_data),
        "odometer": _get_proto_value(lot_data, "odometer"),
        "location": _get_proto_value(lot_data, "location"),
        "damage_pr": _get_proto_value(lot_data, "damage_pr"),
        "damage_sec": _get_proto_value(lot_data, "damage_sec"),
        "fuel": _get_proto_value(lot_data, "fuel"),
        "transmission": _get_proto_value(lot_data, "transmission"),
        "engine_size": str(engine_size) if engine_size is not None else None,
        "cylinders": str(cylinders) if cylinders is not None else None,
        "seller": _get_proto_value(lot_data, "seller"),
        "document": _get_proto_value(lot_data, "document"),
        "status": _get_proto_value(lot_data, "status"),
    }




@user_bids_router.post(
    '/bid',
    description=f'Bid on some lot on auction, required_permission: {Permissions.BID_WRITE.value}',
)
async def bid_on_auction(
    db: AsyncSession = Depends(get_async_db),
    data: BidIn = Body(...),
    user: HeaderUser = Depends(require_permissions(Permissions.BID_WRITE.value)),
):
    user_uuid = user.user_uuid
    bid_service = BidService(db)

    lot_payload: dict[str, Any] | None = None
    current_bid_amount = 0
    try:
        async with ApiRpcClient() as auction_client:
            lot_response = await auction_client.get_lot_by_vin_or_lot_id(
                vin_or_lot_id=str(data.lot_id), site=data.auction.value
            )
            if not lot_response.lot:
                raise BadRequestProblem(detail="Lot not found")

            lot_data = lot_response.lot[0]
            if lot_data.form_get_type == 'history':
                raise BadRequestProblem(detail="Auction is closed")

            lot_payload = _build_bid_payload(lot_data)

            current_bid_response = await auction_client.get_current_bid(
                lot_id=data.lot_id, site=data.auction.value
            )
            current_bid_amount = current_bid_response.current_bid.pre_bid
            if current_bid_amount and current_bid_amount > data.bid_amount:
                raise BadRequestProblem(detail="Current bid on auction is higher")
    except grpc.aio.AioRpcError as exc:
        raise_rpc_problem("Auction", exc)

    if lot_payload is None:
        raise BadRequestProblem(detail="Unable to read lot data")

    bid = None
    try:
        async with AccountRpcClient() as account_client:
            account_info = await account_client.get_account_info(user_uuid=user_uuid)

            if account_info.balance < data.bid_amount:
                raise BadRequestProblem(detail="Not enough money")

            highest_bid = await bid_service.get_highest_bid_for_lot(data.auction, data.lot_id)
            if highest_bid and highest_bid.bid_amount >= data.bid_amount:
                raise BadRequestProblem(detail="Someone made a higher bid for this lot")

            previous_bid = await bid_service.get_user_bid_for_lot(user_uuid, data.auction, data.lot_id)
            if previous_bid and previous_bid.bid_amount >= data.bid_amount:
                raise BadRequestProblem(detail="Your previous bid is higher")

            bid = await bid_service.create(
                BidCreate(
                    lot_id=data.lot_id,
                    bid_amount=data.bid_amount,
                    user_uuid=user_uuid,
                    auction=data.auction,
                    **lot_payload,
                )
            )

            await account_client.create_transaction(
                user_uuid=user_uuid,
                transaction_type=stripe_pb2.TransactionType.TRANSACTION_TYPE_BID_PLACEMENT,
                amount=data.bid_amount,
            )
    except grpc.aio.AioRpcError as exc:
        raise_rpc_problem("Account", exc)


    if bid is None:
        raise BadRequestProblem(detail="Bid was not created")

    auction_date_value = lot_payload.get("auction_date")
    if auction_date_value is not None and hasattr(auction_date_value, "isoformat"):
        auction_date_value = auction_date_value.isoformat()

    payload = {
        "user_uuid": user_uuid,
        "bid_amount": bid.bid_amount,
        "auction_data": auction_date_value,
        "vehicle_title": lot_payload.get("title"),
        "vehicle_image": lot_payload.get("images").split(',')[0] if lot_payload.get("images") else None,
        "auction": data.auction.value,
        "lot_id": data.lot_id,
        "current_bid": current_bid_amount,
    }

    publisher = RabbitMQPublisher()
    try:
        await publisher.connect()
        await publisher.publish(routing_key="bid.new_bid_placed", payload=payload)
    finally:
        await publisher.close()
