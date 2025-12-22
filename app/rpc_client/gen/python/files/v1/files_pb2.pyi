from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FileVisibility(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FILE_VISIBILITY_UNSPECIFIED: _ClassVar[FileVisibility]
    FILE_VISIBILITY_PUBLIC: _ClassVar[FileVisibility]
    FILE_VISIBILITY_PRIVATE: _ClassVar[FileVisibility]

class FileKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FILE_KIND_UNSPECIFIED: _ClassVar[FileKind]
    FILE_KIND_IMAGE: _ClassVar[FileKind]
    FILE_KIND_PDF: _ClassVar[FileKind]
    FILE_KIND_DOCUMENT: _ClassVar[FileKind]
    FILE_KIND_OTHER: _ClassVar[FileKind]
FILE_VISIBILITY_UNSPECIFIED: FileVisibility
FILE_VISIBILITY_PUBLIC: FileVisibility
FILE_VISIBILITY_PRIVATE: FileVisibility
FILE_KIND_UNSPECIFIED: FileKind
FILE_KIND_IMAGE: FileKind
FILE_KIND_PDF: FileKind
FILE_KIND_DOCUMENT: FileKind
FILE_KIND_OTHER: FileKind

class CreatePresignedUploadRequest(_message.Message):
    __slots__ = ("file_name", "mime_type", "visibility", "folder", "kind")
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    VISIBILITY_FIELD_NUMBER: _ClassVar[int]
    FOLDER_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    file_name: str
    mime_type: str
    visibility: FileVisibility
    folder: str
    kind: FileKind
    def __init__(self, file_name: _Optional[str] = ..., mime_type: _Optional[str] = ..., visibility: _Optional[_Union[FileVisibility, str]] = ..., folder: _Optional[str] = ..., kind: _Optional[_Union[FileKind, str]] = ...) -> None: ...

class CreatePresignedUploadResponse(_message.Message):
    __slots__ = ("file_id", "bucket", "key", "upload_url", "expires_in", "http_method", "headers")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    FILE_ID_FIELD_NUMBER: _ClassVar[int]
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_IN_FIELD_NUMBER: _ClassVar[int]
    HTTP_METHOD_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    file_id: int
    bucket: str
    key: str
    upload_url: str
    expires_in: int
    http_method: str
    headers: _containers.ScalarMap[str, str]
    def __init__(self, file_id: _Optional[int] = ..., bucket: _Optional[str] = ..., key: _Optional[str] = ..., upload_url: _Optional[str] = ..., expires_in: _Optional[int] = ..., http_method: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ...) -> None: ...

class CreatePresignedUploadBatchRequest(_message.Message):
    __slots__ = ("file_name", "mime_type", "visibility", "folder", "kind", "amount_of_files")
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    VISIBILITY_FIELD_NUMBER: _ClassVar[int]
    FOLDER_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_OF_FILES_FIELD_NUMBER: _ClassVar[int]
    file_name: str
    mime_type: str
    visibility: FileVisibility
    folder: str
    kind: FileKind
    amount_of_files: int
    def __init__(self, file_name: _Optional[str] = ..., mime_type: _Optional[str] = ..., visibility: _Optional[_Union[FileVisibility, str]] = ..., folder: _Optional[str] = ..., kind: _Optional[_Union[FileKind, str]] = ..., amount_of_files: _Optional[int] = ...) -> None: ...

class CreatePresignedUploadBatchResponse(_message.Message):
    __slots__ = ("presigned_uploads",)
    PRESIGNED_UPLOADS_FIELD_NUMBER: _ClassVar[int]
    presigned_uploads: _containers.RepeatedCompositeFieldContainer[CreatePresignedUploadResponse]
    def __init__(self, presigned_uploads: _Optional[_Iterable[_Union[CreatePresignedUploadResponse, _Mapping]]] = ...) -> None: ...

class GetDownloadUrlRequest(_message.Message):
    __slots__ = ("file_id", "expires_in")
    FILE_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_IN_FIELD_NUMBER: _ClassVar[int]
    file_id: int
    expires_in: int
    def __init__(self, file_id: _Optional[int] = ..., expires_in: _Optional[int] = ...) -> None: ...

class GetDownloadUrlResponse(_message.Message):
    __slots__ = ("file_id", "download_url", "expires_in")
    FILE_ID_FIELD_NUMBER: _ClassVar[int]
    DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_IN_FIELD_NUMBER: _ClassVar[int]
    file_id: int
    download_url: str
    expires_in: int
    def __init__(self, file_id: _Optional[int] = ..., download_url: _Optional[str] = ..., expires_in: _Optional[int] = ...) -> None: ...

class GetBatchDownloadUrlsRequest(_message.Message):
    __slots__ = ("file_ids", "expires_in")
    FILE_IDS_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_IN_FIELD_NUMBER: _ClassVar[int]
    file_ids: _containers.RepeatedScalarFieldContainer[int]
    expires_in: int
    def __init__(self, file_ids: _Optional[_Iterable[int]] = ..., expires_in: _Optional[int] = ...) -> None: ...

class GetBatchDownloadUrlsResponse(_message.Message):
    __slots__ = ("download_urls",)
    DOWNLOAD_URLS_FIELD_NUMBER: _ClassVar[int]
    download_urls: _containers.RepeatedCompositeFieldContainer[GetDownloadUrlResponse]
    def __init__(self, download_urls: _Optional[_Iterable[_Union[GetDownloadUrlResponse, _Mapping]]] = ...) -> None: ...
