from fastapi.testclient import TestClient

from src.avito_splitter.api import app


def test_post_split_happy_path() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/split",
            json={
                "itemId": 8001,
                "mcId": 201,
                "mcTitle": "Ремонт квартир и домов под ключ",
                "description": "Делаем ремонт квартир под ключ, а также отдельно выполняем сантехнические и электромонтажные работы.",
            },
        )

    assert response.status_code == 200
    assert response.json()["shouldSplit"] is True
    assert [draft["mcId"] for draft in response.json()["drafts"]] == [101, 102]


def test_post_split_empty_result() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/split",
            json={
                "itemId": 8002,
                "mcId": 201,
                "mcTitle": "Ремонт квартир и домов под ключ",
                "description": "Делаем ремонт под ключ, включая электрику и сантехнику.",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"shouldSplit": False, "drafts": []}


def test_post_split_rejects_invalid_payload() -> None:
    with TestClient(app) as client:
        response = client.post("/split", json={"itemId": "bad"})

    assert response.status_code == 422
