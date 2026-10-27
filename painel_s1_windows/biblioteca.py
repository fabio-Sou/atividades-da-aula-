import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from protocolo import FRAME_BYTES, FRAME_HEIGHT, FRAME_WIDTH
from renderizar import (
    IMAGE_LAYOUT_CODES,
    ImagePixels,
    RENDERER_VERSION,
    load_image_pixels,
    orient_frame_for_preview,
    prepare_image_pixels,
    render_frame,
)

ImageLibraryEntry = dict[str, Any]


@dataclass(frozen=True)
class PreparedImage:
    pixels: bytes
    preview_path: Path


class ImageLibrary:
    def __init__(self, app_directory: Path) -> None:
        self.root = app_directory / "Imagens preparadas"
        self.visual_root = self.root / "Imagens visuais"
        self.data_root = self.root / "Dados internos"
        self.index_path = self.root / "biblioteca.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.visual_root.mkdir(exist_ok=True)
        self.data_root.mkdir(exist_ok=True)
        self.entries = self._load_entries()

    def _load_entries(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            return []
        try:
            entries = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"Não foi possível ler a biblioteca local {self.index_path}: {error}"
            ) from error
        if not isinstance(entries, list):
            raise ValueError("O arquivo da biblioteca local não contém uma lista.")
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or entry.get("kind") not in {"image", "folder"}
                or not isinstance(entry.get("path"), str)
                or not isinstance(entry.get("name"), str)
                or not isinstance(entry.get("cache_name"), str)
                or not isinstance(entry.get("prepared", {}), dict)
            ):
                raise ValueError("Um item salvo na biblioteca local é inválido.")
            for source_data in entry["prepared"].values():
                if (
                    not isinstance(source_data, dict)
                    or not isinstance(source_data.get("variants", {}), dict)
                ):
                    raise ValueError("O cache salvo na biblioteca local é inválido.")
                for variant in source_data.get("variants", {}).values():
                    if not isinstance(variant, dict):
                        raise ValueError("Uma imagem preparada salva é inválida.")
        return entries

    def _save_entries(self) -> None:
        temporary_path = self.index_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(self.entries, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self.index_path)

    def save(self) -> None:
        self._save_entries()

    def add(self, kind: str, path: Path) -> ImageLibraryEntry:
        if kind not in {"image", "folder"}:
            raise ValueError(f"Tipo de item desconhecido: {kind}")
        resolved_path = str(path.resolve())
        for entry in self.entries:
            if entry["kind"] == kind and entry["path"] == resolved_path:
                return entry

        display_name = path.name
        base_name = path.name if kind == "folder" else path.stem
        cache_name = base_name
        existing_names = {entry["cache_name"].casefold() for entry in self.entries}
        suffix = 2
        while cache_name.casefold() in existing_names:
            cache_name = f"{base_name} ({suffix})"
            suffix += 1
        entry: ImageLibraryEntry = {
            "kind": kind,
            "name": display_name,
            "path": resolved_path,
            "cache_name": cache_name,
            "prepared": {},
        }
        self.entries.append(entry)
        self._save_entries()
        return entry

    def remove(self, entry: ImageLibraryEntry) -> None:
        if entry not in self.entries:
            return
        for source_data in entry["prepared"].values():
            if not isinstance(source_data, dict):
                raise ValueError("Um item preparado na biblioteca é inválido.")
            variants = source_data.get("variants", {})
            if not isinstance(variants, dict):
                raise ValueError("As variantes preparadas na biblioteca são inválidas.")
            for variant in variants.values():
                if not isinstance(variant, dict):
                    raise ValueError("Uma variante preparada na biblioteca é inválida.")
                for key in ("data_path", "preview_path"):
                    relative_path = variant.get(key)
                    if not isinstance(relative_path, str):
                        continue
                    path = (self.root / relative_path).resolve()
                    if self.root.resolve() not in path.parents:
                        raise ValueError("O caminho salvo para cache está fora da pasta.")
                    if path.exists():
                        path.unlink()
        self.entries.remove(entry)
        self._save_entries()

    def prepare_image(
        self,
        entry: ImageLibraryEntry,
        source_path: Path,
        image_layout: str,
        orientation: str,
        *,
        save_index: bool = True,
    ) -> PreparedImage:
        layout_code = IMAGE_LAYOUT_CODES.get(image_layout)
        if layout_code is None:
            raise ValueError(f"Modo de ajuste desconhecido: {image_layout}")
        if orientation not in {"landscape", "portrait"}:
            raise ValueError(f"Orientação desconhecida: {orientation}")

        source = source_path.resolve()
        stat = source.stat()
        source_key = str(source)
        source_data = entry["prepared"].setdefault(source_key, {})
        if not isinstance(source_data, dict):
            raise ValueError("Os dados da imagem preparada estão inválidos.")
        variants = source_data.setdefault("variants", {})
        if not isinstance(variants, dict):
            raise ValueError("As variantes da imagem preparada estão inválidas.")
        variant_key = f"{layout_code}|{orientation}"
        cached = variants.get(variant_key)
        if cached is not None and not isinstance(cached, dict):
            raise ValueError("A cópia preparada da imagem está inválida.")
        if (
            cached is not None
            and cached.get("renderer_version") == RENDERER_VERSION
            and cached.get("size") == stat.st_size
            and cached.get("mtime_ns") == stat.st_mtime_ns
        ):
            data_path = self._cache_path(cached.get("data_path"))
            preview_path = self._cache_path(cached.get("preview_path"))
            if (
                data_path.is_file()
                and preview_path.is_file()
                and data_path.stat().st_size == FRAME_BYTES
            ):
                try:
                    with Image.open(preview_path) as preview:
                        preview.verify()
                    return PreparedImage(data_path.read_bytes(), preview_path)
                except (OSError, ValueError):
                    pass

        image: ImagePixels = load_image_pixels(source)
        pixels = prepare_image_pixels(image, layout_code, orientation)
        frame = render_frame(
            pixels,
            None,
            0.0,
            0,
            orientation=orientation,
            visible_metrics=set(),
        )
        preview_pixels, preview_width, preview_height = orient_frame_for_preview(
            frame,
            orientation,
        )
        visual_directory = (
            self.visual_root
            / entry["cache_name"]
            / f"{image_layout} - {'Em pé' if orientation == 'portrait' else 'Deitada'}"
        )
        data_directory = (
            self.data_root
            / entry["cache_name"]
            / f"{image_layout} - {'Em pé' if orientation == 'portrait' else 'Deitada'}"
        )
        visual_directory.mkdir(parents=True, exist_ok=True)
        data_directory.mkdir(parents=True, exist_ok=True)
        preview_name = source.stem
        duplicate_stem = any(
            Path(existing_path).stem.casefold() == source.stem.casefold()
            and existing_path != source_key
            for existing_path in entry["prepared"]
        )
        if duplicate_stem:
            preview_name += f" ({source.suffix.lstrip('.').upper()})"
        preview_path = visual_directory / f"{preview_name}.png"
        data_path = data_directory / f"{source.name}.rgb565"

        data_path.write_bytes(pixels)
        Image.frombytes(
            "RGB",
            (preview_width, preview_height),
            _rgb565_to_rgb(preview_pixels),
        ).save(preview_path, format="PNG")
        variants[variant_key] = {
            "renderer_version": RENDERER_VERSION,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "data_path": str(data_path.relative_to(self.root)),
            "preview_path": str(preview_path.relative_to(self.root)),
        }
        if save_index:
            self._save_entries()
        return PreparedImage(pixels, preview_path)

    def _cache_path(self, relative_path: Any) -> Path:
        if not isinstance(relative_path, str):
            raise ValueError("O caminho salvo para cache é inválido.")
        path = (self.root / relative_path).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("O caminho salvo para cache está fora da pasta.")
        return path


def _rgb565_to_rgb(pixels: bytes) -> bytes:
    if len(pixels) != FRAME_BYTES:
        raise ValueError("A imagem preparada tem tamanho inválido.")
    rgb = bytearray(FRAME_WIDTH * FRAME_HEIGHT * 3)
    for source_offset in range(0, len(pixels), 2):
        value = int.from_bytes(pixels[source_offset : source_offset + 2], "big")
        target_offset = source_offset // 2 * 3
        rgb[target_offset] = ((value >> 11) & 0x1F) * 255 // 31
        rgb[target_offset + 1] = ((value >> 5) & 0x3F) * 255 // 63
        rgb[target_offset + 2] = (value & 0x1F) * 255 // 31
    return bytes(rgb)
