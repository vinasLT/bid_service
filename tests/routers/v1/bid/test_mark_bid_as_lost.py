import grpc
import pytest
from rfc9457 import BadRequestProblem

from app.routers.v1.bid import admin
from app.schemas.bid import BidLostRequest, BidStatus
from tests.routers.v1.bid.stubs import (
    AccountClientStub,
    BidServiceStub,
    DummyBid,
    PublisherStub,
    override_account_client,
    override_bid_service,
    override_publisher,
)


@pytest.mark.asyncio
async def test_mark_bid_as_lost_returns_400_when_missing(monkeypatch):
    stub = BidServiceStub(get_result=None)
    override_bid_service(monkeypatch, stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_lost(
            bid_id=42,
            loss_data=BidLostRequest(),
            db=object(),
        )
    assert exc_info.value.detail == "Bid not found"


@pytest.mark.asyncio
async def test_mark_bid_as_lost_rejects_won_bids(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.WON)
    stub = BidServiceStub(get_result=existing_bid)
    override_bid_service(monkeypatch, stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_lost(
            bid_id=existing_bid.id,
            loss_data=BidLostRequest(auction_result_bid=existing_bid.bid_amount),
            db=object(),
        )
    assert exc_info.value.detail == "Won bids cannot be marked as lost"


@pytest.mark.asyncio
async def test_mark_bid_as_lost_returns_400_when_service_cannot_update(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.WAITING_AUCTION_RESULT)
    stub = BidServiceStub(get_result=existing_bid, mark_lost_result=None)
    override_bid_service(monkeypatch, stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_lost(
            bid_id=existing_bid.id,
            loss_data=BidLostRequest(auction_result_bid=5000),
            db=object(),
        )
    assert exc_info.value.detail == "Bid not found"


@pytest.mark.asyncio
async def test_mark_bid_as_lost_marks_bid_refunds_and_notifies(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.WAITING_AUCTION_RESULT)
    lost_bid = DummyBid(bid_status=BidStatus.LOST, auction_result_bid=8000)
    stub = BidServiceStub(get_result=existing_bid, mark_lost_result=lost_bid)
    override_bid_service(monkeypatch, stub)

    publisher = override_publisher(monkeypatch, PublisherStub())
    account_client = override_account_client(monkeypatch, AccountClientStub())

    result = await admin.mark_bid_as_lost(
        bid_id=existing_bid.id,
        loss_data=BidLostRequest(auction_result_bid=lost_bid.auction_result_bid),
        db=object(),
    )

    assert result is lost_bid
    assert stub.mark_bid_as_lost_calls == [
        {"bid_id": existing_bid.id, "auction_result_bid": lost_bid.auction_result_bid}
    ]
    assert account_client.calls and account_client.calls[0]["amount"] == lost_bid.bid_amount
    assert publisher.publish_calls[0][0] == "bid.you_lost_bid"
    payload = publisher.publish_calls[0][1]
    assert payload["bid_status"] == BidStatus.LOST.value
    assert payload["refunded_amount"] == lost_bid.bid_amount


@pytest.mark.asyncio
async def test_mark_bid_as_lost_rolls_back_when_refund_fails(monkeypatch):
    existing_bid = DummyBid(
        bid_status=BidStatus.WAITING_AUCTION_RESULT,
        auction_result_bid=7000,
    )
    lost_bid = DummyBid(bid_status=BidStatus.LOST, auction_result_bid=6500)
    stub = BidServiceStub(get_result=existing_bid, mark_lost_result=lost_bid)
    override_bid_service(monkeypatch, stub)

    rpc_error = grpc.aio.AioRpcError(grpc.StatusCode.INTERNAL, None, None)
    override_account_client(monkeypatch, AccountClientStub(exc=rpc_error))

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_lost(
            bid_id=existing_bid.id,
            loss_data=BidLostRequest(auction_result_bid=lost_bid.auction_result_bid),
            db=object(),
        )
    assert "Account service error" in exc_info.value.detail

    assert stub.update_calls, "Expected rollback to original status"
    rollback_bid_id, rollback_update = stub.update_calls[0]
    assert rollback_bid_id == existing_bid.id
    assert rollback_update.bid_status == existing_bid.bid_status
    assert rollback_update.auction_result_bid == existing_bid.auction_result_bid


@pytest.mark.asyncio
async def test_mark_bid_as_lost_raises_when_notification_fails_after_refund(monkeypatch):
    existing_bid = DummyBid()
    lost_bid = DummyBid(bid_status=BidStatus.LOST)
    stub = BidServiceStub(get_result=existing_bid, mark_lost_result=lost_bid)
    override_bid_service(monkeypatch, stub)

    override_account_client(monkeypatch, AccountClientStub())
    publisher = PublisherStub(publish_exception=RuntimeError("connection lost"))
    override_publisher(monkeypatch, publisher)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_lost(
            bid_id=existing_bid.id,
            loss_data=BidLostRequest(),
            db=object(),
        )
    assert exc_info.value.detail.startswith("Failed to send notification after refund was processed")

    assert publisher.closed is True


@pytest.mark.asyncio
async def test_mark_bid_as_lost_updates_notification_without_refund(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.LOST, auction_result_bid=5000)
    updated_bid = DummyBid(
        bid_status=BidStatus.LOST,
        auction_result_bid=5500,
    )
    stub = BidServiceStub(get_result=existing_bid, mark_lost_result=updated_bid)
    override_bid_service(monkeypatch, stub)

    publisher = override_publisher(monkeypatch, PublisherStub())

    result = await admin.mark_bid_as_lost(
        bid_id=existing_bid.id,
        loss_data=BidLostRequest(auction_result_bid=updated_bid.auction_result_bid),
        db=object(),
    )

    assert result is updated_bid
    assert not stub.update_calls
    assert stub.mark_bid_as_lost_calls == [
        {"bid_id": existing_bid.id, "auction_result_bid": updated_bid.auction_result_bid}
    ]
    payload = publisher.publish_calls[0][1]
    assert "refunded_amount" not in payload


@pytest.mark.asyncio
async def test_mark_bid_as_lost_reports_notification_failure_without_refund(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.LOST)
    stub = BidServiceStub(get_result=existing_bid, mark_lost_result=existing_bid)
    override_bid_service(monkeypatch, stub)

    publisher = PublisherStub(publish_exception=RuntimeError("queue unavailable"))
    override_publisher(monkeypatch, publisher)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_lost(
            bid_id=existing_bid.id,
            loss_data=BidLostRequest(),
            db=object(),
        )
    assert exc_info.value.detail.startswith("Failed to send notification")

    assert stub.update_calls == []
    assert publisher.closed is True


@pytest.mark.asyncio
async def test_decline_bid_requires_on_approval(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.WON)
    stub = BidServiceStub(get_result=existing_bid)
    override_bid_service(monkeypatch, stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.decline_bid(
            bid_id=existing_bid.id,
            db=object(),
        )
    assert exc_info.value.detail == "Bid is not awaiting seller approval"


@pytest.mark.asyncio
async def test_decline_bid_marks_lost_and_unblocks(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.ON_APPROVAL)
    lost_bid = DummyBid(bid_status=BidStatus.LOST, account_blocked=False)
    stub = BidServiceStub(get_result=existing_bid, mark_lost_result=lost_bid)
    override_bid_service(monkeypatch, stub)
    override_account_client(monkeypatch, AccountClientStub())
    publisher = override_publisher(monkeypatch, PublisherStub())

    result = await admin.decline_bid(
        bid_id=existing_bid.id,
        db=object(),
    )

    assert result is lost_bid
    assert stub.mark_bid_as_lost_calls == [{"bid_id": existing_bid.id, "auction_result_bid": None}]
    assert publisher.publish_calls[0][0] == "bid.you_lost_bid"
