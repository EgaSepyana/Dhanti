import io

from pypdf import PdfReader

CHUNK_SIZE_CHARS = 1000


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 100:
        return False
    return stripped.isupper() or (stripped.istitle() and len(stripped.split()) <= 12)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> list[str]:
    chunks = []
    for start in range(0, len(text), chunk_size):
        piece = text[start : start + chunk_size].strip()
        if piece:
            chunks.append(piece)
    return chunks


def parse_pdf(content: bytes) -> tuple[int, dict, list[dict]]:
    reader = PdfReader(io.BytesIO(content))
    page_count = len(reader.pages)

    headings: list[dict] = []
    chunks: list[dict] = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        for line in text.splitlines():
            if _is_heading(line):
                headings.append({"text": line.strip(), "page": page_num})

        for piece in chunk_text(text):
            chunks.append({"text": piece, "page": page_num, "embedding_id": None})

    structure = {"headings": headings}
    return page_count, structure, chunks
