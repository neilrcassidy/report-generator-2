"""Students list: selection downloads, bulk delete, search/filter and notices."""

import io
import json
import zipfile

from fastapi.testclient import TestClient

HTMX = {"HX-Request": "true"}


def create_student(client: TestClient, name: str, cert: str = "B1") -> int:
    response = client.post(
        "/students", data={"name": name, "certification": cert}, follow_redirects=False
    )
    assert response.status_code == 303
    return int(response.headers["location"].split("?")[0].rsplit("/", 1)[1])


def add_exam(client: TestClient, student_id: int, headers: dict[str, str] | None = None):
    data = {
        "taken_on": "2026-01-10",
        "score:READING": "85",
        "score:WRITING": "90",
        "score:LISTENING": "80",
    }
    return client.post(f"/students/{student_id}/exams", data=data, headers=headers or {})


def test_download_one_selected_gives_pdf(client: TestClient) -> None:
    ana = create_student(client, "Ana López")
    add_exam(client, ana)
    response = client.get("/reports/download", params={"ids": [ana]})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Ana%20L%C3%B3pez.pdf" in response.headers["content-disposition"]


def test_download_several_selected_gives_zip_without_students_lacking_exams(
    client: TestClient,
) -> None:
    ana, luis, eva = (create_student(client, n) for n in ("Ana", "Luis", "Eva"))
    add_exam(client, ana)
    add_exam(client, luis)  # Eva has no exams
    response = client.get("/reports/download", params={"ids": [ana, luis, eva, 999]})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        assert sorted(zf.namelist()) == ["Ana.pdf", "Luis.pdf"]


def test_download_with_one_reportable_student_gives_pdf(client: TestClient) -> None:
    ana, eva = create_student(client, "Ana"), create_student(client, "Eva")
    add_exam(client, ana)
    response = client.get("/reports/download", params={"ids": [ana, eva]})
    assert response.headers["content-type"] == "application/pdf"


def test_download_nothing_reportable_is_409(client: TestClient) -> None:
    eva = create_student(client, "Eva")
    assert client.get("/reports/download").status_code == 409
    assert client.get("/reports/download", params={"ids": [eva]}).status_code == 409


def test_bulk_delete_removes_only_selected(client: TestClient) -> None:
    ana, luis, eva = (create_student(client, n) for n in ("Ana", "Luis", "Eva"))
    add_exam(client, ana)
    response = client.post("/students/delete", data={"ids": [ana, eva]}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/students?notice=students_deleted&n=2"
    assert client.get(f"/students/{ana}").status_code == 404
    assert client.get(f"/students/{eva}").status_code == 404
    assert client.get(f"/students/{luis}").status_code == 200


def test_bulk_delete_with_nothing_selected_deletes_nothing(client: TestClient) -> None:
    ana = create_student(client, "Ana")
    response = client.post("/students/delete", follow_redirects=False)
    assert response.headers["location"] == "/students?notice=students_deleted&n=0"
    assert client.get(f"/students/{ana}").status_code == 200


def test_list_renders_selection_controls(client: TestClient) -> None:
    ana = create_student(client, "Ana")
    add_exam(client, ana)
    create_student(client, "Eva")
    html = client.get("/students").text
    assert "data-select-all" in html
    assert html.count('name="ids"') == 2
    assert 'data-has-result="true"' in html
    assert 'data-has-result="false"' in html
    assert 'formaction="/reports/download"' in html
    assert 'formaction="/students/delete"' in html
    assert 'data-label-many="Descargar {n} informes (ZIP)"' in html
    assert 'src="/assets/logo.png"' in html


def test_search_ignores_accents_and_case(client: TestClient) -> None:
    create_student(client, "Ana López")
    create_student(client, "Luis Martín")
    html = client.get("/students", params={"q": "LOPEZ"}).text
    assert "Ana López" in html
    assert "Luis Martín" not in html


def test_certification_filter(client: TestClient) -> None:
    create_student(client, "Ana", "B1")
    create_student(client, "Bea", "C1")
    html = client.get("/students", params={"cert": "C1"}).text
    assert "Bea" in html
    assert ">Ana<" not in html


def test_htmx_search_returns_rows_partial_and_no_match_state(client: TestClient) -> None:
    create_student(client, "Ana")
    partial = client.get("/students", params={"q": "zzz"}, headers=HTMX).text
    assert "<html" not in partial
    assert "Sin resultados" in partial


def test_list_is_sorted_ignoring_accents(client: TestClient) -> None:
    for name in ("Zoe", "Álvaro", "bruno"):
        create_student(client, name)
    html = client.get("/students").text
    assert html.index("Álvaro") < html.index("bruno") < html.index("Zoe")


def test_redirect_notices(client: TestClient) -> None:
    response = client.post(
        "/students", data={"name": "Ana", "certification": "B1"}, follow_redirects=False
    )
    assert response.headers["location"].endswith("?notice=student_created")
    student_id = response.headers["location"].split("?")[0].rsplit("/", 1)[1]
    response = client.post(f"/students/{student_id}/delete", follow_redirects=False)
    assert response.headers["location"] == "/students?notice=student_deleted"


def test_htmx_exam_changes_trigger_notice(client: TestClient) -> None:
    ana = create_student(client, "Ana")
    response = add_exam(client, ana, HTMX)
    assert json.loads(response.headers["HX-Trigger"]) == {"notice": {"code": "exam_added"}}
    exam_id = response.text.split(f'action="/students/{ana}/exams/')[1].split("/")[0]
    response = client.post(f"/students/{ana}/exams/{exam_id}/delete", headers=HTMX)
    assert json.loads(response.headers["HX-Trigger"]) == {"notice": {"code": "exam_deleted"}}


def test_notice_texts_live_in_template(client: TestClient) -> None:
    html = client.get("/students").text
    for code in ("student_created", "students_deleted", "exam_added", "exam_deleted"):
        assert f'data-code="{code}"' in html


def test_static_assets_served(client: TestClient) -> None:
    for path in (
        "/assets/logo.png",
        "/static/icons.svg",
        "/static/js/selection.js",
        "/static/js/confirm.js",
        "/static/js/toast.js",
    ):
        assert client.get(path).status_code == 200, path
