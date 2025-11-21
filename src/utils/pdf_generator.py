import io
import textwrap
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


def create_pdf_bytes(text: str, title: str | None = None) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left_margin = 20 * mm
    top_margin = 20 * mm
    y = height - top_margin

    if title:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left_margin, y, title)
        y -= 10 * mm

    c.setFont("Helvetica", 11)

    for paragraph in text.splitlines():
        if not paragraph.strip():
            # Blank line
            y -= 6 * mm
            continue
        wrapped = textwrap.wrap(paragraph, width=90)
        for line in wrapped:
            if y < 25 * mm:
                c.showPage()
                y = height - top_margin
                c.setFont("Helvetica", 11)
            c.drawString(left_margin, y, line)
            y -= 6 * mm

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
