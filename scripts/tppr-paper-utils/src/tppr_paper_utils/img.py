import pymupdf as fitz
from PIL import Image
import io


def extract_page_image(pdf_path: str, page_num: int, clip: tuple = None) -> Image.Image:
    """
    Render a page (or region of a page) as an image.

    Args:
        pdf_path: path to PDF
        page_num: 0-indexed page number
        clip: optional (x0, y0, x1, y1) to crop a region
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    if clip:
        rect = fitz.Rect(*clip)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)  # 2x zoom
    else:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    return img
