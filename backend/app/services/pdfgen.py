"""Tiny dependency-free PDF writer for synthetic demo documents.

Produces a single-page text PDF whose text can be extracted with pypdf, so
the rule-based document extraction can be demonstrated on realistic files.
"""
from __future__ import annotations


def _esc(s: str) -> str:
    s = s.encode("latin-1", "replace").decode("latin-1")
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(lines: list[str], title: str = "MyKshema demo document") -> bytes:
    content_lines = ["BT", "/F1 10 Tf", "12 TL", "50 800 Td"]
    for i, line in enumerate(lines[:60]):
        if i == 0:
            content_lines.append("/F2 14 Tf")
            content_lines.append(f"({_esc(line)}) Tj T*")
            content_lines.append("/F1 10 Tf T*")
        else:
            content_lines.append(f"({_esc(line)}) Tj T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Title (" + _esc(title).encode("latin-1") + b") /Producer (MyKshema synthetic demo) >>",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 7 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
