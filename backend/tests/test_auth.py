"""
Tests for JWT authentication endpoints and the get_current_user dependency.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_PASSWORD


class TestLogin:
    async def test_login_success_returns_token(self, async_client: AsyncClient):
        """Valid credentials return a JWT access token."""
        response = await async_client.post(
            "/api/auth/login",
            json={"username": "testadmin", "password": TEST_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert len(data["access_token"]) > 20  # sanity check it's a real JWT

    async def test_login_wrong_password_returns_401(self, async_client: AsyncClient):
        """Wrong password must return HTTP 401."""
        response = await async_client.post(
            "/api/auth/login",
            json={"username": "testadmin", "password": "this_is_wrong"},
        )
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]

    async def test_login_wrong_username_returns_401(self, async_client: AsyncClient):
        """Unknown username must return HTTP 401."""
        response = await async_client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": TEST_PASSWORD},
        )
        assert response.status_code == 401

    async def test_protected_endpoint_without_token_returns_403(
        self, async_client: AsyncClient
    ):
        """Requests without Authorization header must be rejected."""
        response = await async_client.get("/api/documents/")
        # HTTPBearer returns 403 when no credentials are provided
        assert response.status_code in (401, 403)

    async def test_valid_token_grants_access(
        self, async_client: AsyncClient, auth_headers: dict, mock_db
    ):
        """A valid JWT token allows access to protected endpoints."""
        # Mock DB to return an empty list of documents
        result_mock = mock_db.execute.return_value
        result_mock.scalars.return_value.all.return_value = []

        response = await async_client.get("/api/documents/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
