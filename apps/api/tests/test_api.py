from datetime import date

from tests.conftest import PROFILE


def test_requires_login(client):
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/log/2026-01-01").status_code == 401


def test_register_login_logout(client):
    r = client.post("/api/auth/register", json={"email": "A@Example.com", "password": "password123"})
    assert r.status_code == 201 and r.json()["email"] == "a@example.com"
    assert client.post("/api/auth/register", json={"email": "a@example.com", "password": "password123"}).status_code == 409
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-pass"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200 and r.json()["has_profile"] is False


def test_profile_and_targets(user_client):
    r = user_client.get("/api/profile")
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["allergies"] == ["peanut"]  # normalised
    assert body["targets"]["recommended_calories"] > 1200


def test_profile_rejects_children(user_client):
    assert user_client.put("/api/profile", json=PROFILE | {"age": 10}).status_code == 422


def test_food_search_and_log(user_client, foods):
    r = user_client.get("/api/foods/search", params={"q": "egg"})
    assert r.status_code == 200 and r.json()[0]["name"].startswith("Egg")
    egg = foods["egg"]
    r = user_client.post("/api/log", json={"food_id": egg, "grams": 100, "meal": "breakfast"})
    assert r.status_code == 201 and r.json()["kcal"] == 143
    r = user_client.post("/api/log/batch", json={"meal": "lunch", "items": [{"food_id": foods["bread"], "grams": 50}]})
    assert r.status_code == 201
    day = user_client.get(f"/api/log/{date.today()}").json()
    assert len(day["entries"]) == 2
    assert day["totals"]["kcal"] == 143 + 126
    entry_id = day["entries"][0]["id"]
    assert user_client.delete(f"/api/log/{entry_id}").status_code == 204
    assert len(user_client.get(f"/api/log/{date.today()}").json()["entries"]) == 1
    assert [f["id"] for f in user_client.get("/api/foods/recent").json()] == [foods["bread"]]


def test_cannot_delete_other_users_entries(user_client, client, foods):
    entry = user_client.post("/api/log", json={"food_id": foods["egg"], "grams": 50, "meal": "snack"}).json()
    user_client.post("/api/auth/logout")
    client.post("/api/auth/register", json={"email": "other@example.com", "password": "password123"})
    assert client.delete(f"/api/log/{entry['id']}").status_code == 404


def test_weight_updates_progress(user_client):
    r = user_client.post("/api/progress/weight", json={"weight_kg": 61.5})
    assert r.status_code == 200
    assert r.json()["weights"][-1]["weight_kg"] == 61.5
    assert user_client.get("/api/profile").json()["profile"]["weight_kg"] == 61.5


def test_export_and_delete_account(user_client, foods):
    user_client.post("/api/log", json={"food_id": foods["egg"], "grams": 50, "meal": "snack"})
    data = user_client.get("/api/profile/export").json()
    assert data["user"]["email"] == "sam@example.com" and len(data["meals"]) == 1
    assert user_client.delete("/api/profile/account").status_code == 204
    assert user_client.get("/api/auth/me").status_code == 401
    assert user_client.post("/api/auth/login", json={"email": "sam@example.com", "password": "password123"}).status_code == 401


def test_device_account(client):
    r = client.post("/api/auth/device")
    assert r.status_code == 201
    assert r.json()["email"] == "" and r.json()["has_profile"] is False
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Max-Age=315360000" in cookie  # ~10 years
    me = client.get("/api/auth/me").json()
    assert me["id"] == r.json()["id"]
    # Device accounts have no usable password.
    from betteru.db import SessionLocal
    from betteru.models import User

    with SessionLocal() as db:
        email = db.get(User, me["id"]).email
    assert client.post("/api/auth/login", json={"email": email, "password": "!"}).status_code in (401, 422)


def test_profile_name_saved(client):
    client.post("/api/auth/device")
    r = client.put("/api/profile", json=PROFILE | {"name": "Nia"})
    assert r.status_code == 200 and r.json()["profile"]["name"] == "Nia"
    assert client.get("/api/auth/me").json()["name"] == "Nia"


def test_week_totals(user_client, foods):
    user_client.post("/api/log", json={"food_id": foods["egg"], "grams": 100, "meal": "breakfast"})
    week = user_client.get("/api/log/week").json()
    assert len(week) == 7 and week[-1]["date"] == date.today().isoformat()
    assert week[-1]["kcal"] == 143 and week[0]["kcal"] == 0
