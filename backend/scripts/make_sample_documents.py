"""Generate fictional sample documents in ../sample-data for the upload demo."""
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pdfgen import make_pdf  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "sample-data"
FICTION = "SYNTHETIC DEMO RECORD - FICTIONAL PATIENT - NOT FOR CLINICAL USE"


def png(width: int = 320, height: int = 200) -> bytes:
    """A plain placeholder PNG (no readable text) to demo the no-OCR manual-review path."""
    rows = b"".join(b"\x00" + bytes([230, 244, 246] * width) for _ in range(height))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "sample_lab_report_nov2026.pdf").write_bytes(make_pdf([
        "Blood Report - Quarterly Diabetes Panel", FICTION, "",
        "Laboratory: CityCare Diagnostics (fictional)", "Patient: Ananya Rao (fictional)",
        "Report date: 2026-11-20", "Referring doctor: Dr. Meera Iyer", "",
        "Test | Result | Unit | Reference range",
        "HbA1c | 6.7 | % | 4.0 - 5.6 %",
        "Fasting Blood Glucose | 112 | mg/dL | 70 - 99 mg/dL",
        "Serum Creatinine | 1.0 | mg/dL | 0.5 - 1.1 mg/dL",
        "eGFR | 75 | mL/min/1.73m2 | >= 90 mL/min/1.73m2",
        "Urine Albumin/Creatinine Ratio | 25 | mg/g | < 30 mg/g",
    ], "Sample lab report"))
    (OUT / "sample_prescription_ortho.pdf").write_bytes(make_pdf([
        "Prescription", FICTION, "",
        "Prescriber: Dr. Rohan Kulkarni (fictional orthopaedic surgeon)",
        "Facility: Greenleaf Bone & Joint Clinic (fictional)", "Date: 21/11/2026",
        "Diagnosis: Early osteoarthritis, right knee", "Allergies: Penicillin", "", "Rx:",
        "- Paracetamol 650 mg | Three times daily as needed | 10 days",
        "- Glucosamine 1500 mg | Once daily | 8 weeks",
        "", "Advice: physiotherapy, weight management. Avoid regular NSAID use given kidney function.",
    ], "Sample prescription"))
    (OUT / "sample_scanned_xray.png").write_bytes(png())
    print("Wrote sample documents to", OUT)


if __name__ == "__main__":
    main()
