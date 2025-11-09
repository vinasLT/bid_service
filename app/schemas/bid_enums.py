from enum import Enum


class Auctions(str, Enum):
    COPART = "copart"
    IAAI = "iaai"


class BidStatus(str, Enum):
    WAITING_AUCTION_RESULT = "waiting_auction_result"
    WON = "won"
    LOST = "lost"
