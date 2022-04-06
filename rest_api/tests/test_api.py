import pytest
from httpx import AsyncClient
import requests


@pytest.mark.api
def test_api_wrong_url(api_base_path):
    url = f"{api_base_path}analysis?repo_url=https://gitlab.com/someowner/somerepo"
    print(url)
    response = requests.get(url)
    print(response.json())
    assert response.status_code == 404

    url = f"{api_base_path}analysis?repo_url=https://github.com/someowner"
    print(url)
    response = requests.get(url)
    print(response.json())
    assert response.status_code == 404

    url = f"{api_base_path}analysis?repo_url=https://github.com/Himanshu-Dreamteam/nonexistentrepo"
    print(url)
    response = requests.get(url)
    print(response.json())
    assert response.status_code == 404
