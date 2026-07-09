import os
import re
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepInFrame
)
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
    PDF_ANSWER_MIN_RATIO,
    EXAM_WORDS_PER_FILE,
)

KOREAN_FONT = "HYGothic-Medium"
LATIN_FONT = "Helvetica"
LATIN_FONT_BOLD = "Helvetica-Bold"

BODY_FONT_SIZE = 9      # so'z qatorlari uchun boshlang'ich (maksimal) shrift
BODY_MIN_FONT_SIZE = 6  # juda uzun so'zlar uchun ruxsat etilgan eng kichik shrift
CELL_PAD_LR = 3          # chap+o'ng padding (har biri, nuqtada)
CELL_PAD_TB = 2          # yuqori+past padding (har biri, nuqtada)

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
        leading=size + 2,
        alignment=TA_CENTER,
    )


def _clean(text):
    return text.lstrip("*") if isinstance(text, str) else text


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _p(text, font, size=10, bold=False):
    return Paragraph(_escape(text), _style(font, size, bold))


def _fit_font_size(text, font, max_width_pt, base_size=BODY_FONT_SIZE, min_size=BODY_MIN_FONT_SIZE, bold=False):
    """
    Matn berilgan kenglikka BITTA QATORDA sig'ishi uchun kerakli shriftni
    hisoblaydi. Uzun o'zbekcha/koreyscha so'zlar 2 qatorga bo'linib
    pastdagi qatorlarni pastga surib yubormasligi uchun - matn 2 qatorga
    bo'linish o'rniga shrift biroz kichrayadi va bitta qatorda qoladi.
    """
    _ensure_fonts()
    font_name = LATIN_FONT_BOLD if (font == LATIN_FONT and bold) else font
    plain = str(text)
    size = base_size
    while size > min_size:
        try:
            width = pdfmetrics.stringWidth(plain, font_name, size)
        except Exception:
            break
        if width <= max_width_pt:
            return size
        size -= 0.5
    return min_size


def _p_fit(text, font, max_width_pt, base_size=BODY_FONT_SIZE, min_size=BODY_MIN_FONT_SIZE, bold=False):
    size = _fit_font_size(text, font, max_width_pt, base_size, min_size, bold)
    return _p(text, font, size, bold)


def split_words_into_groups(words, words_per_file=None):
    if words_per_file is None:
        words_per_file = EXAM_WORDS_PER_FILE
    return [words[i:i + words_per_file] for i in range(0, len(words), words_per_file)]


def _header_paragraph(location, list_num, total_lists):
    if not location:
        return None
    loc = _strip_emoji(location)
    # DIQQAT: location matnida koreyscha va lotin harflar aralash bo'lishi mumkin
    # (masalan "35-topik › 읽기"). LATIN_FONT (Helvetica) koreyscha harflarni
    # chiza olmaydi va ular qora katakcha (■■) bo'lib ko'rinadi. Shuning uchun
    # KOREAN_FONT ishlatiladi - u lotin harflarni ham to'g'ri chizadi.
    return _p(f"{loc} - List {list_num}/{total_lists}", KOREAN_FONT, 11, bold=True)


def _build_word_table(group_words, mode, col_widths, header_names, header_fonts, bilingual, row_height_pt):
    num_w, q_w, a_w = col_widths
    q_w_pt = q_w * cm - (2 * CELL_PAD_LR)
    a_w_pt = a_w * cm - (2 * CELL_PAD_LR)

    data = [[_p(header_names[i], header_fonts[i], 10, bold=True) for i in range(3)]]

    for idx, (korean, uzbek) in enumerate(group_words, 1):
        korean_c = _clean(korean)
        uzbek_c = _clean(uzbek)
        if bilingual:
            row = [
                _p(idx, LATIN_FONT, 9, True),
                _p_fit(korean_c, KOREAN_FONT, q_w_pt),
                _p_fit(uzbek_c, LATIN_FONT, a_w_pt),
            ]
        else:
            question = korean_c if mode == "kr_to_uz" else uzbek_c
            q_font = KOREAN_FONT if mode == "kr_to_uz" else LATIN_FONT
            row = [_p(idx, LATIN_FONT, 9, True), _p_fit(question, q_font, q_w_pt), ""]
        data.append(row)

    # Har bir qatorga BIR XIL, oldindan hisoblangan balandlik beriladi -
    # shu tufayli jadval chegaralari har doim A4/A5 balandligini to'liq
    # to'ldirib chiqadi (na kam, na ortiq), va so'z 2 qatorga bo'linib
    # ketsa ham (kamdan-kam holatda) keyingi qatorlar joyidan siljimaydi.
    row_heights = [row_height_pt] * len(data)

    table = Table(data, colWidths=[num_w * cm, q_w * cm, a_w * cm], rowHeights=row_heights, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.88, 0.88, 0.88)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), CELL_PAD_TB),
        ("BOTTOMPADDING", (0, 0), (-1, -1), CELL_PAD_TB),
        ("LEFTPADDING", (0, 0), (-1, -1), CELL_PAD_LR),
        ("RIGHTPADDING", (0, 0), (-1, -1), CELL_PAD_LR),
    ]))
    return table


def _build_half_flowables(group_words, location, list_num, total_lists, mode, col_widths, header_names, header_fonts, bilingual, row_height_pt):
    flow = []
    header = _header_paragraph(location, list_num, total_lists)
    if header:
        flow.append(header)
        flow.append(Spacer(1, 0.15 * cm))
    flow.append(_build_word_table(group_words, mode, col_widths, header_names, header_fonts, bilingual, row_height_pt))
    return flow


def _compute_question_answer_widths(words, mode):
    """
    Savol ustuniga qo'yiladigan matn uzunligiga qarab ustun kengligini
    moslashtiradi. Masalan uz_to_kr rejimida savol ustunida o'zbekcha
    (odatda uzunroq) so'zlar bo'ladi - shu holatda savol ustuniga ko'proq
    joy beriladi. Qolgan haddan tashqari uzun so'zlar esa _fit_font_size
    orqali avtomatik kichraytiriladi (2 qatorga bo'linmasligi uchun).
    """
    available = PDF_HALF_WIDTH_CM - (2 * PDF_MARGIN_CM) - PDF_COL_NUMBER_WIDTH_CM

    question_texts = []
    for korean, uzbek in words:
        text = _clean(korean) if mode == "kr_to_uz" else _clean(uzbek)
        if text:
            question_texts.append(text)

    avg_len = (sum(len(t) for t in question_texts) / len(question_texts)) if question_texts else 5

    needed_ratio = (avg_len * 0.20) / available if available else PDF_QUESTION_RATIO
    q_ratio = max(PDF_QUESTION_RATIO, min(needed_ratio, 1 - PDF_ANSWER_MIN_RATIO))
    a_ratio = 1 - q_ratio

    return PDF_COL_NUMBER_WIDTH_CM, available * q_ratio, available * a_ratio


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
    words_per_list = EXAM_WORDS_PER_FILE

    if bilingual:
        col_widths = _compute_bilingual_widths(words)
        header_names = ["번호", "한국어", "O'zbekcha"]
        header_fonts = [KOREAN_FONT, KOREAN_FONT, LATIN_FONT]
    else:
        col_widths = _compute_question_answer_widths(words, mode)
        header_names = ["번호", "질문", "답안"]
        header_fonts = [KOREAN_FONT, KOREAN_FONT, KOREAN_FONT]

    temp_dir = "temp_exams"
    os.makedirs(temp_dir, exist_ok=True)
    filepath = os.path.join(temp_dir, f"{filename_prefix}.pdf")

    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4),
                             leftMargin=0, rightMargin=0, topMargin=0.5 * cm, bottomMargin=0.5 * cm)
    elements = []
    half_w = PDF_HALF_WIDTH_CM * cm

    # SimpleDocTemplate ichki frame'ga standart 6pt padding qo'shadi
    # (yuqori+past), shu sababli xavfsizlik uchun ozgina joy ayirib qo'yamiz.
    available_height = doc.height - 12
    available_width = doc.width

    # Sarlavha (title) uchun ketadigan joy: 11pt shrift (leading 13) + spacer
    title_block_height = 13 + (0.15 * cm)

    # Jadval (header qatori + so'z qatorlari) uchun qolgan joyni HAMMA
    # qatorlarga TENG bo'lib taqsimlaymiz - shu tufayli jadval chegarasi
    # aynan sahifa (A5) balandligining oxirigacha to'liq yetib boradi,
    # bo'sh joy qolmaydi.
    total_rows = words_per_list + 1  # +1 = ustun sarlavhasi qatori
    row_height_pt = (available_height - title_block_height) / total_rows

    for i in range(0, total_lists, 2):
        left_flow = _build_half_flowables(groups[i], location, i + 1, total_lists, mode, col_widths, header_names, header_fonts, bilingual, row_height_pt)
        if i + 1 < total_lists:
            right_flow = _build_half_flowables(groups[i + 1], location, i + 2, total_lists, mode, col_widths, header_names, header_fonts, bilingual, row_height_pt)
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

        # Butun sahifa (ikkala ustun birga) bitta KeepInFrame ichiga o'raladi -
        # bu FAQAT yakuniy xavfsizlik to'ri (haddan tashqari noodatiy holat
        # uchun); qator balandligi endi FIKS va oldindan hisoblangani uchun
        # bu deyarli hech qachon ishga tushmaydi.
        wrapped_page = KeepInFrame(
            available_width, available_height, [page_table],
            mode="shrink", hAlign="CENTER", vAlign="TOP"
        )
        elements.append(wrapped_page)
        if i + 2 < total_lists:
            elements.append(PageBreak())

    doc.build(elements)
    return filepath


def create_exam_pdf(words, location=None, mode="kr_to_uz", filename_prefix="exam"):
    return _build_pdf(words, location, mode, filename_prefix, bilingual=False)


def create_exam_pdf_bilingual(words, location=None, filename_prefix="bilingual"):
    return _build_pdf(words, location, "both", filename_prefix, bilingual=True)