import pytest
from httpx import AsyncClient
import requests


@pytest.mark.api
def test_api_wrong_url(api_base_path):
    url = f"{api_base_path}/analysis?repo_url=https://gitlab.com/someowner/somerepo"
    print(url)
    response = requests.get(url)
    print(response.json())
    assert response.status_code == 422

    url = f"{api_base_path}/analysis?repo_url=https://github.com/someowner"
    print(url)
    response = requests.get(url)
    print(response.json())
    assert response.status_code == 422

    url = f"{api_base_path}/analysis?repo_url=https://github.com/Himanshu-Dreamteam/nonexistentrepo"
    print(url)
    response = requests.get(url)
    print(response.json())
    assert response.status_code == 404


@pytest.mark.api
def test_api_valid_url(api_base_path, empty_db_tables, db_connection):
    """
    If we seed DB with data then the implementation should just pick that cached data and return instead of checking out
    the git repo.
    """
    repo_url = "https://github.com/github/.github"
    email = "jdoe@example.com"
    db = db_connection
    db.execute_sql(f"insert into repo (repo_url,status,loc_facts_status,commit_feq_facts_status) values('{repo_url}','done','done','done');")
    repo_id = db.execute_sql(f"select * from repo where repo_url = '{repo_url}' limit 1").fetchall()[0][0]
    db.execute_sql(f"insert into committer (email) values('{email}');")
    committer_id = db.execute_sql(f"select * from committer where email = '{email}' limit 1").fetchall()[0][0]
    db.execute_sql(f"insert into {'CommitterStatsPerRepo'.lower()} (repo_id,committer_id,loc,loc_percentile,loc_percentage,consistency_score) values({repo_id},{committer_id},100,0.9,0.87,16);")
    db.close()

    url = f"{api_base_path}/analysis?repo_url={repo_url}"
    print(url)
    response = requests.get(url)
    print(response.json())
    assert response.status_code == 200
    result = response.json()
    assert result["repo_url"] == repo_url
    assert result["status"] == "done"
    assert result["loc_analysis"][email]["email"] == email
    assert result["loc_analysis"][email]["loc"] == 100
    assert result["loc_analysis"][email]["loc_percentile"] == 0.9
    assert result["loc_analysis"][email]["loc_percentage"] == 0.87
    assert result["commit_freq_analysis"][email] == 16
