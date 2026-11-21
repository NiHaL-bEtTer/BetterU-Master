"""USDA branded-food fallback (API mocked)."""

import pytest

import betteru.services.branded as branded
from betteru.config import get_settings

CLIF = {
    "fdcId": 2586177,
    "description": "CHOCOLATE CHIP ENERGY BAR, CHOCOLATE CHIP ENERGY BAR",
    "brandName": "CLIF BAR",
    "gtinUpc": "00722252100900",
    "foodCategory": "Snack, Energy & Granola Bars",
    "servingSize": 68.0,
    "servingSizeUnit": "GRM",
    "householdServingFullText": "1 BAR",
    "foodNutrients": [
        {"nutrientId": 1008, "unitName": "KCAL", "value": 368},
        {"nutrientId": 1003, "unitName": "G", "value": 14.7},
        {"nutrientId": 1004, "unitName": "G", "value": 8.82},
        {"nutrientId": 1005, "unitName": "G", "value": 64.7},
    ],
}


@pytest.fixture
def usda(monkeypatch):
    calls = []

    def fake_fetch(params):
        calls.append(params)
        return [CLIF] if ("clif" in params["query"].lower() or params["query"].lstrip("0") == "722252100900") else []

    monkeypatch.setattr(branded, "_fetch", fake_fetch)
    monkeypatch.setattr(get_settings(), "usda_api_key", "test-key")
    return calls


def test_clean_name():
    assert branded._clean_name("CHOCOLATE CHIP BAR, CHOCOLATE CHIP BAR", "CLIF BAR") == "Clif Bar Chocolate Chip Bar"
    assert branded._clean_name("CLIF BAR, BLUEBERRY", "CLIF BAR") == "Clif Bar, Blueberry"


def test_weak_search_fetches_and_caches(user_client, foods, usda):
    r = user_client.get("/api/foods/search", params={"q": "clif bar chocolate chip"}).json()
    top = r[0]
    assert top["name"] == "Clif Bar Chocolate Chip Energy Bar"
    assert top["source"] == "usda_branded" and top["kcal"] == 368
    assert top["portions"] == [{"id": top["portions"][0]["id"], "description": "1 bar", "grams": 68.0}]
    assert len(usda) == 1
    # Second search is served locally — no extra API call.
    user_client.get("/api/foods/search", params={"q": "clif bar chocolate chip"})
    assert len(usda) == 1


def test_strong_local_match_skips_api(user_client, foods, usda):
    user_client.get("/api/foods/search", params={"q": "egg"})
    assert usda == []


def test_no_key_no_call(user_client, foods, usda, monkeypatch):
    monkeypatch.setattr(get_settings(), "usda_api_key", "")
    user_client.get("/api/foods/search", params={"q": "clif bar"})
    assert usda == []


def test_barcode_falls_back_to_usda(user_client, usda, monkeypatch):
    import betteru.clients.external as external

    monkeypatch.setattr(external, "open_food_facts_product", lambda code: None)
    r = user_client.get("/api/foods/barcode/722252100900")
    assert r.status_code == 200 and r.json()["source"] == "usda_branded"
    # Same product with different zero-padding is found locally.
    assert user_client.get("/api/foods/barcode/0722252100900").json()["id"] == r.json()["id"]
