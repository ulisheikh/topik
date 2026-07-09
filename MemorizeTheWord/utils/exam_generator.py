import os
import re
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from config import (
    PDF_HALF_WIDTH_CM,
    PDF_MARGIN_CM,
    PDF_COL_NUMBER_WIDTH_CM,
    PDF_QUESTION_RATIO,
    PDF_ANSWER_RATIO,
    PDF_BILINGUAL_MIN_RATIO,
    PDF_BILINGUAL_MAX_RATIO,
)

KOREAN_FONT = "HYGothic-Medium"
LATIN_FONT = "Helvetica"
LATIN_FONT_BOLD = "Helvetica-Bold"

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF"
    "]+",
    flags=re.UNICODE,
)

_fonts_ready = False


def _ensure_fonts():
    global _fonts_ready
    if _fonts_ready:
        return
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))
    except Exception:
        pass
    _fonts_ready = True


def _strip_emoji(text):
    return _EMOJI_PATTERN.sub("", str(text)).strip()


def _style(font, size=10, bold=False):
    _ensure_fonts()
    font_name = LATIN_FONT_BOLD if (font == LATIN_FONT and bold) else font
    return ParagraphStyle(
        name=f"s_{font}_{size}_{bold}",
        fontName=font_name,
        fontSize=size,
        leading=size + 3,
        alignment=TA_CENTER,
    )


def _clean(text):
    return text.lstrip("*") if isinstance(text, str) else text


def _p(text, font, size=10, bold=False):
    text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(text, _style(font, size, bold))


def split_words_into_groups(words, words_per_file=24):
    return [words[i:i + words_per_file] for i in range(0, len(words), words_per_file)]


def _header_paragraph(location, list_num, total_lists):
    if not location:
        return None
    loc = _strip_emoji(location)
    return _p(f"{loc} - List {list_num}/{total_lists}", LATIN_FONT, 11, bold=True)


def _build_word_table(group_words, mode, col_widths, header_names, header_fonts, bilingual):
    num_w, q_w, a_w = col_widths
    data = [[_p(header_names[i], header_fonts[i], 11, bold=True) for i in range(3)]]

    for idx, (korean, uzbek) in enumerate(group_words, 1):
        korean_c = _clean(korean)
        uzbek_c = _clean(uzbek)
        if bilingual:
            row = [_p(idx, LATIN_FONT, 10, True), _p(korean_c, KOREAN_FONT, 10), _p(uzbek_c, LATIN_FONT, 10)]
        else:
            question = korean_c if mode == "kr_to_uz" else uzbek_c
            q_font = KOREAN_FONT if mode == "kr_to_uz" else LATIN_FONT
            row = [_p(idx, LATIN_FONT, 10, True), _p(question, q_font, 10), ""]
        data.append(row)

    table = Table(data, colWidths=[num_w * cm, q_w * cm, a_w * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.88, 0.88, 0.88)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _build_half_flowables(group_words, location, list_num, total_lists, mode, col_widths, header_names, header_fonts, bilingual):
    flow = []
    header = _header_paragraph(location, list_num, total_lists)
    if header:
        flow.append(header)
        flow.append(Spacer(1, 0.25 * cm))
    flow.append(_build_word_table(group_words, mode, col_widths, header_names, header_fonts, bilingual))
    return flow


def _compute_question_answer_widths():
    available = PDF_HALF_WIDTH_CM - (2 * PDF_MARGIN_CM) - PDF_COL_NUMBER_WIDTH_CM
    return PDF_COL_NUMBER_WIDTH_CM, available * PDF_QUESTION_RATIO, available * PDF_ANSWER_RATIO


def _compute_bilingual_widths(all_words):
    available = PDF_HALF_WIDTH_CM - (2 * PDF_MARGIN_CM) - PDF_COL_NUMBER_WIDTH_CM
    kr = [len(_clean(k)) for k, u in all_words if _clean(k)]
    uz = [len(_clean(u)) for k, u in all_words if _clean(u)]
    avg_kr = sum(kr) / len(kr) if kr else 1
    avg_uz = sum(uz) / len(uz) if uz else 1
    total = avg_kr + avg_uz
    uz_ratio = (avg_uz / total) if total else 0.5
    uz_ratio = max(PDF_BILINGUAL_MIN_RATIO, min(PDF_BILINGUAL_MAX_RATIO, uz_ratio))
    return PDF_COL_NUMBER_WIDTH_CM, available * (1 - uz_ratio), available * uz_ratio


def _build_pdf(words, location, mode, filename_prefix, bilingual):
    groups = split_words_into_groups(words)
    total_lists = len(groups)

    if bilingual:
        col_widths = _compute_bilingual_widths(words)
        header_names = ["번호", "한국어", "O'zbekcha"]
        header_fonts = [KOREAN_FONT, KOREAN_FONT, LATIN_FONT]
    else:
        col_widths = _compute_question_answer_widths()
        header_names = ["번호", "질문", "답안"]
        header_fonts = [KOREAN_FONT, KOREAN_FONT, KOREAN_FONT]

    temp_dir = "temp_exams"
    os.makedirs(temp_dir, exist_ok=True)
    filepath = os.path.join(temp_dir, f"{filename_prefix}.pdf")

    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4),
                             leftMargin=0, rightMargin=0, topMargin=0.5 * cm, bottomMargin=0.5 * cm)
    elements = []
    half_w = PDF_HALF_WIDTH_CM * cm

    for i in range(0, total_lists, 2):
        left_flow = _build_half_flowables(groups[i], location, i + 1, total_lists, mode, col_widths, header_names, header_fonts, bilingual)
        if i + 1 < total_lists:
            right_flow = _build_half_flowables(groups[i + 1], location, i + 2, total_lists, mode, col_widths, header_names, header_fonts, bilingual)
        else:
            right_flow = [Spacer(1, 1)]

        page_table = Table([[left_flow, right_flow]], colWidths=[half_w, half_w])
        page_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), PDF_MARGIN_CM * cm),
            ("RIGHTPADDING", (0, 0), (0, 0), PDF_MARGIN_CM * cm),
            ("LEFTPADDING", (1, 0), (1, 0), PDF_MARGIN_CM * cm),
            ("RIGHTPADDING", (1, 0), (1, 0), PDF_MARGIN_CM * cm),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LINEAFTER", (0, 0), (0, 0), 0.5, colors.grey),
        ]))
        elements.append(page_table)
        if i + 2 < total_lists:
            elements.append(PageBreak())

    doc.build(elements)
    return filepath


def create_exam_pdf(words, location=None, mode="kr_to_uz", filename_prefix="exam"):
    return _build_pdf(words, location, mode, filename_prefix, bilingual=False)


def create_exam_pdf_bilingual(words, location=None, filename_prefix="bilingual"):
    return _build_pdf(words, location, "both", filename_prefix, bilingual=True)