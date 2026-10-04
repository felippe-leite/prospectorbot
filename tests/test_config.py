from prospector.config import Settings


def test_dotenv_loading_with_quotes_and_comments(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ["GEOAPIFY_API_KEY", "PROSPECTOR_DATABASE_PATH", "PROSPECTOR_MAX_LINKS"]:
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text('GEOAPIFY_API_KEY="test-key" # comment\nPROSPECTOR_DATABASE_PATH=data/custom.db\nPROSPECTOR_MAX_LINKS=3\n')
    settings = Settings.from_env()
    assert settings.geoapify_api_key.get_secret_value() == "test-key"
    assert str(settings.database_path) == "data/custom.db"
    assert settings.max_links == 3
    assert "test-key" not in repr(settings)


def test_environment_takes_precedence_including_empty_value(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text('GEOAPIFY_API_KEY=file-key\n')
    monkeypatch.setenv("GEOAPIFY_API_KEY", "environment-key")
    assert Settings.from_env().geoapify_api_key.get_secret_value() == "environment-key"
    monkeypatch.setenv("GEOAPIFY_API_KEY", "")
    assert Settings.from_env().geoapify_api_key is None


def test_file_does_not_interpolate_or_mutate_environment(tmp_path, monkeypatch):
    import os
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)
    monkeypatch.setenv("EXAMPLE_TOKEN", "expanded")
    (tmp_path / ".env").write_text('GEOAPIFY_API_KEY="${EXAMPLE_TOKEN}"\n')
    assert Settings.from_env().geoapify_api_key.get_secret_value() == "${EXAMPLE_TOKEN}"
    assert "GEOAPIFY_API_KEY" not in os.environ


def test_does_not_search_parent_directories(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text('GEOAPIFY_API_KEY=parent-key\n')
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.chdir(child)
    monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)
    assert Settings.from_env().geoapify_api_key is None
