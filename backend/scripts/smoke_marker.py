"""Read-only, fully local Marker check; prints structure counts, never document text."""

import argparse
from collections import Counter
from pathlib import Path

from app.services.marker_service import convert_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    if not args.pdf.is_file() or args.pdf.suffix.lower() != ".pdf":
        parser.error("Provide an existing PDF file")
    parsed = convert_pdf(args.pdf)
    types = Counter(block.block_type for page in parsed.pages for block in page.blocks)
    print(f"pages={len(parsed.pages)} images={len(parsed.images)} markdown_chars={len(parsed.markdown)}")
    print("blocks=" + ", ".join(f"{name}:{count}" for name, count in sorted(types.items())))
    print("pages_with_text=" + ",".join(str(page.page_number) for page in parsed.pages if page.blocks))


if __name__ == "__main__":
    main()
