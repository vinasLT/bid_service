from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import grpc
import pytest
from fastapi_pagination import Params
from rfc9457 import BadRequestProblem

from app.routers.v1.bid import user
from app.schemas.bid import BidIn, BidFilters, GetMyBidIn
from app.schemas.bid_enums import Auctions, BidStatus
from tests.routers.v1.bid.stubs import (
    ApiRpcClientStub,
    AccountClientStub,
    BidPlacementServiceStub,
    DummyBid,
    PublisherStub,
    override_auction_client,
    override_user_account_client,
    override_user_bid_service,
    override_user_publisher,
)


def _make_lot_data(**overrides):
    defaults = {
        "form_get_type": "auction",
        "link_img_hd": ("img_hd_1.jpg", "img_hd_2.jpg"),
        "link_img_small": ("thumb_1.jpg",),
        "title": "Clean Title Vehicle",
        "auction_date": datetime.now(timezone.utc) + timedelta(days=1),
        "vin": "VIN123",
        "odometer": 12000,
        "location": "Some Yard",
        "damage_pr": "front",
        "damage_sec": "side",
        "fuel": "gasoline",
        "transmission": "automatic",
        "engine_size": "2.0",
        "cylinders": "4",
        "seller": "Seller Inc",
        "document": "Clean",
        "status": "run_and_drive",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _setup_defaults(monkeypatch, *, api_stub=None, account_stub=None, bid_stub=None, publisher_stub=None):
    override_auction_client(monkeypatch, api_stub or ApiRpcClientStub(lot_items=[_make_lot_data()]))
    override_user_account_client(
        monkeypatch,
        account_stub
        or AccountClientStub(account_info=SimpleNamespace(balance=50_000)),
    )
    override_user_publisher(monkeypatch, publisher_stub or PublisherStub())
    override_user_bid_service(monkeypatch, bid_stub or BidPlacementServiceStub(create_result=DummyBid()))


def _call_bid_on_auction(data: BidIn, user_uuid: str = "user-123"):
    return user.bid_on_auction(
        db=object(),
        data=data,
        user=SimpleNamespace(uuid=user_uuid, email="user@example.com"),
    )


@pytest.mark.asyncio
async def test_bid_on_auction_raises_when_lot_not_found(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=1, auction=Auctions.COPART, bid_amount=5_000))
    assert exc_info.value.detail == "Lot not found"


@pytest.mark.asyncio
async def test_bid_on_auction_rejects_closed_auction(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(form_get_type="history")])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=5, auction=Auctions.COPART, bid_amount=7_000))
    assert exc_info.value.detail == "Auction is closed"


@pytest.mark.asyncio
async def test_bid_on_auction_rejects_when_auction_starts_within_cutoff(monkeypatch):
    auction_date = datetime.now(timezone.utc) + timedelta(minutes=10)
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data(auction_date=auction_date)])
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=6, auction=Auctions.COPART, bid_amount=7_500))
    assert exc_info.value.detail == "Auction starts in less than 15 minutes"


@pytest.mark.asyncio
async def test_bid_on_auction_rejects_when_current_bid_is_higher(monkeypatch):
    api_stub = ApiRpcClientStub(
        lot_items=[_make_lot_data()],
        current_bid_amount=11_000,
    )
    _setup_defaults(monkeypatch, api_stub=api_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=8, auction=Auctions.COPART, bid_amount=10_000))
    assert exc_info.value.detail == "Current bid on auction is higher"


@pytest.mark.asyncio
async def test_bid_on_auction_rejects_when_account_blocked(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    bid_stub = BidPlacementServiceStub(blocking=True)
    _setup_defaults(monkeypatch, api_stub=api_stub, bid_stub=bid_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=9, auction=Auctions.COPART, bid_amount=6_000))

    assert exc_info.value.detail == "Account is blocked until payment is completed"
    assert bid_stub.blocking_checks == ["user-123"]


@pytest.mark.asyncio
async def test_bid_on_auction_rejects_when_not_enough_money(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    account_stub = AccountClientStub(account_info=SimpleNamespace(balance=3_000))
    bid_stub = BidPlacementServiceStub(create_result=DummyBid(bid_amount=6_000))
    _setup_defaults(monkeypatch, api_stub=api_stub, account_stub=account_stub, bid_stub=bid_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=3, auction=Auctions.COPART, bid_amount=6_000))
    assert exc_info.value.detail == "Not enough money"
    assert not bid_stub.create_calls


@pytest.mark.asyncio
async def test_bid_on_auction_requires_plan(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    account_stub = AccountClientStub(
        account_info=SimpleNamespace(balance=5_000, plan=None),
    )
    _setup_defaults(monkeypatch, api_stub=api_stub, account_stub=account_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=4, auction=Auctions.COPART, bid_amount=4_000))

    assert exc_info.value.detail == "You need to buy plan for biding"


@pytest.mark.asyncio
async def test_bid_on_auction_respects_plan_bid_limit(monkeypatch):
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    account_stub = AccountClientStub(
        account_info=SimpleNamespace(
            balance=8_000,
            plan=SimpleNamespace(max_bid_one_time=2),
        ),
    )
    bid_stub = BidPlacementServiceStub(bids_count=2)
    _setup_defaults(
        monkeypatch,
        api_stub=api_stub,
        account_stub=account_stub,
        bid_stub=bid_stub,
    )

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=7, auction=Auctions.COPART, bid_amount=4_000))

    assert exc_info.value.detail == "You can place up to 2 bids at one time"
    assert bid_stub.bids_count_calls == ["user-123"]


@pytest.mark.asyncio
async def test_bid_on_auction_rejects_when_someone_already_has_higher_bid(monkeypatch):
    highest_bid = DummyBid(bid_amount=12_000, user_uuid="other-user")
    bid_stub = BidPlacementServiceStub(highest_bid=highest_bid)
    _setup_defaults(monkeypatch, bid_stub=bid_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=10, auction=Auctions.COPART, bid_amount=11_000))
    assert exc_info.value.detail == "Someone already placed a higher bid for this lot"
    assert bid_stub.user_bid_calls == []
    assert bid_stub.create_calls == []


@pytest.mark.asyncio
async def test_bid_on_auction_rejects_when_previous_user_bid_is_higher(monkeypatch):
    previous_bid = DummyBid(bid_amount=9_000)
    bid_stub = BidPlacementServiceStub(highest_bid=None, user_bid=previous_bid)
    _setup_defaults(monkeypatch, bid_stub=bid_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=12, auction=Auctions.COPART, bid_amount=8_500))
    assert exc_info.value.detail == "Your previous bid is higher"
    assert bid_stub.create_calls == []


@pytest.mark.asyncio
async def test_bid_on_auction_raises_when_bid_not_created(monkeypatch):
    bid_stub = BidPlacementServiceStub(create_result=None)
    _setup_defaults(monkeypatch, bid_stub=bid_stub)

    with pytest.raises(BadRequestProblem) as exc_info:
        await _call_bid_on_auction(BidIn(lot_id=14, auction=Auctions.COPART, bid_amount=9_000))
    assert exc_info.value.detail == "Bid was not created"


@pytest.mark.asyncio
async def test_bid_on_auction_creates_bid_and_publishes_notification(monkeypatch):
    api_stub = ApiRpcClientStub(
        lot_items=[_make_lot_data(auction_date=datetime.now(timezone.utc) + timedelta(days=2))],
        current_bid_amount=4_500,
    )
    created_bid = DummyBid(bid_amount=6_000)
    bid_stub = BidPlacementServiceStub(create_result=created_bid)
    account_stub = AccountClientStub(account_info=SimpleNamespace(balance=20_000))
    publisher_stub = PublisherStub()

    _setup_defaults(
        monkeypatch,
        api_stub=api_stub,
        bid_stub=bid_stub,
        account_stub=account_stub,
        publisher_stub=publisher_stub,
    )

    data = BidIn(lot_id=20, auction=Auctions.COPART, bid_amount=6_000)
    result = await _call_bid_on_auction(data, user_uuid="user-xyz")

    assert result is created_bid
    assert bid_stub.create_calls, "Expected bid creation call"
    created_payload = bid_stub.create_calls[0]
    assert created_payload.lot_id == data.lot_id
    assert created_payload.user_uuid == "user-xyz"
    assert created_payload.images.startswith("img_hd_1")

    assert account_stub.account_info_calls == ["user-xyz"]
    assert account_stub.calls and account_stub.calls[0]["amount"] == -data.bid_amount

    assert publisher_stub.connected is True
    assert publisher_stub.closed is True
    routing_key, payload = publisher_stub.publish_calls[0]
    assert routing_key == "bid.new_bid_placed"
    assert payload["current_bid"] == 4_500
    assert payload["vehicle_title"] == "Clean Title Vehicle"
    assert payload["vehicle_image"] == "img_hd_1.jpg"


@pytest.mark.asyncio
async def test_bid_on_auction_raises_rpc_problem_when_auction_client_fails(monkeypatch):
    rpc_error = grpc.aio.AioRpcError(grpc.StatusCode.INTERNAL, None, None)
    api_stub = ApiRpcClientStub(rpc_error=rpc_error)
    _setup_defaults(monkeypatch, api_stub=api_stub)

    captured = {}

    def fake_raise_rpc_problem(service_name, exc):
        captured["service_name"] = service_name
        captured["exc"] = exc
        raise RuntimeError("rpc raised")

    monkeypatch.setattr(user, "raise_rpc_problem", fake_raise_rpc_problem)

    with pytest.raises(RuntimeError, match="rpc raised"):
        await _call_bid_on_auction(BidIn(lot_id=30, auction=Auctions.COPART, bid_amount=5_000))
    assert captured["service_name"] == "Auction"
    assert captured["exc"] is rpc_error


@pytest.mark.asyncio
async def test_bid_on_auction_raises_rpc_problem_when_account_client_fails(monkeypatch):
    rpc_error = grpc.aio.AioRpcError(grpc.StatusCode.INTERNAL, None, None)
    api_stub = ApiRpcClientStub(lot_items=[_make_lot_data()])
    account_stub = AccountClientStub(info_exc=rpc_error)
    _setup_defaults(monkeypatch, api_stub=api_stub, account_stub=account_stub)

    captured = {}

    def fake_raise_rpc_problem(service_name, exc):
        captured["service_name"] = service_name
        captured["exc"] = exc
        raise RuntimeError("account rpc")

    monkeypatch.setattr(user, "raise_rpc_problem", fake_raise_rpc_problem)

    with pytest.raises(RuntimeError, match="account rpc"):
        await _call_bid_on_auction(BidIn(lot_id=40, auction=Auctions.COPART, bid_amount=8_000))
    assert captured["service_name"] == "Payment"
    assert captured["exc"] is rpc_error


@pytest.mark.asyncio
async def test_get_my_bid_returns_existing_bid(monkeypatch):
    dummy_bid = DummyBid(lot_id=123)
    stub = BidPlacementServiceStub(user_bid=dummy_bid)
    override_user_bid_service(monkeypatch, stub)

    request = GetMyBidIn(auction=Auctions.COPART, lot_id=123)
    current_user = SimpleNamespace(uuid="user-abc")

    result = await user.get_my_bid(
        db=object(),
        data=request,
        user=current_user,
    )

    assert result is dummy_bid
    assert stub.user_bid_calls == [("user-abc", request.auction, request.lot_id)]


@pytest.mark.asyncio
async def test_get_my_bid_raises_when_missing(monkeypatch):
    stub = BidPlacementServiceStub(user_bid=None)
    override_user_bid_service(monkeypatch, stub)

    request = GetMyBidIn(auction=Auctions.IAAI, lot_id=99)
    current_user = SimpleNamespace(uuid="user-missing")

    with pytest.raises(BadRequestProblem) as exc_info:
        await user.get_my_bid(db=object(), data=request, user=current_user)

    assert exc_info.value.detail == "Bid not found"
    assert stub.user_bid_calls == [("user-missing", request.auction, request.lot_id)]


@pytest.mark.asyncio
async def test_get_my_bids_applies_filters_and_paginate(monkeypatch):
    stub = BidPlacementServiceStub()
    override_user_bid_service(monkeypatch, stub)

    captured = {}

    async def fake_paginate(db, query, params):
        captured["db"] = db
        captured["query"] = query
        captured["params"] = params
        return {"data": ["bid"], "count": 1}

    monkeypatch.setattr(user, "paginate", fake_paginate)

    filters = BidFilters(
        bid_status=BidStatus.WON,
        auction=Auctions.COPART,
        search="VIN777",
        sort_by="bid_amount",
        sort_order="asc",
    )
    params = Params(page=2, size=25)
    db_session = object()
    current_user = SimpleNamespace(uuid="user-777")

    result = await user.get_my_bids(
        db=db_session,
        params=params,
        filters=filters,
        user=current_user,
    )

    assert result == {"data": ["bid"], "count": 1}
    assert stub.build_query_kwargs == filters.model_dump(exclude_none=True)
    assert captured["db"] is db_session
    assert captured["params"] is params
    assert captured["query"] is stub.query_stub

    assert stub.query_stub is not None
    assert stub.query_stub.where_calls, "Expected user filter applied to query"
    user_clause = stub.query_stub.where_calls[0][0]
    assert getattr(user_clause.right, "value", None) == current_user.uuid
