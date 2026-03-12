from __future__ import annotations

from collections import deque
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image

from app.config.settings import AppSettings
from app.domain.enums import AssetKind
from app.domain.errors import ImageTransformFailedError, StorageFailedError
from app.domain.schemas import StoredAsset
from app.infrastructure.storage.filesystem import FilesystemStorage


class ImagePipeline:
    def __init__(self, settings: AppSettings, storage: FilesystemStorage) -> None:
        self.settings = settings
        self.storage = storage

    def generate_assets(self, isbn: str, title: str, cover_bytes: bytes, detail_bytes: bytes) -> list[StoredAsset]:
        try:
            cover = Image.open(BytesIO(cover_bytes)).convert("RGB")
            detail = Image.open(BytesIO(detail_bytes)).convert("RGB")
        except Exception as exc:
            raise ImageTransformFailedError(f"Could not open downloaded images: {exc}") from exc

        assets = [
            self._save_image(isbn, title, AssetKind.COVER, cover),
            self._save_image(isbn, title, AssetKind.Y1000, self._create_framed_variant(cover, 900)),
            self._save_image(isbn, title, AssetKind.COUPANG, self._create_framed_variant(cover, 810, "쿠팡_아이콘.png")),
            self._save_image(isbn, title, AssetKind.NAVER, self._create_framed_variant(cover, 810, "네이버_아이콘.png")),
            self._save_image(isbn, title, AssetKind.DETAIL, self._resize_detail(detail)),
        ]
        return assets

    def _save_image(self, isbn: str, title: str, kind: AssetKind, image: Image.Image) -> StoredAsset:
        path = self.storage.asset_path(isbn, title, kind.value)
        try:
            image.save(path, format="JPEG", quality=95)
        except Exception as exc:
            raise StorageFailedError(f"Unable to save image asset {kind.value}: {exc}") from exc
        relative = path.relative_to(self.settings.runtime_root)
        width, height = image.size
        return StoredAsset(kind=kind, file_path=str(relative), width=width, height=height)

    def _resize_detail(self, image: Image.Image) -> Image.Image:
        width = 860
        height = int(image.size[1] * width / image.size[0])
        return image.resize((width, height), Image.LANCZOS)

    def _create_framed_variant(
        self,
        image: Image.Image,
        target_height: int,
        icon_name: Optional[str] = None,
    ) -> Image.Image:
        resized = image.resize(
            (int(image.size[0] * target_height / image.size[1]), target_height),
            Image.LANCZOS,
        )
        framed = Image.new("RGBA", resized.size, (125, 125, 125, 255))
        inner = resized.resize((resized.size[0] - 2, resized.size[1] - 2), Image.LANCZOS)
        framed.paste(inner, (1, 1))

        background = Image.new("RGBA", (1000, 1000), (252, 250, 245, 255))
        x_offset = int((1000 - framed.size[0]) / 2)
        y_offset = int((1000 - framed.size[1]) / 2)
        background.paste(framed, (x_offset, y_offset), framed)

        if icon_name:
            self._paste_icon(background, icon_name, x_offset + framed.size[0], y_offset + framed.size[1])
        return background.convert("RGB")

    def _paste_icon(self, image: Image.Image, icon_name: str, end_x: int, end_y: int) -> None:
        icon_path = self.settings.resource_dir / icon_name
        if not icon_path.exists():
            raise StorageFailedError(f"Required icon is missing: {icon_path}")
        icon = self._prepare_overlay_icon(icon_path)
        start_x = end_x - int(icon.size[0] / 2)
        start_y = end_y - int(icon.size[1] / 2)
        image.paste(icon, (start_x, start_y), icon)

    def _prepare_overlay_icon(self, icon_path: Path) -> Image.Image:
        icon = Image.open(icon_path).convert("RGBA")
        return self._remove_corner_background(icon)

    def _remove_corner_background(self, image: Image.Image, tolerance: int = 28) -> Image.Image:
        width, height = image.size
        if width == 0 or height == 0:
            return image

        source = image.copy()
        pixels = source.load()
        alpha = source.getchannel("A").copy()

        corner_samples = {
            pixels[0, 0][:3],
            pixels[width - 1, 0][:3],
            pixels[0, height - 1][:3],
            pixels[width - 1, height - 1][:3],
        }

        def is_background(rgb: tuple[int, int, int]) -> bool:
            return any(
                max(abs(channel - sample_channel) for channel, sample_channel in zip(rgb, sample)) <= tolerance
                for sample in corner_samples
            )

        queue: deque[tuple[int, int]] = deque()
        visited: set[tuple[int, int]] = set()
        border_points = (
            [(x, 0) for x in range(width)]
            + [(x, height - 1) for x in range(width)]
            + [(0, y) for y in range(height)]
            + [(width - 1, y) for y in range(height)]
        )

        for x, y in border_points:
            if (x, y) in visited:
                continue
            rgba = pixels[x, y]
            if rgba[3] == 0 or is_background(rgba[:3]):
                visited.add((x, y))
                queue.append((x, y))

        while queue:
            x, y = queue.popleft()
            alpha.putpixel((x, y), 0)
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if nx < 0 or ny < 0 or nx >= width or ny >= height or (nx, ny) in visited:
                    continue
                rgba = pixels[nx, ny]
                if rgba[3] == 0 or is_background(rgba[:3]):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        source.putalpha(alpha)
        bbox = alpha.getbbox()
        if bbox:
            return source.crop(bbox)
        return source
