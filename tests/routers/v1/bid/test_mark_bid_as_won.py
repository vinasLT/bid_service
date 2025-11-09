import pytest
from rfc9457 import BadRequestProblem

from app.routers.v1.bid import admin
from app.schemas.bid import BidStatus, BidWinRequest
from tests.routers.v1.bid.stubs import (
    BidServiceStub,
    DummyBid,
    PublisherStub,
    override_bid_service,
    override_publisher,
)


@pytest.mark.asyncio
async def test_mark_bid_as_won_returns_400_when_missing(monkeypatch):
    stub = BidServiceStub(get_result=None)
    override_bid_service(monkeypatch, stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_won(
            bid_id=10,
            win_data=BidWinRequest(auction_result_bid=5000),
            db=object(),
        )
    assert exc_info.value.detail == "Bid not found"


@pytest.mark.asyncio
async def test_mark_bid_as_won_rejects_already_won_bids(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.WON)
    stub = BidServiceStub(get_result=existing_bid)
    override_bid_service(monkeypatch, stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_won(
            bid_id=existing_bid.id,
            win_data=BidWinRequest(auction_result_bid=existing_bid.bid_amount),
            db=object(),
        )
    assert exc_info.value.detail == "Bid already marked as won"


@pytest.mark.asyncio
async def test_mark_bid_as_won_returns_400_when_service_cannot_update(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.WAITING_AUCTION_RESULT)
    stub = BidServiceStub(get_result=existing_bid, mark_won_result=None)
    override_bid_service(monkeypatch, stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_won(
            bid_id=existing_bid.id,
            win_data=BidWinRequest(auction_result_bid=existing_bid.bid_amount),
            db=object(),
        )
    assert exc_info.value.detail == "Bid not found"


@pytest.mark.asyncio
async def test_mark_bid_as_won_marks_bid_and_notifies(monkeypatch):
    existing_bid = DummyBid()
    won_bid = DummyBid(bid_status=BidStatus.WON, auction_result_bid=11_000)
    stub = BidServiceStub(get_result=existing_bid, mark_won_result=won_bid)
    override_bid_service(monkeypatch, stub)

    publisher = override_publisher(monkeypatch, PublisherStub())

    result = await admin.mark_bid_as_won(
        bid_id=existing_bid.id,
        win_data=BidWinRequest(auction_result_bid=won_bid.auction_result_bid),
        db=object(),
    )

    assert result is won_bid
    assert stub.mark_bid_as_won_calls == [
        {"bid_id": existing_bid.id, "auction_result_bid": won_bid.auction_result_bid}
    ]
    assert publisher.connected is True
    assert publisher.closed is True
    assert publisher.publish_calls and publisher.publish_calls[0][0] == "notification.bid.won"
    payload = publisher.publish_calls[0][1]
    assert payload["bid_status"] == BidStatus.WON.value
    assert payload["vehicle_image"] == "first.jpg"


@pytest.mark.asyncio
async def test_mark_bid_as_won_rolls_back_when_notification_fails(monkeypatch):
    existing_bid = DummyBid(bid_status=BidStatus.WAITING_AUCTION_RESULT, auction_result_bid=9000)
    won_bid = DummyBid(bid_status=BidStatus.WON, auction_result_bid=9500)
    stub = BidServiceStub(get_result=existing_bid, mark_won_result=won_bid)
    override_bid_service(monkeypatch, stub)

    publisher = PublisherStub(publish_exception=RuntimeError("queue down"))
    override_publisher(monkeypatch, publisher)

    with pytest.raises(BadRequestProblem) as exc_info:
        await admin.mark_bid_as_won(
            bid_id=existing_bid.id,
            win_data=BidWinRequest(auction_result_bid=won_bid.auction_result_bid),
            db=object(),
        )
    assert exc_info.value.detail.startswith("Failed to send notification")

    assert stub.update_calls, "Expected bid rollback"
    rollback_bid_id, rollback_update = stub.update_calls[0]
    assert rollback_bid_id == existing_bid.id
    assert rollback_update.bid_status == existing_bid.bid_status
    assert rollback_update.auction_result_bid == existing_bid.auction_result_bid
    assert publisher.closed is True
