"""Relationship interpretation API endpoints."""

from __future__ import annotations

import json
import os
from typing import Any, Type

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict, ValidationError

from ...interpret.loader import RulepackValidationError, lint_rulepack
from ...interpret.models import InterpretRequest, InterpretResponse, RulepackLintResult, RulepackMeta, RulepackVersionPayload
from ...interpret.service import InterpretationError, evaluate_relationship
from ...interpret.store import RulepackStore, get_rulepack_store
from ..errors import ErrorEnvelope
from ..pagination import Pagination, get_pagination


_API_KEY = os.getenv("AE_API_KEY")


def _require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if _API_KEY and x_api_key != _API_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "invalid or missing API key"},
        )


router = APIRouter(prefix="/v1/interpret", tags=["interpret"], dependencies=[Depends(_require_api_key)])


class RulepackUploadPayload(BaseModel):
    content: dict[str, Any] | None = None
    text: str | None = None

    def as_bytes(self) -> bytes:
        if self.text is not None:
            return self.text.encode("utf-8")
        if self.content is not None:
            return json.dumps(self.content).encode("utf-8")
        raise ValueError("upload payload missing content")


class RulepackLintPayload(BaseModel):
    content: dict[str, Any] | None = None
    text: str | None = None

    def as_bytes(self) -> bytes:
        if self.text is not None:
            return self.text.encode("utf-8")
        if self.content is not None:
            return json.dumps(self.content).encode("utf-8")
        raise ValueError("lint payload missing content")


def _store_dependency() -> RulepackStore:
    return get_rulepack_store()


class RulepackCollection(BaseModel):
    """Paginated rulepack listing."""

    items: list[RulepackMeta]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "relationship_basic",
                        "name": "Relationship Basic",
                        "version": 1,
                        "title": "Relationship Essentials",
                        "description": "Core synastry findings",
                        "created_at": "2023-01-01T00:00:00+00:00",
                        "mutable": False,
                        "available_versions": [1],
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 25,
            }
        }
    )


@router.get(
    "/rulepacks",
    response_model=RulepackCollection,
    operation_id="listRulepacks",
    summary="List uploaded rulepacks.",
)
def list_rulepacks(
    pagination: Pagination = Depends(get_pagination),
    store: RulepackStore = Depends(_store_dependency),
) -> RulepackCollection:
    items = store.list_rulepacks()
    total = len(items)
    start = pagination.offset
    end = start + pagination.limit
    return RulepackCollection(
        items=items[start:end],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/rulepacks/{rulepack_id}",
    response_model=RulepackVersionPayload,
    operation_id="getRulepack",
    responses={404: {"model": ErrorEnvelope}},
)
def get_rulepack(
    rulepack_id: str,
    response: Response,
    version: int | None = None,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    store: RulepackStore = Depends(_store_dependency),
) -> RulepackVersionPayload | Response:
    try:
        payload = store.get_rulepack(rulepack_id, version=version)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail={"code": "RULEPACK_NOT_FOUND", "message": str(exc)}
        ) from exc
    if if_none_match and if_none_match == payload.etag:
        return Response(status_code=304, headers={"ETag": payload.etag})
    response.headers["ETag"] = payload.etag
    return payload


async def _read_rulepack_payload(
    request: Request,
    model: Type[RulepackUploadPayload] | Type[RulepackLintPayload],
) -> tuple[bytes, str]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(
                status_code=400,
                detail={"code": "BAD_REQUEST", "message": "multipart payload missing file"},
            )
        return await upload.read(), upload.filename or "upload"
    try:
        data = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "invalid JSON"}) from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "invalid payload"})
    try:
        payload = model.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "message": "invalid payload", "errors": exc.errors()},
        ) from exc
    try:
        return payload.as_bytes(), "inline"
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": str(exc)}) from exc


@router.post(
    "/rulepacks",
    response_model=RulepackMeta,
    status_code=201,
    operation_id="uploadRulepack",
    responses={400: {"model": ErrorEnvelope}},
)
async def upload_rulepack(
    request: Request,
    store: RulepackStore = Depends(_store_dependency),
) -> RulepackMeta:
    raw, source = await _read_rulepack_payload(request, RulepackUploadPayload)
    try:
        meta = store.save_rulepack(raw, source=source)
    except RulepackValidationError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_RULEPACK", "message": str(exc), "errors": exc.errors}) from exc
    return meta


@router.post(
    "/rulepacks/lint",
    response_model=RulepackLintResult,
    operation_id="lintRulepack",
)
async def lint_rulepack_endpoint(request: Request) -> RulepackLintResult:
    raw, source = await _read_rulepack_payload(request, RulepackLintPayload)
    return lint_rulepack(raw, source=source)


@router.delete(
    "/rulepacks/{rulepack_id}",
    status_code=204,
    operation_id="deleteRulepack",
    responses={403: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
)
def delete_rulepack(rulepack_id: str, store: RulepackStore = Depends(_store_dependency)) -> Response:
    try:
        store.delete_rulepack(rulepack_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": str(exc)}) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "RULEPACK_NOT_FOUND", "message": str(exc)}) from exc
    return Response(status_code=204)


@router.post(
    "/relationship",
    response_model=InterpretResponse,
    operation_id="interpretRelationship",
    summary="Run a relationship interpretation.",
    responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "synastry": {
                            "summary": "Synastry findings from pre-computed hits",
                            "value": {
                                "rulepack_id": "relationship_basic",
                                "scope": "synastry",
                                "synastry": {
                                    "hits": [
                                        {
                                            "a": "Sun",
                                            "b": "Moon",
                                            "aspect": "trine",
                                            "severity": 0.6,
                                        },
                                        {
                                            "a": "Venus",
                                            "b": "Mars",
                                            "aspect": "conjunction",
                                            "severity": 0.5,
                                        },
                                    ]
                                },
                            },
                        }
                    }
                }
            }
        }
    },
)
def relationship_findings(
    request: InterpretRequest,
    store: RulepackStore = Depends(_store_dependency),
) -> InterpretResponse:
    try:
        rulepack = store.get_rulepack(request.rulepack_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail={"code": "RULEPACK_NOT_FOUND", "message": str(exc)}
        ) from exc
    try:
        return evaluate_relationship(rulepack, request)
    except InterpretationError as exc:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": str(exc)}) from exc


__all__ = ["router"]
