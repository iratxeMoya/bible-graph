import pytest

from app import search
from tests.data import (
    EPH_2_8,
    EPH_2_9,
    GEN_1_1,
    GEN_1_3,
    JOHN_1_14,
    JOHN_1_16,
    PS_32_1,
    ROM_3_24,
    ROM_8_32,
    TIT_3_5,
    TIT_3_7,
)


def get(client, **params):
    response = client.get("/api/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def ids(body, *, seeds_only=False):
    return {n["id"] for n in body["nodes"] if n["is_seed"] or not seeds_only}


def edge_pairs(body):
    return {(e["source"], e["target"]) for e in body["edges"]}


def test_default_search_returns_seeds_and_direct_neighbors(client):
    body = get(client, q="gracia")
    assert body["query"] == "gracia"
    assert body["total_matches"] == 4
    assert body["truncated"] is False
    assert ids(body, seeds_only=True) == {JOHN_1_14, JOHN_1_16, ROM_3_24, EPH_2_8}
    assert ids(body) == {JOHN_1_14, JOHN_1_16, ROM_3_24, EPH_2_8, GEN_1_1, TIT_3_5, PS_32_1}


def test_node_fields(client):
    body = get(client, q="gracia")
    node = next(n for n in body["nodes"] if n["id"] == ROM_3_24)
    assert node == {
        "id": ROM_3_24,
        "ref": "Romanos 3:24",
        "label": "Ro 3:24",
        "book": "Romanos",
        "testament": "NT",
        "text": "Siendo justificados gratuitamente por su gracia, por la redención que es en Cristo Jesús;",
        "is_seed": True,
        "hop": 0,
    }
    neighbor = next(n for n in body["nodes"] if n["id"] == GEN_1_1)
    assert (neighbor["is_seed"], neighbor["hop"], neighbor["testament"]) == (False, 1, "AT")


def test_seeds_are_ranked_by_occurrences_then_by_incoming_votes(client):
    # Juan 1:16 dice "gracia" dos veces. Después: Juan 1:14 (50 votos entrantes),
    # Efesios 2:8 (40) y Romanos 3:24 (35).
    assert ids(get(client, q="gracia", seeds=1, neighbors=0)) == {JOHN_1_16}
    assert ids(get(client, q="gracia", seeds=2, neighbors=0)) == {JOHN_1_16, JOHN_1_14}
    assert ids(get(client, q="gracia", seeds=3, neighbors=0)) == {JOHN_1_16, JOHN_1_14, EPH_2_8}
    assert get(client, q="gracia", seeds=1, neighbors=0)["total_matches"] == 4


def test_search_ignores_accents_and_case(client):
    assert ids(get(client, q="REDENCION", neighbors=0)) == {ROM_3_24}


def test_search_matches_other_forms_of_the_word(client):
    # "perdón" encuentra "perdonadas" y "perdonó".
    assert ids(get(client, q="perdón", neighbors=0)) == {PS_32_1, ROM_8_32}


def test_neighbors_limits_each_node_to_its_heaviest_connections(client):
    # Romanos 3:24 <-> Efesios 2:8 existe en los dos sentidos y cuenta como un solo vecino.
    assert ids(get(client, q="redención", neighbors=1)) == {ROM_3_24, EPH_2_8}
    assert ids(get(client, q="redención", neighbors=2)) == {ROM_3_24, EPH_2_8, TIT_3_5}


def test_expansion_follows_edges_in_both_directions(client):
    # Génesis 1:1 -> Juan 1:14: desde Juan 1:14 se llega a Génesis 1:1 por la arista entrante.
    body = get(client, q="Verbo")
    assert ids(body) == {JOHN_1_14, GEN_1_1}
    assert edge_pairs(body) == {(GEN_1_1, JOHN_1_14)}


def test_min_weight_filters_nodes_and_edges(client):
    default = get(client, q="plenitud")
    assert ids(default) == {JOHN_1_16}
    assert default["edges"] == []
    with_zero = get(client, q="plenitud", min_weight=0)
    assert ids(with_zero) == {JOHN_1_16, GEN_1_3}
    assert edge_pairs(with_zero) == {(JOHN_1_16, GEN_1_3)}
    heavy = get(client, q="redención", min_weight=30)
    assert ids(heavy) == {ROM_3_24, EPH_2_8, TIT_3_5}
    assert edge_pairs(heavy) == {(ROM_3_24, EPH_2_8), (EPH_2_8, ROM_3_24), (ROM_3_24, TIT_3_5)}


def test_two_hops(client):
    body = get(client, q="redención", hops=2)
    hops = {n["id"]: n["hop"] for n in body["nodes"]}
    assert hops == {
        ROM_3_24: 0,
        EPH_2_8: 1,
        TIT_3_5: 1,
        PS_32_1: 1,
        EPH_2_9: 2,
        ROM_8_32: 2,
    }


def test_edges_between_neighbors_are_included(client):
    body = get(client, q="redención")
    assert (EPH_2_8, TIT_3_5) in edge_pairs(body)
    assert edge_pairs(body) == {
        (ROM_3_24, EPH_2_8),
        (EPH_2_8, ROM_3_24),
        (ROM_3_24, TIT_3_5),
        (EPH_2_8, TIT_3_5),
        (ROM_3_24, PS_32_1),
    }


def test_edge_fields_for_single_verse_and_range_targets(client):
    edges = {(e["source"], e["target"]): e for e in get(client, q="redención")["edges"]}
    assert edges[(ROM_3_24, EPH_2_8)] == {
        "source": ROM_3_24,
        "target": EPH_2_8,
        "weight": 40,
        "target_end_id": None,
        "target_label": "Ef 2:8",
    }
    assert edges[(ROM_3_24, TIT_3_5)]["target_end_id"] == TIT_3_7
    assert edges[(ROM_3_24, TIT_3_5)]["target_label"] == "Tit 3:5-7"


@pytest.mark.parametrize("q", ["xyzzy", "de la", "((("])
def test_no_matches_returns_an_empty_graph(client, q):
    assert get(client, q=q) == {
        "query": q,
        "total_matches": 0,
        "truncated": False,
        "nodes": [],
        "edges": [],
    }


def test_truncation_keeps_the_lowest_hops(client, monkeypatch):
    monkeypatch.setattr(search, "MAX_NODES", 3)
    body = get(client, q="gracia")
    assert body["truncated"] is True
    assert len(body["nodes"]) == 3
    assert all(n["is_seed"] for n in body["nodes"])
    node_ids = ids(body)
    assert all(s in node_ids and t in node_ids for s, t in edge_pairs(body))


def test_query_is_trimmed(client):
    assert get(client, q="  redención  ")["query"] == "redención"


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": "a"},
        {"q": "   "},
        {"q": " a "},
        {"q": "x" * 101},
        {"q": "gra\x00cia"},
        {"q": "gracia", "seeds": 0},
        {"q": "gracia", "seeds": 101},
        {"q": "gracia", "neighbors": -1},
        {"q": "gracia", "neighbors": 21},
        {"q": "gracia", "min_weight": -1},
        {"q": "gracia", "hops": 0},
        {"q": "gracia", "hops": 3},
        {"q": "gracia", "seeds": "muchas"},
    ],
)
def test_invalid_parameters_are_rejected(client, params):
    assert client.get("/api/search", params=params).status_code == 422


def test_search_operators_and_quotes_do_not_break_the_query(client):
    assert ids(get(client, q='"gracia por gracia"', neighbors=0)) == {JOHN_1_16}
    assert get(client, q="'; DROP TABLE edges; --")["nodes"] == []
    assert get(client, q="gracia")["total_matches"] == 4
