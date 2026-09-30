from app import search
from tests.data import ROM_3_24, TIT_3_5, TIT_3_6, TIT_3_7


def test_single_verse(client):
    response = client.get(f"/api/verses/{ROM_3_24}")
    assert response.status_code == 200
    assert response.json() == {
        "ref": "Romanos 3:24",
        "verses": [
            {
                "id": ROM_3_24,
                "ref": "Romanos 3:24",
                "text": "Siendo justificados gratuitamente por su gracia, por la redención que es en Cristo Jesús;",
            }
        ],
    }


def test_range(client):
    response = client.get(f"/api/verses/{TIT_3_5}", params={"end": TIT_3_7})
    assert response.status_code == 200
    body = response.json()
    assert body["ref"] == "Tito 3:5-7"
    assert [v["id"] for v in body["verses"]] == [TIT_3_5, TIT_3_6, TIT_3_7]
    assert [v["ref"] for v in body["verses"]] == ["Tito 3:5", "Tito 3:6", "Tito 3:7"]


def test_end_equal_to_start_is_a_single_verse(client):
    body = client.get(f"/api/verses/{TIT_3_5}", params={"end": TIT_3_5}).json()
    assert body["ref"] == "Tito 3:5"
    assert len(body["verses"]) == 1


def test_range_whose_end_does_not_exist_stops_at_the_last_existing_verse(client):
    body = client.get(f"/api/verses/{TIT_3_5}", params={"end": TIT_3_7 + 5}).json()
    assert body["ref"] == "Tito 3:5-7"


def test_unknown_verse_is_404(client):
    assert client.get("/api/verses/1001002").status_code == 404


def test_range_starting_at_unknown_verse_is_404(client):
    assert client.get("/api/verses/56003004", params={"end": TIT_3_7}).status_code == 404


def test_end_before_start_is_422(client):
    assert client.get(f"/api/verses/{TIT_3_7}", params={"end": TIT_3_5}).status_code == 422


def test_range_longer_than_the_limit_is_422(client, monkeypatch):
    monkeypatch.setattr(search, "MAX_PASSAGE_VERSES", 2)
    assert client.get(f"/api/verses/{TIT_3_5}", params={"end": TIT_3_7}).status_code == 422


def test_non_numeric_or_out_of_range_ids_are_422(client):
    assert client.get("/api/verses/abc").status_code == 422
    assert client.get("/api/verses/0").status_code == 422
    assert client.get("/api/verses/99999999999999999999").status_code == 422
