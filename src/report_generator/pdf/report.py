"""The mock exam report card PDF (layout ported from the prototype)."""

import io
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Indenter, Paragraph, SimpleDocTemplate, Spacer, Table
from reportlab.platypus.doctemplate import BaseDocTemplate

from report_generator.config import AppConfig
from report_generator.domain.scoring import StudentResult, Tier
from report_generator.pdf.flowables import ProgressBar, SectionHeader, SemiCircleGauge

ASSETS_DIR = Path(__file__).parent / "assets"
PAGE_WIDTH, PAGE_HEIGHT = A4
SIDE_MARGIN = 40


@dataclass(frozen=True)
class ReportInput:
    student_name: str
    certification: str
    result: StudentResult


class _Palette:
    def __init__(self, config: AppConfig) -> None:
        c = config.colors
        self.green_dark = colors.HexColor(c.green_dark)
        self.background = colors.HexColor(c.black)
        self._by_tier = {
            Tier.PASS: colors.HexColor(c.green_light),
            Tier.AVERAGE: colors.HexColor(c.yellow),
            Tier.FAIL: colors.HexColor(c.red),
        }

    def for_tier(self, tier: Tier) -> Color:
        return self._by_tier[tier]


# -- Page decorations ---------------------------------------------------------


def _draw_header(canv: Canvas, config: AppConfig, palette: _Palette) -> None:
    canv.saveState()
    logo = ASSETS_DIR / "logo.png"
    canv.drawImage(
        str(logo),
        SIDE_MARGIN,
        PAGE_HEIGHT - 85,
        width=140,
        height=50,
        preserveAspectRatio=True,
        mask="auto",
    )
    subtitle = config.texts.subtitle
    canv.setFont("Helvetica", 14)
    canv.setFillColor(colors.black)
    canv.drawRightString(PAGE_WIDTH - SIDE_MARGIN, PAGE_HEIGHT - 80, subtitle)
    canv.setStrokeColor(palette.green_dark)
    canv.setLineWidth(2)
    canv.line(SIDE_MARGIN, PAGE_HEIGHT - 85, PAGE_WIDTH - SIDE_MARGIN, PAGE_HEIGHT - 85)
    canv.restoreState()


def _link_for(kind: str, text: str) -> str:
    if kind == "tel":
        return "tel:" + re.sub(r"[^\d+]", "", text)
    if kind == "mailto":
        return "mailto:" + text
    return text if text.startswith("http") else f"https://{text}"


def _draw_footer(canv: Canvas, config: AppConfig, palette: _Palette) -> None:
    footer_height, margin, icon_size, gap, line_height, font_size = 60, 50, 20, 5, 12, 10
    contacts = config.contacts
    phones = [p for p in (contacts.phone.landline, contacts.phone.mobile) if p]
    blocks = [
        ("phone.png", phones, "tel"),
        ("email.png", [contacts.email], "mailto"),
        ("web.png", [contacts.website], "url"),
    ]

    canv.saveState()
    canv.setFillColor(palette.green_dark)
    canv.rect(0, 0, PAGE_WIDTH, footer_height, fill=1, stroke=0)
    center_y = footer_height / 2
    canv.setFont("Helvetica", font_size)

    for i, (icon, lines, kind) in enumerate(blocks):
        if not lines:
            continue
        text_width = max(canv.stringWidth(line, "Helvetica", font_size) for line in lines)
        block_width = icon_size + gap + text_width
        # Left-aligned, centred, right-aligned.
        x = (margin, PAGE_WIDTH / 2 - block_width / 2, PAGE_WIDTH - margin - block_width)[i]
        canv.drawImage(
            str(ASSETS_DIR / icon),
            x,
            center_y - icon_size / 2,
            width=icon_size,
            height=icon_size,
            preserveAspectRatio=True,
            mask="auto",
        )
        canv.setFillColor(colors.white)
        text_x = x + icon_size + gap
        first_y = center_y + line_height * len(lines) / 2 - line_height + 2
        for j, line in enumerate(lines):
            y = first_y - j * line_height
            canv.drawString(text_x, y, line)
            width = canv.stringWidth(line, "Helvetica", font_size)
            canv.linkURL(_link_for(kind, line), (text_x, y, text_x + width, y + line_height))
    canv.restoreState()


# -- Body ---------------------------------------------------------------------


def _conclusion_text(config: AppConfig, tier: Tier) -> str:
    texts = config.texts
    return {
        Tier.PASS: texts.pass_conclusion_text,
        Tier.AVERAGE: texts.average_conclusion_text,
        Tier.FAIL: texts.fail_conclusion_text,
    }[tier]


def _status_text(config: AppConfig, tier: Tier) -> str:
    texts = config.texts
    return {
        Tier.PASS: texts.status_pass,
        Tier.AVERAGE: texts.status_average,
        Tier.FAIL: texts.status_fail,
    }[tier]


def _doubt_text(config: AppConfig) -> str:
    mobile = config.contacts.phone.mobile
    if not (config.texts.doubt_text and mobile):
        return ""
    return config.texts.doubt_text.format(
        mobile_clean=re.sub(r"[^\d+]", "", mobile), mobile_display=mobile
    )


def _body(report: ReportInput, config: AppConfig, palette: _Palette) -> list[Flowable]:
    styles = getSampleStyleSheet()
    label_style = ParagraphStyle("InfoLabel", parent=styles["Normal"], fontSize=12, leading=13)
    data_style = ParagraphStyle(
        "InfoData", parent=styles["Heading3"], fontSize=14, leading=16, spaceAfter=5
    )
    justified = ParagraphStyle(
        "Justified", parent=styles["Normal"], alignment=TA_JUSTIFY, leading=12, fontSize=11
    )
    skill_style = ParagraphStyle("Skill", parent=styles["Normal"], leading=12, fontSize=11)
    status_style = ParagraphStyle(
        "Status", parent=styles["Heading3"], alignment=TA_CENTER, fontSize=16
    )

    labels = config.texts.labels
    result = report.result
    group = config.group_for(report.certification)
    elements: list[Flowable] = []

    if config.texts.intro_text:
        intro = config.texts.intro_text.replace("{min_pass}", str(group.pass_threshold))
        elements += [Paragraph(intro, justified), Spacer(1, 10)]

    def label(text: str) -> Paragraph:
        return Paragraph(f"<b>{escape(text)}</b>", label_style)

    info = Table(
        [
            [label(labels.student), label(labels.certification)],
            [
                Paragraph(escape(report.student_name), data_style),
                Paragraph(escape(report.certification), data_style),
            ],
        ],
        colWidths=[300, 200],
        style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
        ],
    )
    exams = Table(
        [[label(labels.exams_done)], [Paragraph(str(result.exams_done), data_style)]],
        colWidths=[500],
        style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
            ("LINEBELOW", (0, 1), (-1, 1), 1.2, colors.grey),
        ],
    )
    elements += [info, Spacer(1, 5), exams, Spacer(1, 5)]

    left: list[Flowable] = [
        SectionHeader(labels.individual_score, palette.green_dark, width=240, height=25),
        Spacer(1, 8),
    ]
    for skill in result.skills:
        left += [
            Paragraph(escape(skill.skill), skill_style),
            Spacer(1, 3),
            ProgressBar(skill.score, palette.for_tier(skill.tier), palette.background, width=210),
            Spacer(1, 15),
        ]
    right: list[Flowable] = [
        SectionHeader(labels.total_score, palette.green_dark, width=200, height=25),
        Indenter(10, 0),
        SemiCircleGauge(result.overall, palette.for_tier(result.tier), palette.background),
        Spacer(1, 2),
        Indenter(-10, 0),
        SectionHeader(labels.status, palette.green_dark, width=200, height=20),
        Paragraph(_status_text(config, result.tier), status_style),
    ]
    elements += [
        Table(
            [[left, right]],
            colWidths=[270, 230],
            style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (1, 0), (1, 0), 20)],
        ),
        Spacer(1, 10),
    ]

    conclusion = _conclusion_text(config, result.tier)
    if conclusion:
        elements.append(Paragraph(conclusion + _doubt_text(config), justified))
    return elements


def render_report(report: ReportInput, config: AppConfig) -> bytes:
    palette = _Palette(config)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=SIDE_MARGIN,
        rightMargin=SIDE_MARGIN,
        topMargin=100,
        bottomMargin=70,
        title=f"{config.texts.subtitle} - {report.student_name}",
        author=config.texts.title,
    )

    def decorate(canv: Canvas, _doc: BaseDocTemplate) -> None:
        _draw_header(canv, config, palette)
        _draw_footer(canv, config, palette)

    doc.build(_body(report, config, palette), onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()


# -- File naming / bundling ---------------------------------------------------


def report_filename(student_name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", student_name).strip(" .")
    return f"{cleaned or 'informe'}.pdf"


def render_zip(reports: Iterable[ReportInput], config: AppConfig) -> bytes:
    buffer = io.BytesIO()
    used: set[str] = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for report in reports:
            name = report_filename(report.student_name)
            stem, n = name[:-4], 2
            while name.lower() in used:  # two students with the same name
                name, n = f"{stem} ({n}).pdf", n + 1
            used.add(name.lower())
            zf.writestr(name, render_report(report, config))
    return buffer.getvalue()
