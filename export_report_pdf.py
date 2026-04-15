from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "REPORT.md"
TARGET = ROOT / "REPORT.pdf"
PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 50
TOP_MARGIN = 800
LINE_HEIGHT = 16
LINES_PER_PAGE = 44


def normalize_markdown(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.replace("`", "").replace("•", "-")
        if line.startswith("# "):
            lines.append(line[2:].upper())
        elif line.startswith("## "):
            lines.append(line[3:])
        else:
            lines.append(line)
    return lines


def paginate(lines: list[str]) -> list[list[str]]:
    return [lines[index : index + LINES_PER_PAGE] for index in range(0, len(lines), LINES_PER_PAGE)]


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def page_stream(lines: list[str]) -> bytes:
    chunks = ["BT", "/F1 11 Tf", f"{LEFT_MARGIN} {TOP_MARGIN} Td"]
    for index, line in enumerate(lines):
        if index > 0:
            chunks.append(f"0 -{LINE_HEIGHT} Td")
        chunks.append(f"({pdf_escape(line)}) Tj")
    chunks.append("ET")
    return "\n".join(chunks).encode("latin-1", errors="replace")


def build_pdf(page_lines: list[list[str]]) -> bytes:
    objects: list[bytes] = []

    def add_object(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content_ids: list[int] = []
    page_ids: list[int] = []
    for lines in page_lines:
        stream = page_stream(lines)
        content_id = add_object(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        content_ids.append(content_id)
        page_ids.append(0)

    pages_obj_index = len(objects) + 1
    for index, content_id in enumerate(content_ids):
        page_body = (
            f"<< /Type /Page /Parent {pages_obj_index} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_obj} 0 R >> >> >>"
        ).encode()
        page_ids[index] = add_object(page_body)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_obj = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
    catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")

    xref_start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def main() -> None:
    lines = normalize_markdown(SOURCE.read_text(encoding="utf-8"))
    pdf_bytes = build_pdf(paginate(lines))
    TARGET.write_bytes(pdf_bytes)


if __name__ == "__main__":
    main()
