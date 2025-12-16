from enum import Enum


class Auctions(str, Enum):
    COPART = "copart"
    IAAI = "iaai"


class BidStatus(str, Enum):
    WAITING_AUCTION_RESULT = "waiting_auction_result"
    ON_APPROVAL = "on_approval"
    WON = "won"
    LOST = "lost"


class PaymentStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    PAID = "paid"
