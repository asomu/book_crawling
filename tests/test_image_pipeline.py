from io import BytesIO
from pathlib import Path

from PIL import Image

from app.config.settings import AppSettings
from app.infrastructure.images.pipeline import ImagePipeline
from app.infrastructure.storage.filesystem import FilesystemStorage


def _image_bytes(size: tuple[int, int], color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_image_pipeline_generates_expected_assets(tmp_path: Path):
    settings = AppSettings(
        data_dir=tmp_path / "data",
        assets_dir=tmp_path / "data" / "assets",
        browser_state_dir=tmp_path / "data" / "browser",
        snapshots_dir=tmp_path / "data" / "snapshots",
        logs_dir=tmp_path / "logs",
        resource_dir=Path(__file__).resolve().parents[1] / "resource",
    )
    settings.ensure_runtime_dirs()
    storage = FilesystemStorage(settings)
    pipeline = ImagePipeline(settings, storage)

    assets = pipeline.generate_assets(
        "9791130671017",
        "테스트 북",
        _image_bytes((600, 900), (20, 50, 90)),
        _image_bytes((900, 1300), (90, 40, 20)),
    )

    assert [asset.kind.value for asset in assets] == ["cover", "y1000", "coupang", "naver", "detail"]
    expected_sizes = {
        "cover": (600, 900),
        "y1000": (1000, 1000),
        "coupang": (1000, 1000),
        "naver": (1000, 1000),
        "detail": (860, 1242),
    }

    for asset in assets:
        path = tmp_path / asset.file_path
        assert path.exists()
        assert path.name.startswith("테스트 북_")
        with Image.open(path) as generated:
            assert generated.size == expected_sizes[asset.kind.value]


def test_prepare_overlay_icon_removes_corner_background(tmp_path: Path):
    resource_dir = tmp_path / "resource"
    resource_dir.mkdir(parents=True, exist_ok=True)
    icon_path = resource_dir / "badge.png"

    icon = Image.new("RGB", (40, 40), (255, 255, 255))
    for x in range(10, 30):
        for y in range(10, 30):
            icon.putpixel((x, y), (220, 60, 80))
    icon.save(icon_path, format="PNG")

    settings = AppSettings(
        data_dir=tmp_path / "data",
        assets_dir=tmp_path / "data" / "assets",
        browser_state_dir=tmp_path / "data" / "browser",
        snapshots_dir=tmp_path / "data" / "snapshots",
        logs_dir=tmp_path / "logs",
        resource_dir=resource_dir,
    )
    settings.ensure_runtime_dirs()
    storage = FilesystemStorage(settings)
    pipeline = ImagePipeline(settings, storage)

    prepared = pipeline._prepare_overlay_icon(icon_path)

    assert prepared.mode == "RGBA"
    assert prepared.size == (20, 20)
    assert prepared.getchannel("A").getextrema() == (255, 255)
