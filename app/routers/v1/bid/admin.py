import grpc
from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends, Body
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession
from rfc9457 import BadRequestProblem
from app.config import Permissions
from app.core.utils import raise_rpc_problem
from app.database.crud import BidService
from app.database.db.session import get_async_db
from app.database.schemas.bid import BidRead, BidUpdate
from app.rpc_client.account import AccountRpcClient
from app.rpc_client.gen.python.payment.v1 import stripe_pb2
from app.schemas.bid import BidPage, BidAdminFilters, BidWinRequest, BidLostRequest, BidStatus
from app.services.rabbit_service import RabbitMQPublisher

admin_bids_router = APIRouter(prefix='/admin')


def _extract_primary_image(images: str | None) -> str | None:
    if not images:
        return None
    first_image = images.split(",")[0].strip()
    return first_image or None


def _serialize_datetime(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _build_bid_notification_payload(bid):
    auction_value = bid.auction.value if hasattr(bid.auction, "value") else bid.auction
    bid_status_value = bid.bid_status.value if hasattr(bid.bid_status, "value") else bid.bid_status
    return {
        "user_uuid": bid.user_uuid,
        "bid_id": bid.id,
        "lot_id": bid.lot_id,
        "auction": auction_value,
        "bid_amount": bid.bid_amount,
        "auction_result_bid": bid.auction_result_bid,
        "vehicle_title": bid.title,
        "vehicle_image": _extract_primary_image(bid.images),
        "auction_date": _serialize_datetime(bid.auction_date),
        "vin": bid.vin,
        "bid_status": bid_status_value,
    }


@admin_bids_router.get(
    '/bids',
    response_model=BidPage,
    description=f'List all bids with pagination, required_permission: {Permissions.BID_ALL_READ.value}',
)
async def get_all_bids(
    params: Params = Depends(),
    filters: BidAdminFilters = Depends(),
    db: AsyncSession = Depends(get_async_db),
    _: HeaderUser = Depends(require_permissions(Permissions.BID_ALL_READ.value)),
):
    bid_service = BidService(db)
    query = bid_service.build_admin_query(**filters.model_dump(exclude_none=True))
    return await paginate(db, query, params)


@admin_bids_router.post(
    '/bids/{bid_id}/won',
    response_model=BidRead,
    description=f'Mark bid as won and notify the user, required_permission: {Permissions.BID_ALL_WRITE.value}',
    dependencies=[Depends(require_permissions(Permissions.BID_ALL_WRITE))],
)
async def mark_bid_as_won(
    bid_id: int,
    win_data: BidWinRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    bid_service = BidService(db)
    existing_bid = await bid_service.get(bid_id)
    if existing_bid is None:
        raise BadRequestProblem(detail="Bid not found")
    if existing_bid.bid_status == BidStatus.WON:
        raise BadRequestProblem(detail="Bid already marked as won")

    previous_status = existing_bid.bid_status
    previous_result = existing_bid.auction_result_bid
    bid = await bid_service.mark_bid_as_won(
        bid_id=bid_id,
        auction_result_bid=win_data.auction_result_bid,
    )
    if bid is None:
        raise BadRequestProblem(detail="Bid not found")

    payload = _build_bid_notification_payload(bid)

    publisher = RabbitMQPublisher()
    try:
        await publisher.connect()
        await publisher.publish(routing_key="notification.bid.won", payload=payload)
    except Exception as exc:
        await bid_service.update(
            bid_id,
            BidUpdate(
                bid_status=previous_status,
                auction_result_bid=previous_result,
            ),
        )
        raise BadRequestProblem(detail=f"Failed to send notification: {exc}")
    finally:
        await publisher.close()

    return bid


@admin_bids_router.post(
    '/bids/{bid_id}/lost',
    response_model=BidRead,
    description=f'Mark bid as lost, refund user funds, and notify them about the outbid, required_permission: {Permissions.BID_ALL_WRITE.value}',
dependencies=[Depends(require_permissions(Permissions.BID_ALL_WRITE))],
)
async def mark_bid_as_lost(
    bid_id: int,
    loss_data: BidLostRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    bid_service = BidService(db)
    existing_bid = await bid_service.get(bid_id)
    if existing_bid is None:
        raise BadRequestProblem(detail="Bid not found")

    if existing_bid.bid_status == BidStatus.WON:
        raise BadRequestProblem(detail="Won bids cannot be marked as lost")

    refund_required = existing_bid.bid_status != BidStatus.LOST
    previous_status = existing_bid.bid_status
    previous_result = existing_bid.auction_result_bid

    bid = existing_bid

    if refund_required or loss_data.auction_result_bid is not None:
        bid = await bid_service.mark_bid_as_lost(
            bid_id=bid_id,
            auction_result_bid=loss_data.auction_result_bid,
        )
        if bid is None:
            raise BadRequestProblem(detail="Bid not found")

    if refund_required:
        try:
            async with AccountRpcClient() as account_client:
                await account_client.create_transaction(
                    user_uuid=bid.user_uuid,
                    transaction_type=stripe_pb2.TransactionType.TRANSACTION_TYPE_ADJUSTMENT,
                    amount=bid.bid_amount,
                )
        except grpc.aio.AioRpcError as exc:
            await bid_service.update(
                bid_id,
                BidUpdate(
                    bid_status=previous_status,
                    auction_result_bid=previous_result,
                ),
            )
            raise_rpc_problem("Account", exc)

    payload = _build_bid_notification_payload(bid)
    if refund_required:
        payload["refunded_amount"] = bid.bid_amount

    publisher = RabbitMQPublisher()
    try:
        await publisher.connect()
        await publisher.publish(routing_key="notification.bid.outbid", payload=payload)
    except Exception as exc:
        if refund_required:
            raise BadRequestProblem(detail=f"Failed to send notification after refund was processed: {exc}")
        raise BadRequestProblem(detail=f"Failed to send notification: {exc}")
    finally:
        await publisher.close()

    return bid
