from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from app.db.session import session_scope
from app.repo.orb_policies import OrbPolicyRepo
from app.schemas.orb_policy import (
    OrbPolicyCreate, OrbPolicyUpdate, OrbPolicyOut, OrbPolicyListOut, Paging
)

router = APIRouter(prefix="", tags=["Plus"])
repo = OrbPolicyRepo()


@router.get("/policies", response_model=OrbPolicyListOut)
def list_policies(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    with session_scope() as db:
        items = [
            OrbPolicyOut(
                id=p.id,
                name=p.name,
                description=p.description,
                per_object=p.per_object or {},
                per_aspect=p.per_aspect or {},
                adaptive_rules=p.adaptive_rules or {},
            )
            for p in db.query(repo.model).offset(offset).limit(limit).all()
        ]
        total = db.query(repo.model).count()
    return OrbPolicyListOut(items=items, paging=Paging(limit=limit, offset=offset, total=total))


@router.get("/policies/{policy_id}", response_model=OrbPolicyOut)
def get_policy(policy_id: int):
    with session_scope() as db:
        p = repo.get(db, policy_id)
        if not p:
            raise HTTPException(status_code=404, detail="policy not found")
        return OrbPolicyOut(
            id=p.id, name=p.name, description=p.description,
            per_object=p.per_object or {}, per_aspect=p.per_aspect or {}, adaptive_rules=p.adaptive_rules or {},
        )


@router.post("/policies", response_model=OrbPolicyOut, status_code=201)
def create_policy(payload: OrbPolicyCreate):
    with session_scope() as db:
        p = repo.create(db, **payload.model_dump())
        return OrbPolicyOut(
            id=p.id, name=p.name, description=p.description,
            per_object=p.per_object or {}, per_aspect=p.per_aspect or {}, adaptive_rules=p.adaptive_rules or {},
        )


@router.put("/policies/{policy_id}", response_model=OrbPolicyOut)
def update_policy(policy_id: int, payload: OrbPolicyUpdate):
    with session_scope() as db:
        p = repo.get(db, policy_id)
        if not p:
            raise HTTPException(status_code=404, detail="policy not found")
        data = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
        p = repo.update(db, policy_id, **data)
        return OrbPolicyOut(
            id=p.id, name=p.name, description=p.description,
            per_object=p.per_object or {}, per_aspect=p.per_aspect or {}, adaptive_rules=p.adaptive_rules or {},
        )


@router.delete("/policies/{policy_id}", status_code=204)
def delete_policy(policy_id: int):
    with session_scope() as db:
        p = repo.get(db, policy_id)
        if not p:
            return
        repo.delete(db, policy_id)
        return
