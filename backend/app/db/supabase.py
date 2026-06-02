from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class SupabaseGateway:
    def __init__(self) -> None:
        self.base_url = settings.supabase_url.rstrip("/")
        self.service_role_key = settings.supabase_service_role_key

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.service_role_key)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service role access is not configured.",
            )

        url = f"{self.base_url}/rest/v1/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=self._headers(), params=params)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Supabase request failed.",
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()
        if not isinstance(data, list):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unexpected Supabase response shape.",
            )

        return data

    async def upsert(
        self,
        path: str,
        payload: dict[str, Any],
        on_conflict: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service role access is not configured.",
            )

        url = f"{self.base_url}/rest/v1/{path.lstrip('/')}"
        headers = {
            **self._headers(),
            "Prefer": "resolution=merge-duplicates,return=representation",
        }
        params = {"on_conflict": on_conflict} if on_conflict else None

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=headers, params=params, json=payload)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Supabase upsert failed.",
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()
        return data if isinstance(data, list) else []

    async def insert(
        self,
        path: str,
        payload: dict[str, Any] | list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service role access is not configured.",
            )

        url = f"{self.base_url}/rest/v1/{path.lstrip('/')}"
        headers = {**self._headers(), "Prefer": "return=representation"}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Supabase insert failed.",
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()
        return data if isinstance(data, list) else []

    async def patch(
        self,
        path: str,
        payload: dict[str, Any],
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service role access is not configured.",
            )

        url = f"{self.base_url}/rest/v1/{path.lstrip('/')}"
        headers = {**self._headers(), "Prefer": "return=representation"}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.patch(url, headers=headers, params=params, json=payload)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Supabase patch failed.",
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()
        return data if isinstance(data, list) else []

    async def delete(
        self,
        path: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service role access is not configured.",
            )

        url = f"{self.base_url}/rest/v1/{path.lstrip('/')}"
        headers = {**self._headers(), "Prefer": "return=representation"}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.delete(url, headers=headers, params=params)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "Supabase delete failed.",
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )

        data = response.json()
        return data if isinstance(data, list) else []


supabase_gateway = SupabaseGateway()
