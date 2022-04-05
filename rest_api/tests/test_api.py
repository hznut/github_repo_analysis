import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.skip
@pytest.mark.api
@pytest.mark.anyio
async def test_get_analysis(url_base_path):
    async with AsyncClient(app=app, base_url=f"http://{url_base_path}") as ac:
        response = await ac.get("/analysis?repo_url=https://github.com/someowner/somerepo")
    assert response.status_code == 200
    assert response.json() == {"message": "Tomato"}

    # url = f"{url_base_path}/analysis?repo_url=https://github.com/someowner/somerepo"
    # response = await client.get(url)
    # assert response.status_code == 404
    # pass
