from ingest.__main__ import check_counts, database_url_from_env, describe_target, main


def test_check_counts_accepts_the_expected_dataset():
    assert check_counts(books=66, verses=31_084, edges=344_542) == []


def test_check_counts_reports_each_problem():
    problems = check_counts(books=65, verses=100, edges=10)
    assert len(problems) == 3


def test_describe_target_hides_credentials():
    target = describe_target("postgresql://user:secreto@ep-x.eu-central-1.aws.neon.tech/neondb")
    assert target == "ep-x.eu-central-1.aws.neon.tech/neondb"
    assert "secreto" not in target


def test_main_needs_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main([]) == 2
    assert "DATABASE_URL" in capsys.readouterr().err


def test_database_url_from_env_strips_whitespace(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "  postgresql://user:clave@host/db \n")
    assert database_url_from_env() == "postgresql://user:clave@host/db"


def test_database_url_from_env_treats_blank_as_missing(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "  \n")
    assert database_url_from_env() is None
    monkeypatch.delenv("DATABASE_URL")
    assert database_url_from_env() is None
