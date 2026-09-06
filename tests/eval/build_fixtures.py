"""One-off generator for this eval suite's new golden PDF fixtures.

Not run automatically by anything -- the existing fixtures under
`data/` (see `data/sample_treaty.pdf` etc.) were hand-built as minimal
raw PDF byte streams (`Tj` text-show operators, no PDF-writing library
in `requirements.txt`), and this follows the same approach so the new
fixtures need no new dependency. Run directly (`python -m
tests.eval.build_fixtures`) to regenerate the two files this module
writes to `data/`.
"""

from pathlib import Path

_FONT_SIZE = 12
_LINE_HEIGHT = 18
_TOP_Y = 750
_LEFT_X = 72


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(lines: list[str]) -> bytes:
    ops = [f"/F1 {_FONT_SIZE} Tf"]
    y = _TOP_Y
    for line in lines:
        ops.append(f"1 0 0 1 {_LEFT_X} {y} Tm")
        ops.append(f"({_escape(line)}) Tj")
        y -= _LINE_HEIGHT
    stream = "\n".join(ops).encode("latin-1")
    return stream


def build_pdf(pages: list[list[str]]) -> bytes:
    """Build a minimal multi-page PDF from a list of pages, each a list of text lines."""
    num_pages = len(pages)
    content_streams = [_content_stream(lines) for lines in pages]

    objects: list[bytes] = [b""] * (3 + 2 * num_pages + 1)
    # 1: Catalog, 2: Pages, 3..3+n-1: Page objects, 3+n..3+2n-1: Content streams, last: Font
    font_obj_num = 3 + 2 * num_pages

    kids = " ".join(f"{3 + i} 0 R" for i in range(num_pages))
    objects[0] = f"<< /Type /Catalog /Pages 2 0 R >>".encode("latin-1")
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>".encode("latin-1")
    for i in range(num_pages):
        page_obj_num = 3 + i
        content_obj_num = 3 + num_pages + i
        objects[page_obj_num - 1] = (
            f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {content_obj_num} 0 R >>"
        ).encode("latin-1")
    for i, stream in enumerate(content_streams):
        content_obj_num = 3 + num_pages + i
        objects[content_obj_num - 1] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )
    objects[font_obj_num - 1] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"

    xref_offset = len(out)
    total_objs = len(objects) + 1
    out += f"xref\n0 {total_objs}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode("latin-1")
    return bytes(out)


HARBORLIGHT_PAGES = [
    [
        "REINSURANCE TREATY AGREEMENT",
        "This Agreement is made between Harborlight Mutual Insurance",
        "Company (the \"Cedent\") and its Reinsurer, effective from the",
        "first day of January, 2026, for a term of one year unless",
        "terminated earlier under the provisions below. It sets out the",
        "terms on which the Reinsurer agrees to indemnify the Cedent for",
        "certain losses arising under its commercial property book.",
    ],
    [
        "FINANCIAL TERMS",
        "Indemnification begins once the Cedent's ultimate net loss from",
        "any single occurrence surpasses five hundred thousand dollars",
        "(USD 500,000). Beyond that threshold, the Reinsurer will cover",
        "the excess up to a maximum of two million five hundred thousand",
        "dollars (USD 2,500,000) per occurrence. In exchange, the Cedent",
        "shall pay the Reinsurer an annual premium of one hundred",
        "seventy-five thousand dollars (USD 175,000), due in advance.",
    ],
    [
        "EXCLUSIONS",
        "No indemnification is available under this Agreement for any",
        "loss caused by or resulting from war or warlike operations,",
        "nuclear reaction or radioactive contamination of any kind, acts",
        "of terrorism however defined, or pollution and environmental",
        "contamination of any nature.",
    ],
]

CONTINENTAL_PAGES = [
    [
        "EXCESS OF LOSS REINSURANCE CONTRACT",
        "Continental Assurance Partners (\"Cedent\") and the Reinsurer",
        "enter into this excess of loss contract governing the Cedent's",
        "casualty portfolio, effective 1 January 2026 through 31",
        "December 2026. This contract is subject to the laws of the",
        "State of New York.",
    ],
    [
        "LAYER TERMS",
        "The Reinsurer's liability attaches after the Cedent retains the",
        "first USD 750,000.00 of ultimate net loss on any one",
        "occurrence, and continues up to a further USD 3,000,000.00 in",
        "excess of that retention. The reinsurance premium payable by",
        "the Cedent for this protection is USD 225,000.00 annually,",
        "payable quarterly in equal installments.",
    ],
    [
        "EXCLUSIONS",
        "This contract does not respond to losses connected with",
        "asbestos-related bodily injury or property damage, cyber",
        "attacks or unauthorized access to electronic data, or any",
        "pandemic, epidemic, or other communicable disease event.",
    ],
]


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    (data_dir / "golden_harborlight_treaty.pdf").write_bytes(build_pdf(HARBORLIGHT_PAGES))
    (data_dir / "golden_continental_treaty.pdf").write_bytes(build_pdf(CONTINENTAL_PAGES))
    print("Wrote data/golden_harborlight_treaty.pdf and data/golden_continental_treaty.pdf")


if __name__ == "__main__":
    main()
