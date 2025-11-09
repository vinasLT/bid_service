from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace

from app.routers.v1.bid import admin, user
from app.schemas.bid import Auctions, BidStatus


@dataclass
class DummyBid:
    id: int = 1
    lot_id: int = 9001
    auction: Auctions = Auctions.COPART
    user_uuid: str = "user-123"
    bid_status: BidStatus = BidStatus.WAITING_AUCTION_RESULT
    bid_amount: int = 10_000
    auction_result_bid: int | None = None
    title: str = "Some vehicle"
    images: str = "first.jpg,second.jpg"
    auction_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    vin: str = "VINCODE123"


class BidServiceStub:
    def __init__(
        self,
        *,
        get_result: DummyBid | None = None,
        mark_won_result: DummyBid | None = None,
        mark_lost_result: DummyBid | None = None,
    ):
        self.db = None
        self.get_result = get_result
        self.mark_won_result = mark_won_result
        self.mark_lost_result = mark_lost_result
        self.mark_bid_as_won_calls: list[dict] = []
        self.mark_bid_as_lost_calls: list[dict] = []
        self.update_calls: list[tuple] = []
        self.build_query_kwargs: dict | None = None
        self.last_get_id: int | None = None

    async def get(self, bid_id: int):
        self.last_get_id = bid_id
        return self.get_result

    def build_admin_query(self, **kwargs):
        self.build_query_kwargs = kwargs
        return SimpleNamespace(name="admin-query")

    async def mark_bid_as_won(self, bid_id: int, auction_result_bid: int | None = None):
        self.mark_bid_as_won_calls.append(
            {"bid_id": bid_id, "auction_result_bid": auction_result_bid}
        )
        return self.mark_won_result

    async def mark_bid_as_lost(
        self,
        bid_id: int,
        auction_result_bid: int | None = None,
    ):
        self.mark_bid_as_lost_calls.append(
            {"bid_id": bid_id, "auction_result_bid": auction_result_bid}
        )
        return self.mark_lost_result

    async def update(self, bid_id: int, data):
        self.update_calls.append((bid_id, data))
        return self.get_result


class PublisherStub:
    def __init__(self, *, publish_exception: Exception | None = None):
        self.publish_exception = publish_exception
        self.connected = False
        self.closed = False
        self.publish_calls: list[tuple[str, dict]] = []

    async def connect(self):
        self.connected = True

    async def publish(self, routing_key: str, payload: dict):
        self.publish_calls.append((routing_key, payload))
        if self.publish_exception:
            raise self.publish_exception

    async def close(self):
        self.closed = True


class AccountClientStub:
    def __init__(
        self,
        *,
        exc: Exception | None = None,
        info_exc: Exception | None = None,
        transaction_exc: Exception | None = None,
        account_info: SimpleNamespace | None = None,
    ):
        # `exc` kept for backwards compatibility, behaving like transaction_exc
        if exc and transaction_exc is None:
            transaction_exc = exc
        self.info_exc = info_exc
        self.transaction_exc = transaction_exc
        self.account_info = account_info or SimpleNamespace(balance=0)
        self.calls: list[dict] = []
        self.account_info_calls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get_account_info(self, user_uuid: str):
        self.account_info_calls.append(user_uuid)
        if self.info_exc:
            raise self.info_exc
        return self.account_info

    async def create_transaction(
        self,
        user_uuid: str,
        transaction_type,
        amount: int,
        plan_id=None,
    ):
        self.calls.append(
            {
                "user_uuid": user_uuid,
                "transaction_type": transaction_type,
                "amount": amount,
                "plan_id": plan_id,
            }
        )
        if self.transaction_exc:
            raise self.transaction_exc


class BidPlacementServiceStub:
    def __init__(
        self,
        *,
        highest_bid: DummyBid | None = None,
        user_bid: DummyBid | None = None,
        create_result: DummyBid | None = None,
    ):
        self.highest_bid = highest_bid
        self.user_bid = user_bid
        self.create_result = create_result
        self.highest_calls: list[tuple] = []
        self.user_bid_calls: list[tuple] = []
        self.create_calls: list = []

    async def get_highest_bid_for_lot(self, auction, lot_id):
        self.highest_calls.append((auction, lot_id))
        return self.highest_bid

    async def get_user_bid_for_lot(self, user_uuid, auction, lot_id):
        self.user_bid_calls.append((user_uuid, auction, lot_id))
        return self.user_bid

    async def create(self, bid_create):
        self.create_calls.append(bid_create)
        return self.create_result


class ApiRpcClientStub:
    def __init__(
        self,
        *,
        lot_items: list | None = None,
        current_bid_amount: int = 0,
        rpc_error: Exception | None = None,
    ):
        self.lot_items = lot_items or []
        self.current_bid_amount = current_bid_amount
        self.rpc_error = rpc_error
        self.get_lot_calls: list[dict] = []
        self.get_current_bid_calls: list[dict] = []

    async def __aenter__(self):
        if self.rpc_error:
            raise self.rpc_error
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get_lot_by_vin_or_lot_id(self, vin_or_lot_id: str, site: str):
        if self.rpc_error:
            raise self.rpc_error
        self.get_lot_calls.append({"vin_or_lot_id": vin_or_lot_id, "site": site})
        return SimpleNamespace(lot=self.lot_items)

    async def get_current_bid(self, lot_id: int, site: str):
        if self.rpc_error:
            raise self.rpc_error
        self.get_current_bid_calls.append({"lot_id": lot_id, "site": site})
        current_bid = SimpleNamespace(pre_bid=self.current_bid_amount)
        return SimpleNamespace(current_bid=current_bid)


def override_bid_service(monkeypatch, stub: BidServiceStub):
    monkeypatch.setattr(admin, "BidService", lambda db: stub)
    return stub


def override_publisher(monkeypatch, stub: PublisherStub):
    monkeypatch.setattr(admin, "RabbitMQPublisher", lambda: stub)
    return stub


def override_account_client(monkeypatch, stub: AccountClientStub):
    monkeypatch.setattr(admin, "AccountRpcClient", lambda: stub)
    return stub


def override_user_bid_service(monkeypatch, stub: BidPlacementServiceStub):
    monkeypatch.setattr(user, "BidService", lambda db: stub)
    return stub


def override_user_publisher(monkeypatch, stub: PublisherStub):
    monkeypatch.setattr(user, "RabbitMQPublisher", lambda: stub)
    return stub


def override_user_account_client(monkeypatch, stub: AccountClientStub):
    monkeypatch.setattr(user, "AccountRpcClient", lambda: stub)
    return stub


def override_auction_client(monkeypatch, stub: ApiRpcClientStub):
    monkeypatch.setattr(user, "ApiRpcClient", lambda: stub)
    return stub
