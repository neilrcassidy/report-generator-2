import io
import zipfile

import pytest
from pypdf import PdfReader

from report_generator.config import AppConfig, load_config
from report_generator.domain.scoring import SkillResult, StudentResult, Tier
from report_generator.pdf.report import ReportInput, render_report, render_zip, report_filename
from report_generator.settings import PROJECT_ROOT


@pytest.fixture(scope="module")
def config() -> AppConfig:
    return load_config(PROJECT_ROOT / "config" / "config.json")


def make_report(
    tier: Tier = Tier.PASS, overall: int = 85, name: str = "Ana López & Co", cert: str = "B1"
) -> ReportInput:
    skills = [
        SkillResult("READING", 90, Tier.PASS),
        SkillResult("WRITING", 79, Tier.AVERAGE),
        SkillResult("LISTENING", 60, Tier.FAIL),
    ]
    return ReportInput(name, cert, StudentResult(4, skills, overall, tier))


def pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() for page in reader.pages)


def test_renders_single_page_pdf_with_student_data(config: AppConfig) -> None:
    data = render_report(make_report(), config)
    assert data.startswith(b"%PDF")
    assert len(PdfReader(io.BytesIO(data)).pages) == 1
    text = pdf_text(data)
    # Name with "&" must be escaped for ReportLab markup, not crash or vanish.
    assert "Ana López & Co" in text
    for expected in ["B1", "READING", "WRITING", "LISTENING", "90 %", "79 %", "60 %", "85 %"]:
        assert expected in text


def test_labels_come_from_config(config: AppConfig) -> None:
    text = pdf_text(render_report(make_report(), config))
    labels = config.texts.labels
    for label in [labels.student, labels.exams_done, labels.total_score, labels.status]:
        assert label in text


def test_intro_uses_group_pass_threshold(config: AppConfig) -> None:
    b1 = pdf_text(render_report(make_report(cert="B1"), config))
    b2 = pdf_text(render_report(make_report(cert="B2"), config))
    assert "80%" in b1.replace("\n", "")
    assert "70%" in b2.replace("\n", "")


@pytest.mark.parametrize(
    ("tier", "phrase"),
    [
        (Tier.PASS, "supera el nivel mínimo"),
        (Tier.AVERAGE, "margen muy ajustado"),
        (Tier.FAIL, "todavía no alcanza el nivel mínimo"),
    ],
)
def test_conclusion_matches_tier(config: AppConfig, tier: Tier, phrase: str) -> None:
    text = " ".join(pdf_text(render_report(make_report(tier=tier), config)).split())
    assert phrase in text


def test_footer_and_doubt_text_include_contacts(config: AppConfig) -> None:
    text = pdf_text(render_report(make_report(), config))
    assert config.contacts.email in text
    assert config.contacts.website in text
    assert "+34 639 209 234" in text


def test_report_filename_strips_unsafe_characters() -> None:
    assert report_filename('Ana: "López"/B1?') == "Ana LópezB1.pdf"
    assert report_filename("..") == "informe.pdf"


def test_zip_contains_one_pdf_per_student_with_unique_names(config: AppConfig) -> None:
    reports = [make_report(name="Ana"), make_report(name="Ana"), make_report(name="Luis")]
    with zipfile.ZipFile(io.BytesIO(render_zip(reports, config))) as zf:
        names = zf.namelist()
        assert names == ["Ana.pdf", "Ana (2).pdf", "Luis.pdf"]
        assert all(zf.read(n).startswith(b"%PDF") for n in names)
