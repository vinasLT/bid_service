from pathlib import Path

import grpc
from fastapi import Query
from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseParamsFields, UseFieldsAliases
from pydantic import BaseModel
from rfc9457 import BadRequestProblem

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def create_pagination_page(pydantic_model: type[BaseModel])-> type[Page[BaseModel]]:
    return CustomizedPage[
        Page[pydantic_model],
        UseParamsFields(size=Query(5, ge=1, le=1000)),
        UseFieldsAliases(
            items="data",
            total='count'
        )
    ]

def raise_rpc_problem(service_name: str, exc: grpc.RpcError) -> None:
    detail = exc.details() if hasattr(exc, "details") else None
    code = exc.code().name if hasattr(exc, "code") else exc.__class__.__name__
    message = detail or str(exc) or "unknown error"
    raise BadRequestProblem(detail=f"{service_name} service error ({code}): {message}")
