"""Local, page-aware PDF conversion with Marker.

Marker models are loaded on the first PDF upload and reused for later uploads.
The service never enables Marker's optional cloud LLM processors.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import re
from threading import Lock

from bs4 import BeautifulSoup
from markdownify import markdownify


@dataclass(frozen=True, slots=True)
class ParsedBlock:
    block_type: str
    text: str
    section_title: str | None = None
    marker_id: str | None = None
    bbox: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedPage:
    page_number: int
    blocks: tuple[ParsedBlock, ...]
    extraction_method: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedPdf:
    pages: tuple[ParsedPage, ...]
    markdown: str
    images: dict[str, bytes]


class MarkerUnavailableError(RuntimeError):
    """Marker or its local model weights are unavailable."""


_converter = None
_conversion_lock = Lock()


def _require_cached_models() -> None:
    """Prevent Surya's S3 loader from downloading weights during an upload."""
    from surya.common.s3 import check_manifest
    from surya.settings import settings

    checkpoints = {
        settings.LAYOUT_MODEL_CHECKPOINT,
        settings.FOUNDATION_MODEL_CHECKPOINT,
        settings.RECOGNITION_MODEL_CHECKPOINT,
        settings.TABLE_REC_MODEL_CHECKPOINT,
        settings.DETECTOR_MODEL_CHECKPOINT,
        settings.OCR_ERROR_MODEL_CHECKPOINT,
    }
    missing = []
    for checkpoint in sorted(checkpoints):
        if checkpoint.startswith("s3://"):
            path = Path(settings.MODEL_CACHE_DIR) / checkpoint.removeprefix("s3://")
            if not check_manifest(str(path)):
                missing.append(str(path))
        elif not Path(checkpoint).is_dir():
            missing.append(checkpoint)
    if missing:
        raise MarkerUnavailableError(
            "Marker model weights are not cached locally: " + ", ".join(missing)
        )


def _field(item, name: str, default=None):
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def _children(item):
    return _field(item, "children") or ()


_STRUCTURED_BLOCKS = {
    "Title", "SectionHeader", "Table", "TableOfContents",
    "Equation", "Picture", "Figure",
}


def _content_blocks(item):
    if str(_field(item, "block_type", "")) in _STRUCTURED_BLOCKS:
        yield item
        return
    children = _children(item)
    if children:
        for child in children:
            yield from _content_blocks(child)
    else:
        yield item


def _composed_html(block) -> str:
    soup = BeautifulSoup(_field(block, "html", "") or "", "html.parser")
    children = {str(_field(child, "id")): child for child in _children(block)}
    for ref in soup.find_all("content-ref"):
        child = children.get(str(ref.get("src")))
        if child is not None:
            ref.replace_with(BeautifulSoup(_composed_html(child), "html.parser"))
        else:
            ref.decompose()
    return str(soup)


def _block_markdown(block) -> str:
    html = _composed_html(block)
    soup = BeautifulSoup(html, "html.parser")
    for math in soup.find_all("math"):
        content = math.get_text(" ", strip=True)
        math.replace_with(f"$${content}$$" if math.get("display") == "block" else f"${content}$")
    for image in soup.find_all("img"):
        alt = image.get("alt", "").strip()
        image.replace_with(f"[Image: {alt}]" if alt else "[Image]")
    for ref in soup.find_all("content-ref"):
        ref.decompose()
    text = markdownify(str(soup), heading_style="ATX").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def parse_marker_output(json_output, markdown_output) -> ParsedPdf:
    """Convert Marker's rendered output into ordered blocks with original pages."""
    current_section = None
    pages: list[ParsedPage] = []
    page_stats = (_field(json_output, "metadata") or {}).get("page_stats", [])
    for page_number, page in enumerate(_children(json_output), start=1):
        blocks: list[ParsedBlock] = []
        for leaf in _content_blocks(page):
            kind = str(_field(leaf, "block_type", "Text"))
            text = _block_markdown(leaf)
            if kind in {"SectionHeader", "Title"}:
                if text:
                    current_section = re.sub(r"\s+", " ", re.sub(r"^#+\s*", "", text)).strip()[:160]
                continue
            if text and text != "[Image]":
                raw_bbox = _field(leaf, "bbox") or ()
                blocks.append(ParsedBlock(
                    kind, text, current_section,
                    str(_field(leaf, "id")) if _field(leaf, "id") is not None else None,
                    tuple(float(value) for value in raw_bbox),
                ))
        method = page_stats[page_number - 1].get("text_extraction_method") if page_number <= len(page_stats) else None
        pages.append(ParsedPage(page_number, tuple(blocks), str(method) if method else None))

    image_bytes: dict[str, bytes] = {}
    for name, image in (_field(markdown_output, "images") or {}).items():
        safe_name = Path(str(name)).name
        if safe_name != str(name) or not safe_name:
            continue
        buffer = BytesIO()
        extension = Path(safe_name).suffix.lower()
        image_format = "PNG" if extension == ".png" else "WEBP" if extension == ".webp" else "JPEG"
        if image_format == "JPEG" and image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffer, format=image_format)
        image_bytes[safe_name] = buffer.getvalue()

    return ParsedPdf(
        pages=tuple(pages),
        markdown=_field(markdown_output, "markdown", "") or "",
        images=image_bytes,
    )


def convert_pdf(file_path: Path) -> ParsedPdf:
    """Run one local Marker conversion and render JSON plus Markdown from it."""
    global _converter
    # Set before importing Marker/Surya so a missing model fails instead of downloading.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["USE_TF"] = "0"
    os.environ["USE_FLAX"] = "0"
    os.environ.setdefault(
        "MODEL_CACHE_DIR", str(Path(__file__).resolve().parents[2] / ".models" / "marker")
    )
    os.environ.setdefault(
        "FONT_PATH", str(Path(os.environ["MODEL_CACHE_DIR"]) / "GoNotoCurrent-Regular.ttf")
    )
    with _conversion_lock:
        if _converter is None:
            try:
                if not Path(os.environ["FONT_PATH"]).is_file():
                    raise MarkerUnavailableError(
                        f"Marker font is not cached locally: {os.environ['FONT_PATH']}"
                    )
                _require_cached_models()
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict

                _converter = PdfConverter(artifact_dict=create_model_dict(), config={"use_llm": False})
            except MarkerUnavailableError:
                raise
            except Exception as exc:
                raise MarkerUnavailableError(
                    "Marker could not load its local models. Install marker-pdf and cache model weights before working offline."
                ) from exc
        from marker.renderers.json import JSONRenderer
        from marker.renderers.markdown import MarkdownRenderer

        document = _converter.build_document(str(file_path))
        return parse_marker_output(JSONRenderer()(document), MarkdownRenderer()(document))
