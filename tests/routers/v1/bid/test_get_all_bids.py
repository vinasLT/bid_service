import pytest
from fastapi_pagination import Params

from app.routers.v1.bid import admin
from app.schemas.bid import Auctions, BidAdminFilters, BidStatus
from tests.routers.v1.bid.stubs import BidServiceStub, override_bid_service


@pytest.mark.asyncio
async def test_get_all_bids_passes_filters_and_params(monkeypatch):
    stub = BidServiceStub()
    override_bid_service(monkeypatch, stub)

    captured = {}

    async def fake_paginate(db, query, params):
        captured["db"] = db
        captured["query"] = query
        captured["params"] = params
        return {"data": ["bid"], "count": 1}

    monkeypatch.setattr(admin, "paginate", fake_paginate)

    filters = BidAdminFilters(
        bid_status=BidStatus.WON,
        auction=Auctions.IAAI,
        search="VINCODE",
        sort_by="bid_amount",
        sort_order="asc",
    )

    params = Params(page=3, size=25)
    db_session = object()

    result = await admin.get_all_bids(
        params=params,
        filters=filters,
        db=db_session,
        _=None,
    )

    assert result == {"data": ["bid"], "count": 1}
    assert captured["db"] is db_session
    assert captured["query"].name == "admin-query"
    assert captured["params"] is params
    assert stub.build_query_kwargs == filters.model_dump(exclude_none=True)
