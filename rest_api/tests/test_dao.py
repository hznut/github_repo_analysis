import pytest
import dao


@pytest.mark.unit
def test_get_repo_by_url():
    dao.init_dao()
    repo = dao.get_repo_by_url("https://github.com/someowner/somerepo")
    assert repo is None
    pass

