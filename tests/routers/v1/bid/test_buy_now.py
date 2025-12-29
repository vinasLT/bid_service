from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from rfc9457 import BadRequestProblem

from app.routers.v1.bid import user
from app.schemas.bid import BuyNowIn
from app.schemas.bid_enums import Auctions, BidStatus, PaymentStatus
from tests.routers.v1.bid.stubs import (
    ApiRpcClientStub,
    AccountClientStub,
    AuthClientStub,
    BidPlacementServiceStub,
    DummyBid,
    PublisherStub,
    override_auction_client,
    override_user_account_client,
    override_user_auth_client,
    override_user_bid_service,
    override_user_publisher,
)


def _make_lot_data(**overrides):
    defaults = {
        "form_get_type": "auction",
        "link_img_hd": ("img_hd_1.jpg",),
        "link_img_small": ("thumb_1.jpg",),
        "title": "Buy Now Vehicle",
        "auction_date": datetime.now(timezone.utc) + timedelta(days=1),
        "vin": "VINBUY123",
        "odometer": 12000,
        "location": "Some Yard",
        "location_offsite": None,
        "damage_pr": "front",
        "damage_sec": "side",
        "fuel": "gasoline",
        "transmission": "automatic",
        "engine_size": "2.0",
        "cylinders": "4",
        "vehicle_type": "car",
        "seller": "Seller Inc",
        "document": "Clean",
        "status": "run_and_drive",
        "is_buynow": True,
        "price_new": 15_000,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _setup_defaults(
    monkeypatch,
    *,
    api_stub=None,
    account_stub=None,
    bid_stub=None,
    publisher_stub=None,
    auth_stub=None,
):
    override_auction_client(monkeypatch, api_stub or ApiRpcClientStub(lot_items=[_make_lot_data()]))
    override_user_account_client(
        monkeypatch,
        account_stub
        or AccountClientStub(account_info=SimpleNamespace(balance=50_000)),
    )
    override_user_publisher(monkeypatch, publisher_stub or PublisherStub())
    override_user_bid_service(monkeypatch, bid_stub or BidPlacementServiceStub(create_result=DummyBid()))
    override_user_auth_client(monkeypatch, auth_stub or AuthClientStub())


def _call_buy_now(data: BuyNowIn, user_uuid: str = "user-123"):
    return user.buy_now_on_auction(
        db=object(),
        data=data,
        user=SimpleNamespace(uuid=user_uuid, email="user@example.com"),
    )


@pytest.mark.asyncio
async def test_buy_now_rejects_when_buy_now_not_available(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(is_buynow=False, price_new=None)])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_buy_now(BuyNowIn(lot_id=1, auction=Auctions.COPART))

    assert exc_info.value.detail == "Buy now is not available for this lot"


@pytest.mark.asyncio
async def test_buy_now_creates_bid_and_publishes_notification(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    created_bid = DummyBid(
        bid_amount=15_000,
        bid_status=BidStatus.WON,
        payment_status=PaymentStatus.PENDING,
        account_blocked=True,
        is_buy_now=True,
    )
    bid_stub = BidPlacementServiceStub(create_result=created_bid)
    account_stub = AccountClientStub(account_info=SimpleNamespace(balance=20_000))
    publisher_stub = PublisherStub()
    auth_stub = AuthClientStub(email="user@example.com", phone_number="+1234567890")

    _setup_defaults(
        monkeypatch,
        api_stub=api_stub,
        bid_stub=bid_stub,
        account_stub=account_stub,
        publisher_stub=publisher_stub,
        auth_stub=auth_stub,
    )

    data = BuyNowIn(lot_id=20, auction=Auctions.COPART)
    result = await _call_buy_now(data, user_uuid="user-xyz")

    assert result is created_bid
    assert bid_stub.create_calls, "Expected buy now bid creation"
    created_payload = bid_stub.create_calls[0]
    assert created_payload.is_buy_now is True
    assert created_payload.bid_amount == 15_000

    assert account_stub.account_info_calls == ["user-xyz"]
    assert account_stub.calls and account_stub.calls[0]["amount"] == -15_000

    routing_key, payload = publisher_stub.publish_calls[0]
    assert routing_key == "bid.you_won_bid"
    assert payload["bid_status"] == "won"
    assert payload["payment_status"] == "pending"
    assert payload["account_blocked"] is True
    assert payload["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_buy_now_rejects_when_lot_not_found(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_buy_now(BuyNowIn(lot_id=2, auction=Auctions.COPART))

    assert exc_info.value.detail == "Lot not found"


@pytest.mark.asyncio
async def test_buy_now_rejects_closed_auction(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(form_get_type="history")])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_buy_now(BuyNowIn(lot_id=3, auction=Auctions.COPART))

    assert exc_info.value.detail == "Auction is closed"


@pytest.mark.asyncio
async def test_buy_now_rejects_when_price_missing(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(price_new=None)])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_buy_now(BuyNowIn(lot_id=4, auction=Auctions.COPART))

    assert exc_info.value.detail == "Buy now is not available for this lot"


@pytest.mark.asyncio
async def test_buy_now_rejects_when_price_zero_or_negative(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(price_new=0)])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem):
        await _call_buy_now(BuyNowIn(lot_id=5, auction=Auctions.COPART))

    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(price_new=-500)])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem):
        await _call_buy_now(BuyNowIn(lot_id=6, auction=Auctions.COPART))


@pytest.mark.asyncio
async def test_buy_now_accepts_string_price(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(price_new="15000")])
    bid_stub = BidPlacementServiceStub(create_result=DummyBid(bid_amount=15_000, is_buy_now=True))
    account_stub = AccountClientStub(account_info=SimpleNamespace(balance=20_000))

    _setup_defaults(monkeypatch, api_stub=api_stub, bid_stub=bid_stub, account_stub=account_stub)

    result = await _call_buy_now(BuyNowIn(lot_id=7, auction=Auctions.COPART))

    assert result is bid_stub.create_result
    created_payload = bid_stub.create_calls[0]
    assert created_payload.bid_amount == 15_000


@pytest.mark.asyncio
async def test_buy_now_rejects_when_no_plan(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    account_stub = AccountClientStub(account_info=SimpleNamespace(balance=20_000, plan=None))
    _setup_defaults(monkeypatch, api_stub=api_stub, account_stub=account_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_buy_now(BuyNowIn(lot_id=8, auction=Auctions.COPART))

    assert exc_info.value.detail == "You need to buy plan for biding"


@pytest.mark.asyncio
async def test_buy_now_rejects_when_account_blocked(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    bid_stub = BidPlacementServiceStub(blocking=True)
    _setup_defaults(monkeypatch, api_stub=api_stub, bid_stub=bid_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_buy_now(BuyNowIn(lot_id=9, auction=Auctions.COPART))

    assert exc_info.value.detail == "Account is blocked until payment is completed"


@pytest.mark.asyncio
async def test_buy_now_rejects_when_user_already_has_bid(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    bid_stub = BidPlacementServiceStub(user_bid=DummyBid())
    _setup_defaults(monkeypatch, api_stub=api_stub, bid_stub=bid_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_buy_now(BuyNowIn(lot_id=10, auction=Auctions.COPART))

    assert exc_info.value.detail == "You already placed a bid for this lot"


@pytest.mark.asyncio
async def test_buy_now_rejects_when_not_enough_money(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(price_new=18_000)])
    account_stub = AccountClientStub(account_info=SimpleNamespace(balance=5_000))
    _setup_defaults(monkeypatch, api_stub=api_stub, account_stub=account_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_buy_now(BuyNowIn(lot_id=11, auction=Auctions.COPART))

    assert exc_info.value.detail == "Not enough money"
