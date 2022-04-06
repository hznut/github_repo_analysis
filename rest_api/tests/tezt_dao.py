import pytest
import uuid


@pytest.mark.unit
def test_empty_db(dao):
    repo = dao.get_repo_by_url("https://github.com/someowner/somerepo")
    assert repo is None

    committer = dao.get_committer("jdoe@example.com")
    assert committer is None


@pytest.mark.skip
@pytest.mark.unit
def test_non_empty_db(dao, load_data):
    repo_url = "https://github.com/someowner/somerepo"
    repo = dao.get_repo_by_url(repo_url)
    assert repo is not None
    assert repo.repo_url == repo_url

