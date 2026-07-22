"""Service-account routes: create/list/revoke (admin) + client_credentials
token exchange (platform.md §8)."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.config import settings
from app.core.security import (
    create_service_token,
    dummy_verify,
    generate_client_id,
    generate_client_secret,
    hash_password,
    verify_password,
)
from app.database.session import DatabaseSession
from app.dependencies.auth import AdminUser
from app.models.service_account import ServiceAccount
from app.schemas.service_account import (
    ServiceAccountCreate,
    ServiceAccountCreated,
    ServiceAccountRead,
    ServiceTokenRequest,
    ServiceTokenResponse,
)

router = APIRouter()


@router.post(
    "/service-accounts",
    response_model=ServiceAccountCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_account(
    payload: ServiceAccountCreate,
    session: DatabaseSession,
    _: AdminUser,
) -> ServiceAccountCreated:
    """Create a new service account. Accessible to administrators only.

    The returned `client_secret` is shown once, in plaintext — only its
    Argon2id hash is stored.
    """
    client_id = generate_client_id()
    client_secret = generate_client_secret()

    account = ServiceAccount(
        client_id=client_id,
        hashed_client_secret=hash_password(client_secret),
        description=payload.description,
        scopes=payload.scopes,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    return ServiceAccountCreated(
        id=account.id,
        client_id=account.client_id,
        description=account.description,
        scopes=account.scopes,
        is_active=account.is_active,
        created_at=account.created_at,
        client_secret=client_secret,
    )


@router.get("/service-accounts", response_model=list[ServiceAccountRead])
async def list_service_accounts(
    session: DatabaseSession,
    _: AdminUser,
) -> list[ServiceAccountRead]:
    """List all service accounts. Accessible to administrators only."""
    result = await session.execute(select(ServiceAccount))
    accounts = result.scalars().all()
    return [ServiceAccountRead.model_validate(a) for a in accounts]


@router.post(
    "/service-accounts/{client_id}/revoke", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_service_account(
    client_id: str,
    session: DatabaseSession,
    _: AdminUser,
) -> None:
    """Revoke a service account: deactivates it and rejects all outstanding
    tokens (token_version bump — same pattern as user logout).

    Accessible to administrators only. Returns HTTP 404 if the client_id
    doesn't exist.
    """
    result = await session.execute(
        select(ServiceAccount).where(ServiceAccount.client_id == client_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No service account found for client_id '{client_id}'.",
        )

    account.is_active = False
    account.token_version += 1
    session.add(account)
    await session.commit()


@router.post("/service-token", response_model=ServiceTokenResponse)
async def issue_service_token(
    payload: ServiceTokenRequest,
    session: DatabaseSession,
) -> ServiceTokenResponse:
    """Exchange client_id/client_secret for a short-lived service token.

    An invalid client_secret returns HTTP 401 without distinguishing
    "unknown client_id" from "wrong secret" (anti-enumeration, same
    principle as POST /auth/token).
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid client credentials.",
    )

    result = await session.execute(
        select(ServiceAccount).where(ServiceAccount.client_id == payload.client_id)
    )
    account = result.scalar_one_or_none()

    if account is None:
        dummy_verify(payload.client_secret)
        raise credentials_exc

    secret_ok = verify_password(payload.client_secret, account.hashed_client_secret)
    if not secret_ok:
        raise credentials_exc
    if not account.is_active:
        raise credentials_exc

    token = create_service_token(
        {
            "sub": account.client_id,
            "scopes": account.scopes,
            "tkv": account.token_version,
        }
    )
    return ServiceTokenResponse(
        access_token=token,
        expires_in=settings.base.service_token_expire_minutes * 60,
    )
