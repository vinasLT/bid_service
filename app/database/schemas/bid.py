from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.bid_enums import Auctions, BidStatus, PaymentStatus


class BidBase(BaseModel):
    lot_id: int
    auction: Auctions
    bid_amount: int
    bid_status: BidStatus = BidStatus.WAITING_AUCTION_RESULT
    payment_status: PaymentStatus = PaymentStatus.NOT_REQUIRED
    account_blocked: bool = False
    is_buy_now: bool = False
    auction_result_bid: int | None = None

    title: str | None = None
    auction_date: datetime | None = None
    vin: str | None = None
    images: str | None = None
    odometer: int | None = None
    location: str | None = None
    damage_pr: str | None = None
    damage_sec: str | None = None
    fuel: str | None = None
    transmission: str | None = None
    engine_size: str | None = None
    cylinders: str | None = None

    seller: str | None = None
    document: str | None = None
    status: str | None = None


class BidCreate(BidBase):
    user_uuid: str


class BidUpdate(BaseModel):
    lot_id: int | None = None
    auction: Auctions | None = None
    user_uuid: str | None = None
    bid_amount: int | None = None
    bid_status: BidStatus | None = None
    payment_status: PaymentStatus | None = None
    account_blocked: bool | None = None
    is_buy_now: bool | None = None
    auction_result_bid: int | None = None

    title: str | None = None
    auction_date: datetime | None = None
    vin: str | None = None
    images: str | None = None
    odometer: int | None = None
    location: str | None = None
    damage_pr: str | None = None
    damage_sec: str | None = None
    fuel: str | None = None
    transmission: str | None = None
    engine_size: str | None = None
    cylinders: str | None = None

    seller: str | None = None
    document: str | None = None
    status: str | None = None


class BidRead(BidBase):
    id: int
    user_uuid: str
    images: list[str] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("images", mode="before")
    @classmethod
    def split_images(cls, value):
        if isinstance(value, str) and value:
            return value.split(",")
        if isinstance(value, list):
            return value
        return None
