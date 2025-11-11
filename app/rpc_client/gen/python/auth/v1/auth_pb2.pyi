from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GetUserRequest(_message.Message):
    __slots__ = ("user_uuid",)
    USER_UUID_FIELD_NUMBER: _ClassVar[int]
    user_uuid: str
    def __init__(self, user_uuid: _Optional[str] = ...) -> None: ...

class GetUserResponse(_message.Message):
    __slots__ = ("first_name", "last_name", "language", "email", "username", "phone_number", "is_active", "phone_verified", "email_verified")
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    PHONE_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    EMAIL_VERIFIED_FIELD_NUMBER: _ClassVar[int]
    first_name: str
    last_name: str
    language: str
    email: str
    username: str
    phone_number: str
    is_active: bool
    phone_verified: bool
    email_verified: bool
    def __init__(self, first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., language: _Optional[str] = ..., email: _Optional[str] = ..., username: _Optional[str] = ..., phone_number: _Optional[str] = ..., is_active: bool = ..., phone_verified: bool = ..., email_verified: bool = ...) -> None: ...
