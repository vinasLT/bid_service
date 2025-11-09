from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TransactionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRANSACTION_TYPE_UNSPECIFIED: _ClassVar[TransactionType]
    TRANSACTION_TYPE_PLAN_PURCHASE: _ClassVar[TransactionType]
    TRANSACTION_TYPE_BID_PLACEMENT: _ClassVar[TransactionType]
    TRANSACTION_TYPE_ADJUSTMENT: _ClassVar[TransactionType]
TRANSACTION_TYPE_UNSPECIFIED: TransactionType
TRANSACTION_TYPE_PLAN_PURCHASE: TransactionType
TRANSACTION_TYPE_BID_PLACEMENT: TransactionType
TRANSACTION_TYPE_ADJUSTMENT: TransactionType

class GetCheckoutLinkRequest(_message.Message):
    __slots__ = ("purpose", "purpose_external_id", "success_link", "cancel_link", "user_external_id", "source")
    PURPOSE_FIELD_NUMBER: _ClassVar[int]
    PURPOSE_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_LINK_FIELD_NUMBER: _ClassVar[int]
    CANCEL_LINK_FIELD_NUMBER: _ClassVar[int]
    USER_EXTERNAL_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    purpose: str
    purpose_external_id: str
    success_link: str
    cancel_link: str
    user_external_id: str
    source: str
    def __init__(self, purpose: _Optional[str] = ..., purpose_external_id: _Optional[str] = ..., success_link: _Optional[str] = ..., cancel_link: _Optional[str] = ..., user_external_id: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...

class GetCheckoutLinkResponse(_message.Message):
    __slots__ = ("link",)
    LINK_FIELD_NUMBER: _ClassVar[int]
    link: str
    def __init__(self, link: _Optional[str] = ...) -> None: ...

class CreateNewTransactionRequest(_message.Message):
    __slots__ = ("user_uuid", "plan_id", "transaction_type", "amount")
    USER_UUID_FIELD_NUMBER: _ClassVar[int]
    PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    user_uuid: str
    plan_id: int
    transaction_type: TransactionType
    amount: int
    def __init__(self, user_uuid: _Optional[str] = ..., plan_id: _Optional[int] = ..., transaction_type: _Optional[_Union[TransactionType, str]] = ..., amount: _Optional[int] = ...) -> None: ...

class CreateNewTransactionResponse(_message.Message):
    __slots__ = ("user_account_id", "plan_id", "transaction_type", "amount")
    USER_ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    user_account_id: int
    plan_id: int
    transaction_type: TransactionType
    amount: int
    def __init__(self, user_account_id: _Optional[int] = ..., plan_id: _Optional[int] = ..., transaction_type: _Optional[_Union[TransactionType, str]] = ..., amount: _Optional[int] = ...) -> None: ...

class Plan(_message.Message):
    __slots__ = ("name", "description", "max_bid_one_time", "bid_power", "price")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    MAX_BID_ONE_TIME_FIELD_NUMBER: _ClassVar[int]
    BID_POWER_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    max_bid_one_time: int
    bid_power: int
    price: int
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ..., max_bid_one_time: _Optional[int] = ..., bid_power: _Optional[int] = ..., price: _Optional[int] = ...) -> None: ...

class GetUserAccountRequest(_message.Message):
    __slots__ = ("user_uuid",)
    USER_UUID_FIELD_NUMBER: _ClassVar[int]
    user_uuid: str
    def __init__(self, user_uuid: _Optional[str] = ...) -> None: ...

class GetUserAccountResponse(_message.Message):
    __slots__ = ("user_uuid", "balance", "plan")
    USER_UUID_FIELD_NUMBER: _ClassVar[int]
    BALANCE_FIELD_NUMBER: _ClassVar[int]
    PLAN_FIELD_NUMBER: _ClassVar[int]
    user_uuid: str
    balance: int
    plan: Plan
    def __init__(self, user_uuid: _Optional[str] = ..., balance: _Optional[int] = ..., plan: _Optional[_Union[Plan, _Mapping]] = ...) -> None: ...
