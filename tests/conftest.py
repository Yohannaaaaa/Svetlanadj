import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture
def app(tmp_path):
    from app import create_app
    app = create_app({"TESTING": True, "DATA_DIR": tmp_path / "data", "SECRET_KEY": "test-secret",
                      "STUDIO_PASSWORD": ""})
    return app


@pytest.fixture
def client(app):
    c = app.test_client()
    c.environ_base["HTTP_X_STUDIO"] = "1"
    return c


@pytest.fixture
def portrait(tmp_path):
    p = tmp_path / "svetlana.png"
    img = Image.new("RGB", (768, 1024), (20, 20, 28))
    d = ImageDraw.Draw(img)
    d.ellipse((234, 220, 534, 600), fill=(225, 200, 190))
    d.rectangle((180, 120, 588, 260), fill=(240, 240, 245))
    d.ellipse((310, 380, 350, 410), fill=(120, 200, 255))
    d.ellipse((418, 380, 458, 410), fill=(120, 200, 255))
    img.save(p)
    return p
