"""Tests for the FastAPI server (via TestClient, no network)."""

from __future__ import annotations

import io
import struct

import pytest
from fastapi.testclient import TestClient

from palettengine.server import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


# --------------------------------------------------------------------------- #
# /api/generate
# --------------------------------------------------------------------------- #
def test_generate_default(client: TestClient) -> None:
    r = client.post("/api/generate", json={"seed": 42})
    assert r.status_code == 200
    doc = r.json()
    assert len(doc["colors"]) == 5
    assert doc["colors"][0]["hex"].startswith("#")
    assert all(c["text_on"] in ("#000000", "#ffffff") for c in doc["colors"])
    assert set(doc["roles"]) == {"light", "dark"}
    assert len(doc["contrast"]) == 5
    assert doc["score"] > 0


def test_generate_deterministic(client: TestClient) -> None:
    a = client.post("/api/generate", json={"seed": 7}).json()
    b = client.post("/api/generate", json={"seed": 7}).json()
    assert a["colors"] == b["colors"]


def test_generate_locks_hold(client: TestClient) -> None:
    r = client.post("/api/generate", json={"seed": 1, "locks": {"2": "#123456"}})
    assert r.json()["colors"][2]["hex"] == "#123456"


def test_text_on_is_wcag_correct(client: TestClient) -> None:
    # A locked near-black swatch must get white text; near-white gets black.
    r = client.post(
        "/api/generate", json={"seed": 1, "locks": {"0": "#0a0a0a", "1": "#f8f8f8"}}
    )
    colors = r.json()["colors"]
    assert colors[0]["text_on"] == "#ffffff"
    assert colors[1]["text_on"] == "#000000"


def test_generate_bad_scheme_422(client: TestClient) -> None:
    assert client.post("/api/generate", json={"scheme": "vaporwave"}).status_code == 422


def test_generate_bad_size_422(client: TestClient) -> None:
    assert client.post("/api/generate", json={"size": 0}).status_code == 422
    assert client.post("/api/generate", json={"size": 99}).status_code == 422


# --------------------------------------------------------------------------- #
# /api/export and /api/simulate
# --------------------------------------------------------------------------- #
HEXES = ["#0b132b", "#3a506b", "#5bc0be", "#e0fbfc"]


def test_export_css(client: TestClient) -> None:
    r = client.post("/api/export", json={"colors": HEXES, "format": "css"})
    assert r.status_code == 200
    assert "--color-1: #0b132b;" in r.text


def test_export_with_roles(client: TestClient) -> None:
    r = client.post(
        "/api/export", json={"colors": HEXES, "format": "scss", "roles_theme": "dark"}
    )
    assert "$background:" in r.text


def test_export_ase_binary(client: TestClient) -> None:
    r = client.post("/api/export", json={"colors": HEXES, "format": "ase"})
    assert r.status_code == 200
    assert r.content[:4] == b"ASEF"
    assert struct.unpack(">I", r.content[8:12])[0] == len(HEXES)


def test_export_unknown_format_422(client: TestClient) -> None:
    r = client.post("/api/export", json={"colors": HEXES, "format": "docx"})
    assert r.status_code == 422


def test_export_bad_hex_422(client: TestClient) -> None:
    r = client.post("/api/export", json={"colors": ["#zzz"], "format": "css"})
    assert r.status_code == 422


def test_simulate(client: TestClient) -> None:
    r = client.post("/api/simulate", json={"colors": HEXES, "kind": "deutan"})
    assert r.status_code == 200
    out = r.json()["colors"]
    assert len(out) == len(HEXES)
    assert all(h.startswith("#") for h in out)


def test_simulate_unknown_kind_422(client: TestClient) -> None:
    r = client.post("/api/simulate", json={"colors": HEXES, "kind": "nope"})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# /api/extract
# --------------------------------------------------------------------------- #
def _png_bytes() -> bytes:
    import numpy as np
    from PIL import Image

    arr = np.zeros((60, 90, 3), dtype=np.uint8)
    arr[:, :30] = (230, 57, 70)
    arr[:, 30:60] = (69, 123, 157)
    arr[:, 60:] = (241, 250, 238)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def test_extract_image(client: TestClient) -> None:
    r = client.post(
        "/api/extract",
        files={"file": ("test.png", _png_bytes(), "image/png")},
        data={"size": "3", "seed": "1", "faithful": "true"},
    )
    assert r.status_code == 200
    assert len(r.json()["colors"]) == 3


def test_extract_empty_upload_422(client: TestClient) -> None:
    r = client.post("/api/extract", files={"file": ("empty.png", b"", "image/png")})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# meta + Colormind compatibility
# --------------------------------------------------------------------------- #
def test_meta(client: TestClient) -> None:
    doc = client.get("/api/meta").json()
    assert "auto" in doc["schemes"]
    assert "ase" in doc["formats"]
    assert "deutan" in doc["cvd_kinds"]


def test_colormind_compat_random(client: TestClient) -> None:
    r = client.post("/api/", json={"model": "default"})
    assert r.status_code == 200
    result = r.json()["result"]
    assert len(result) == 5
    assert all(len(c) == 3 and all(0 <= v <= 255 for v in c) for c in result)


def test_colormind_compat_locks_are_hard(client: TestClient) -> None:
    r = client.post(
        "/api/", json={"model": "default", "input": [[44, 43, 44], [90, 83, 82], "N", "N", "N"]}
    )
    result = r.json()["result"]
    # Unlike Colormind itself, our locked inputs come back exactly.
    assert result[0] == [44, 43, 44]
    assert result[1] == [90, 83, 82]


def test_colormind_compat_raw_body_no_content_type(client: TestClient) -> None:
    # Real Colormind clients POST with `curl --data-binary` and no JSON content-type.
    r = client.post("/api/", content=b'{"model":"default","input":[[10,20,30],"N","N","N","N"]}')
    assert r.status_code == 200
    assert r.json()["result"][0] == [10, 20, 30]


def test_colormind_compat_garbage_body_422(client: TestClient) -> None:
    assert client.post("/api/", content=b"not json").status_code == 422


def test_colormind_list(client: TestClient) -> None:
    assert client.get("/list/").json() == {"result": ["default", "ui"]}
