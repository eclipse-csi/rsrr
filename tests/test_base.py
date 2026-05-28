from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from rsrr.base import Context


@pytest.mark.asyncio
async def test_github_get_with_token():
    ctx = Context(gh_token="test-token")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rsrr.base.httpx.AsyncClient", return_value=mock_client):
        response = await ctx.github_get("https://api.github.com/repos/foo/bar")

    assert response is mock_response
    mock_client.get.assert_called_once_with(
        "https://api.github.com/repos/foo/bar",
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": "Bearer test-token",
        },
    )


@pytest.mark.asyncio
async def test_github_get_without_token():
    ctx = Context()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rsrr.base.httpx.AsyncClient", return_value=mock_client):
        response = await ctx.github_get("https://api.github.com/repos/foo/bar")

    assert response is mock_response
    mock_client.get.assert_called_once_with(
        "https://api.github.com/repos/foo/bar",
        headers={"Accept": "application/vnd.github.v3+json"},
    )
