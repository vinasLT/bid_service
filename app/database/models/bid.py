from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base
from app.schemas.bid import Auctions, BidStatus


class Bid(Base):
    __tablename__ = "bid"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(nullable=False)
    auction: Mapped[Auctions] = mapped_column(Enum(Auctions),nullable=False)
    user_uuid: Mapped[str] = mapped_column(nullable=False)

    bid_status: Mapped[BidStatus] = mapped_column(Enum(BidStatus), nullable=False, default=BidStatus.WAITING_AUCTION_RESULT)

    bid_amount: Mapped[int] = mapped_column(nullable=False)
    auction_result_bid: Mapped[int] = mapped_column(nullable=True)

    #lot_data
    title: Mapped[str] = mapped_column(nullable=True)
    auction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    vin: Mapped[str] = mapped_column(nullable=True)
    images: Mapped[str] = mapped_column(nullable=True)
    odometer: Mapped[int] = mapped_column(nullable=True)
    location: Mapped[str] = mapped_column(nullable=True)
    damage_pr: Mapped[str] = mapped_column(nullable=True)
    damage_sec: Mapped[str] = mapped_column(nullable=True)

    fuel: Mapped[str] = mapped_column(nullable=True)
    transmission: Mapped[str] = mapped_column(nullable=True)
    engine_size: Mapped[str] = mapped_column(nullable=True)
    cylinders: Mapped[str] = mapped_column(nullable=True)

    seller: Mapped[str] = mapped_column(nullable=True)
    document: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )



