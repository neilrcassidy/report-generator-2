from fastapi.testclient import TestClient

HTMX = {"HX-Request": "true"}


def create_student(client: TestClient, name: str = "Ana López", cert: str = "B1") -> str:
    response = client.post(
        "/students", data={"name": name, "certification": cert}, follow_redirects=False
    )
    assert response.status_code == 303
    return response.headers["location"].split("?")[0]  # drop the ?notice=... toast code


def b1_exam(taken_on: str, reading: str, writing: str, listening: str) -> dict[str, str]:
    return {
        "taken_on": taken_on,
        "score:READING": reading,
        "score:WRITING": writing,
        "score:LISTENING": listening,
    }


def test_index_redirects_to_student_list(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/students"


def test_empty_list(client: TestClient) -> None:
    response = client.get("/students")
    assert response.status_code == 200
    assert "Todavía no hay alumnos" in response.text


def test_create_student_and_show_detail(client: TestClient) -> None:
    url = create_student(client)
    page = client.get(url)
    assert page.status_code == 200
    assert "Ana López" in page.text
    assert 'name="score:LISTENING"' in page.text
    assert 'name="score:USE OF ENGLISH"' not in page.text  # B1 has no Use of English


def test_b2_student_gets_use_of_english_field(client: TestClient) -> None:
    page = client.get(create_student(client, cert="B2"))
    assert 'name="score:USE OF ENGLISH"' in page.text


def test_create_student_validation_errors(client: TestClient) -> None:
    response = client.post("/students", data={"name": "   ", "certification": "Z9"})
    assert response.status_code == 422
    assert "Este campo es obligatorio." in response.text
    assert "Todavía no hay alumnos" in client.get("/students").text


def test_add_exams_computes_result(client: TestClient) -> None:
    url = create_student(client)
    client.post(f"{url}/exams", data=b1_exam("2026-01-10", "79", "80", "79.5"))
    response = client.post(f"{url}/exams", data=b1_exam("2026-02-10", "80", "79", "79.5"))
    assert response.status_code == 200  # followed redirect
    assert "80 %" in response.text
    assert "APTO/A" in response.text
    assert "Exámenes (2)" in response.text

    listing = client.get("/students").text
    assert "Ana López" in listing
    assert "80 %" in listing


def test_htmx_exam_post_returns_partial(client: TestClient) -> None:
    url = create_student(client)
    response = client.post(
        f"{url}/exams", data=b1_exam("2026-01-10", "50", "60", "40"), headers=HTMX
    )
    assert response.status_code == 200
    assert response.text.lstrip().startswith('<section id="exams"')
    assert "<html" not in response.text
    assert "NO APTO/A" in response.text


def test_invalid_exam_shows_errors(client: TestClient) -> None:
    url = create_student(client)
    bad = b1_exam("", "101", "abc", "")
    full = client.post(url + "/exams", data=bad)
    assert full.status_code == 422
    assert "Este campo es obligatorio." in full.text

    partial = client.post(
        url + "/exams", data=b1_exam("2026-01-10", "101", "abc", "50"), headers=HTMX
    )
    assert partial.status_code == 200
    assert "Introduce un valor entre 0 y 100." in partial.text
    assert "Valor no válido." in partial.text
    assert "Exámenes (0)" in partial.text


def test_delete_exam_and_student(client: TestClient) -> None:
    url = create_student(client)
    client.post(f"{url}/exams", data=b1_exam("2026-01-10", "50", "60", "40"))
    student_id = url.rsplit("/", 1)[1]
    page = client.get(url).text
    exam_path = page.split(f'action="/students/{student_id}/exams/')[1].split('"')[0]

    response = client.post(f"{url}/exams/{exam_path}", headers=HTMX)
    assert "Exámenes (0)" in response.text

    response = client.post(f"{url}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert client.get(url).status_code == 404


def test_unknown_student_is_404(client: TestClient) -> None:
    assert client.get("/students/999").status_code == 404
    assert client.post("/students/999/exams", data={}).status_code == 404


def test_download_single_report(client: TestClient) -> None:
    url = create_student(client, name="Ana López")
    assert client.get(f"{url}/report.pdf").status_code == 409  # no exams yet

    client.post(f"{url}/exams", data=b1_exam("2026-01-10", "85", "90", "80"))
    response = client.get(f"{url}/report.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "filename*=UTF-8''Ana%20L%C3%B3pez.pdf" in disposition
    assert response.content.startswith(b"%PDF")
    assert 'href="/students/' in client.get(url).text  # download button shown
