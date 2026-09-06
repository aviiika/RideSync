"""Settings parsing.

Regression guard: a real ``.env`` written from ``.env.example`` uses a plain
comma-separated CORS_ORIGINS, which pydantic-settings tries to JSON-decode
unless the field opts out. That crashed the app on first run.
"""

from app.config import Settings


def test_comma_separated_cors_origins(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n", encoding="utf-8"
    )

    settings = Settings(_env_file=env_file)

    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_single_cors_origin(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CORS_ORIGINS=http://localhost:5173\n", encoding="utf-8")

    assert Settings(_env_file=env_file).cors_origins == ["http://localhost:5173"]


def test_defaults_apply_without_an_env_file(tmp_path) -> None:
    settings = Settings(_env_file=tmp_path / "absent.env")

    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.simulation_tick_ms == 500
