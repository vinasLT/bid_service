from typing import Sequence

from sqlalchemy import Select, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models import Bid
from app.database.schemas.bid import BidCreate, BidUpdate
from app.schemas.bid import Auctions, BidStatus


class BidService(BaseService[Bid, BidCreate, BidUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Bid, session)

    async def get_all_by_user_uuid(
        self, user_uuid: str, get_stmt: bool = False
    ) -> Select[tuple[Bid]] | Sequence[Bid]:
        stmt = select(Bid).where(Bid.user_uuid == user_uuid)
        if get_stmt:
            return stmt
        result = await self.session.execute(stmt)
        return result.scalars().all()


    async def get_by_user_uuid_and_id(self, user_uuid: str, bid_id: int) -> Bid | None:
        stmt = (
            select(Bid)
            .where(Bid.user_uuid == user_uuid, Bid.id == bid_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_bid_for_lot(
        self, user_uuid: str, auction: Auctions, lot_id: int
    ) -> Bid | None:
        stmt = (
            select(Bid)
            .where(
                Bid.user_uuid == user_uuid,
                Bid.auction == auction,
                Bid.lot_id == lot_id,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_highest_bid_for_lot(
        self, auction: Auctions, lot_id: int
    ) -> Bid | None:
        stmt = (
            select(Bid)
            .where(Bid.auction == auction, Bid.lot_id == lot_id)
            .order_by(Bid.bid_amount.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_paginated(
        self, page: int, per_page: int
    ) -> tuple[Sequence[Bid], int]:
        offset = (page - 1) * per_page

        count_stmt = select(func.count()).select_from(Bid)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Bid)
            .order_by(Bid.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.session.execute(stmt)
        bids = result.scalars().all()
        return bids, total

    def build_admin_query(
        self,
        bid_status: BidStatus | None = None,
        auction: Auctions | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Select:
        stmt = select(Bid)
        conditions = []

        if bid_status:
            conditions.append(Bid.bid_status == bid_status)
        if auction:
            conditions.append(Bid.auction == auction)
        if search:
            search_like = f"%{search}%"
            search_conditions = [
                Bid.vin.ilike(search_like),
                Bid.title.ilike(search_like),
            ]
            if search.isdigit():
                search_conditions.append(Bid.lot_id == int(search))
            conditions.append(or_(*search_conditions))

        if conditions:
            stmt = stmt.where(*conditions)

        sort_order = sort_order.lower()
        sort_field = Bid.created_at
        if sort_by == "auction_date":
            sort_field = Bid.auction_date
        elif sort_by == "bid_amount":
            sort_field = Bid.bid_amount

        if sort_order == "asc":
            stmt = stmt.order_by(sort_field.asc())
        else:
            stmt = stmt.order_by(sort_field.desc())

        return stmt

    async def mark_bid_as_won(
        self,
        bid_id: int,
        auction_result_bid: int | None = None,
    ) -> Bid | None:
        bid = await self.get(bid_id)
        if not bid:
            return None

        bid.bid_status = BidStatus.WON
        if auction_result_bid is not None:
            bid.auction_result_bid = auction_result_bid

        await self.session.commit()
        await self.session.refresh(bid)
        return bid

    async def mark_bid_as_lost(
        self,
        bid_id: int,
        auction_result_bid: int | None = None,
    ) -> Bid | None:
        bid = await self.get(bid_id)
        if not bid:
            return None

        bid.bid_status = BidStatus.LOST
        if auction_result_bid is not None:
            bid.auction_result_bid = auction_result_bid

        await self.session.commit()
        await self.session.refresh(bid)
        return bid
