from typing import Any

import grpc
from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends, Body, Query
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession
from rfc9457 import BadRequestProblem
from app.config import Permissions
from app.core.utils import raise_rpc_problem
from app.database.crud import BidService
from app.database.db.session import get_async_db
from app.database.models import Bid
from app.database.schemas.bid import BidRead, BidUpdate
from app.rpc_client.account import AccountRpcClient
from app.rpc_client.auth_rcp import AuthRcp
from app.rpc_client.gen.python.payment.v1 import stripe_pb2
from app.schemas.bid import (
    BidPage,
    BidFilters,
    BidWinRequest,
    BidLostRequest,
    BidOnApprovalRequest,
    BidStatus,
    PaymentStatus,
)
from app.services.rabbit_service import RabbitMQPublisher

bids_management_router = APIRouter(prefix='/bids')


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


def _build_bid_notification_payload(bid: Bid, email: str | None, phone_number: str | None):
    auction_value = bid.auction.value if hasattr(bid.auction, "value") else bid.auction
    bid_status_value = bid.bid_status.value if hasattr(bid.bid_status, "value") else bid.bid_status
    return {
        "user_uuid": bid.user_uuid,
        "bid_id": bid.id,
        "lot_id": bid.lot_id,
        "auction": auction_value,
        "bid_amount": bid.bid_amount,
        "final_bid": bid.auction_result_bid,
        "vehicle_title": bid.title,
        "vehicle_image": _extract_primary_image(bid.images),
        "auction_date": _serialize_datetime(bid.auction_date),
        "vin": bid.vin,
        "bid_status": bid_status_value,
        "payment_status": getattr(bid.payment_status, "value", bid.payment_status),
        "account_blocked": getattr(bid, "account_blocked", None),
        'email': email,
        'phone_number': phone_number,
    }


async def _get_user_contacts(user_uuid: str) -> tuple[Any | None, Any | None] | None:
    try:
        async with AuthRcp() as auth_client:
            response = await auth_client.get_user(user_uuid=user_uuid)
            return response.email or None, response.phone_number or None
    except grpc.aio.AioRpcError as exc:
        raise_rpc_problem("Auth", exc)


@bids_management_router.get(
    '',
    response_model=BidPage,
    description=f'List all bids with pagination, required_permission: {Permissions.BID_ALL_READ.value}',
)
async def get_all_bids(
    params: Params = Depends(),
    filters: BidFilters = Depends(),
    db: AsyncSession = Depends(get_async_db),
    _: HeaderUser = Depends(require_permissions(Permissions.BID_ALL_READ.value)),
):
    bid_service = BidService(db)
    query = bid_service.build_admin_query(**filters.model_dump(exclude_none=True))
    return await paginate(db, query, params)


@bids_management_router.post(
    '/{bid_id}/on-approval',
    response_model=BidRead,
    description=f'Mark bid as on approval and block account pending seller decision, required_permission: {Permissions.BID_ALL_WRITE.value}',
    dependencies=[Depends(require_permissions(Permissions.BID_ALL_WRITE))],
)
async def mark_bid_as_on_approval(
    bid_id: int,
    data: BidOnApprovalRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    bid_service = BidService(db)
    existing_bid = await bid_service.get(bid_id)
    if existing_bid is None:
        raise BadRequestProblem(detail="Bid not found")
    if existing_bid.bid_status in (BidStatus.WON, BidStatus.LOST, BidStatus.ON_APPROVAL):
        raise BadRequestProblem(detail="Bid cannot be set to approval in current state")

    bid = await bid_service.mark_bid_as_on_approval(
        bid_id=bid_id,
        auction_result_bid=data.auction_result_bid,
    )
    if bid is None:
        raise BadRequestProblem(detail="Bid not found")
    return bid


@bids_management_router.post(
    '/{bid_id}/won',
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
    previous_payment_status = existing_bid.payment_status
    previous_account_blocked = existing_bid.account_blocked
    bid = await bid_service.mark_bid_as_won(
        bid_id=bid_id,
        auction_result_bid=win_data.auction_result_bid,
    )
    if bid is None:
        raise BadRequestProblem(detail="Bid not found")

    email, phone_number = await _get_user_contacts(bid.user_uuid)
    payload = _build_bid_notification_payload(bid, email=email, phone_number=phone_number)

    publisher = RabbitMQPublisher()
    try:
        await publisher.connect()
        payload['destination'] = 'email'
        await publisher.publish(routing_key="bid.you_won_bid", payload=payload)
        payload['destination'] = 'sms'
        await publisher.publish(routing_key="bid.you_won_bid", payload=payload)
    except Exception as exc:
        await bid_service.update(
            bid_id,
            BidUpdate(
                bid_status=previous_status,
                auction_result_bid=previous_result,
                payment_status=previous_payment_status,
                account_blocked=previous_account_blocked,
            ),
        )
        raise BadRequestProblem(detail=f"Failed to send notification: {exc}")
    finally:
        await publisher.close()

    return bid


@bids_management_router.post(
    '/{bid_id}/approve',
    response_model=BidRead,
    description=f'Seller approves bid -> mark as won, required_permission: {Permissions.BID_ALL_WRITE.value}',
    dependencies=[Depends(require_permissions(Permissions.BID_ALL_WRITE))],
)
async def approve_bid(
    bid_id: int,
    win_data: BidWinRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    bid_service = BidService(db)
    existing_bid = await bid_service.get(bid_id)
    if existing_bid is None:
        raise BadRequestProblem(detail="Bid not found")
    if existing_bid.bid_status != BidStatus.ON_APPROVAL:
        raise BadRequestProblem(detail="Bid is not awaiting seller approval")

    return await mark_bid_as_won(bid_id=bid_id, win_data=win_data, db=db)

@bids_management_router.get('/for-user', response_model=BidPage, description=f'Get bids for user, required_permission: {Permissions.BID_ALL_READ.value}',
                            dependencies=[Depends(require_permissions(Permissions.BID_ALL_READ))])
async def get_user_bids(
    params: Params = Depends(),
    user_uuid: str = Query(...),
    filters: BidFilters = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    bid_service = BidService(db)
    filter_payload = filters.model_dump(exclude_none=True)
    query = bid_service.build_admin_query(**filter_payload).where(Bid.user_uuid == user_uuid)
    return await paginate(db, query, params)

@bids_management_router.post(
    '/{bid_id}/lost',
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
    previous_payment_status = existing_bid.payment_status
    previous_account_blocked = existing_bid.account_blocked

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
                    payment_status=previous_payment_status,
                    account_blocked=previous_account_blocked,
                ),
            )
            raise_rpc_problem("Account", exc)

    email, phone_number = await _get_user_contacts(bid.user_uuid)
    payload = _build_bid_notification_payload(bid, email=email, phone_number=phone_number)
    if refund_required:
        payload["refunded_amount"] = bid.bid_amount

    publisher = RabbitMQPublisher()
    try:
        await publisher.connect()
        payload['destination'] = 'email'
        await publisher.publish(routing_key="bid.you_lost_bid", payload=payload)
        payload['destination'] = 'sms'
        await publisher.publish(routing_key="bid.you_lost_bid", payload=payload)
    except Exception as exc:
        if refund_required:
            raise BadRequestProblem(detail=f"Failed to send notification after refund was processed: {exc}")
        raise BadRequestProblem(detail=f"Failed to send notification: {exc}")
    finally:
        await publisher.close()

    return bid


@bids_management_router.post(
    '/{bid_id}/decline',
    response_model=BidRead,
    description=f'Seller declines bid -> mark as lost and unblock account, required_permission: {Permissions.BID_ALL_WRITE.value}',
    dependencies=[Depends(require_permissions(Permissions.BID_ALL_WRITE))],
)
async def decline_bid(
    bid_id: int,
    loss_data: BidLostRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    bid_service = BidService(db)
    existing_bid = await bid_service.get(bid_id)
    if existing_bid is None:
        raise BadRequestProblem(detail="Bid not found")
    if existing_bid.bid_status != BidStatus.ON_APPROVAL:
        raise BadRequestProblem(detail="Bid is not awaiting seller approval")

    return await mark_bid_as_lost(bid_id=bid_id, loss_data=loss_data, db=db)


@bids_management_router.post(
    '/{bid_id}/paid',
    response_model=BidRead,
    description=f'Mark payment as paid for won bid and unblock account, required_permission: {Permissions.BID_ALL_WRITE.value}',
    dependencies=[Depends(require_permissions(Permissions.BID_ALL_WRITE))],
)
async def mark_payment_as_paid(
    bid_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    bid_service = BidService(db)
    existing_bid = await bid_service.get(bid_id)
    if existing_bid is None:
        raise BadRequestProblem(detail="Bid not found")
    if existing_bid.bid_status != BidStatus.WON:
        raise BadRequestProblem(detail="Only won bids can be marked as paid")
    if existing_bid.payment_status == PaymentStatus.PAID:
        raise BadRequestProblem(detail="Payment already marked as paid")

    bid = await bid_service.mark_payment_as_paid(bid_id)
    if bid is None:
        raise BadRequestProblem(detail="Bid not found")
    return bid
