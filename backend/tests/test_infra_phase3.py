"""Phase 3.4: durable Chroma config + OpenTelemetry wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_chroma_http_mode_uses_http_client(monkeypatch):
    from app.services import rag_service

    rag_service._collection = None
    rag_service._chroma_client = None

    monkeypatch.setattr(rag_service.settings, "rag_enabled", True)
    monkeypatch.setattr(rag_service.settings, "rag_chroma_mode", "http")
    monkeypatch.setattr(rag_service.settings, "rag_chroma_host", "example.com")
    monkeypatch.setattr(rag_service.settings, "rag_chroma_port", 1234)

    fake_client = MagicMock()
    fake_collection = MagicMock()
    fake_client.get_or_create_collection.return_value = fake_collection

    fake_module = MagicMock()
    fake_module.HttpClient.return_value = fake_client
    fake_module.PersistentClient.side_effect = AssertionError(
        "persistent client should not be used in http mode"
    )

    with patch.dict("sys.modules", {"chromadb": fake_module}):
        coll = rag_service.get_chroma_collection()

    assert coll is fake_collection
    fake_module.HttpClient.assert_called_once_with(host="example.com", port=1234)


def test_chroma_persistent_mode_uses_persistent_client(monkeypatch, tmp_path):
    from app.services import rag_service

    rag_service._collection = None
    rag_service._chroma_client = None

    monkeypatch.setattr(rag_service.settings, "rag_enabled", True)
    monkeypatch.setattr(rag_service.settings, "rag_chroma_mode", "persistent")
    monkeypatch.setattr(
        rag_service.settings, "rag_persist_directory", str(tmp_path / "chroma")
    )

    fake_client = MagicMock()
    fake_collection = MagicMock()
    fake_client.get_or_create_collection.return_value = fake_collection

    fake_module = MagicMock()
    fake_module.PersistentClient.return_value = fake_client

    with patch.dict("sys.modules", {"chromadb": fake_module}):
        coll = rag_service.get_chroma_collection()

    assert coll is fake_collection
    fake_module.PersistentClient.assert_called_once()


def test_configure_tracing_is_noop_when_disabled(monkeypatch):
    from app import telemetry

    telemetry._configured = False
    monkeypatch.setattr(telemetry.settings, "enable_otlp", False)
    telemetry.configure_tracing()
    assert telemetry._configured is True
