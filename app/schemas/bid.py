from pydantic import BaseModel, Field

from app.core.utils import create_pagination_page
from app.database.schemas.bid import BidRead
from app.schemas.bid_enums import Auctions, BidStatus, PaymentStatus


class BidIn(BaseModel):
    lot_id: int
    auction: Auctions
    bid_amount: int


class BidWinRequest(BaseModel):
    auction_result_bid: int | None = Field(default=None, ge=0)


class BidLostRequest(BaseModel):
    auction_result_bid: int | None = Field(default=None, ge=0)


class BidOnApprovalRequest(BaseModel):
    auction_result_bid: int | None = Field(default=None, ge=0)


class BidFilters(BaseModel):
    bid_status: BidStatus | None = Field(default=None)
    auction: Auctions | None = Field(default=None)
    search: str | None = Field(default=None, min_length=1, description="Search by lot id, VIN or title")
    sort_by: str = Field(
        default="created_at",
        pattern="^(created_at|auction_date|bid_amount)$",
    )
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
    )

class GetMyBidIn(BaseModel):
    auction: Auctions = Field(..., description='Auction')
    lot_id: int = Field(..., description='Lot ID')

BidPage = create_pagination_page(BidRead)
