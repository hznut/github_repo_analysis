import pytest


@pytest.mark.unit
def test_repo_exists(repo_analyzer):
    exists = repo_analyzer.repo_exists_on_github("https://github.com/golang/vuln")
    assert exists


@pytest.mark.unit
def test_get_analysis_by_repo_url(repo_analyzer, empty_db_tables, db_connection):
    repo_url = "https://github.com/golang/vuln"
    email = "jdoe@example.com"
    db = db_connection
    db.execute_sql(f"insert into repo (repo_url,status,loc_facts_status,commit_feq_facts_status) values('{repo_url}','done','done','done');")
    repo_id = db.execute_sql(f"select * from repo where repo_url = '{repo_url}' limit 1").fetchall()[0][0]
    db.execute_sql(f"insert into committer (email) values('{email}');")
    committer_id = db.execute_sql(f"select * from committer where email = '{email}' limit 1").fetchall()[0][0]
    db.execute_sql(f"insert into {'CommitterStatsPerRepo'.lower()} (repo_id,committer_id,loc,loc_percentile,loc_percentage,consistency_score) values({repo_id},{committer_id},100,0.9,0.87,16);")
    db.close()

    result = repo_analyzer.get_analysis_by_repo_url(repo_url)
    assert result.repo_url == repo_url
    assert result.status == "done"
    assert result.loc_analysis[email].email == email
    assert result.loc_analysis[email].loc == 100
    assert result.loc_analysis[email].loc_percentile == 0.9
    assert result.loc_analysis[email].loc_percentage == 0.87
    assert result.commit_freq_analysis[email] == 16

