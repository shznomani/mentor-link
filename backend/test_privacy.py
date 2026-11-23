"""
Automated privacy tests for Mentor Link.   Run:  cd backend && python -m pytest -v

Each test uses a fresh temporary database, so tests never affect each other
or the real demo data.

Demo accounts (password for all: demo1234)
  mentors: ananya.rao@, rohan.kulkarni@, ... @demo.mentorlink.test   (ids 1-6)
  juniors: junior.demo@ (id 7), junior.b@ (id 8), junior.c@ (id 9)  @demo.mentorlink.test
"""
import os
import re
import tempfile

# Use a throwaway database when this file imports app.py (it builds a default app on import).
os.environ.setdefault("DB_PATH", os.path.join(tempfile.mkdtemp(), "import-default.db"))

import pytest

from app import DEMO_PASSWORD, create_app

DOMAIN = "@demo.mentorlink.test"
ANANYA = 1            # mentor with a sample pending request from Demo Junior B (junior id 8)
ROHAN = 2
KARTHIK_BUSY = 6
JUNIOR_A = "junior.demo" + DOMAIN
JUNIOR_B = "junior.b" + DOMAIN
JUNIOR_C = "junior.c" + DOMAIN


@pytest.fixture()
def client(tmp_path):
    app = create_app({"DB_PATH": str(tmp_path / "test.db"), "DEMO_MODE": True, "TESTING": True})
    return app.test_client()


def sign_in(client, email):
    res = client.post("/api/login", json={"email": email, "password": DEMO_PASSWORD})
    assert res.status_code == 200, res.get_data(as_text=True)
    return {"Authorization": "Bearer " + res.get_json()["token"]}


def mentor_headers(client, name):
    return sign_in(client, name.lower().replace(" ", ".") + DOMAIN)


def send_request(client, headers, mentor_id=ANANYA, **extra):
    body = {"mentor_id": mentor_id, "topic": "Internships", "message": "Where do I start?"}
    body.update(extra)
    return client.post("/api/requests", json=body, headers=headers)


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def has_email(text):
    return bool(EMAIL_PATTERN.search(text)) or "mentorlink.test" in text


def no_contact_anywhere(res):
    """True if the response has no email address and no 'contact' block at all."""
    text = res.get_data(as_text=True)
    return not has_email(text) and '"contact"' not in text


# --- Case 1: a visitor opens a mentor profile ---------------------------------
def test_visitor_never_sees_mentor_contact(client):
    for url in ["/api/mentors", f"/api/mentors/{ANANYA}"]:
        res = client.get(url)                       # no login at all
        assert res.status_code == 200
        text = res.get_data(as_text=True)
        assert not has_email(text)                  # no email address anywhere
        assert "email" not in text.lower()
        assert "phone" not in text.lower()


def test_visitor_cannot_read_requests(client):
    assert client.get("/api/requests").status_code == 401
    assert client.get("/api/requests/1").status_code == 401


# --- Case 2: a junior sends a request ----------------------------------------
def test_new_request_is_pending_and_hides_contact_from_both(client):
    junior = sign_in(client, JUNIOR_A)
    res = send_request(client, junior)
    assert res.status_code == 201
    assert res.get_json()["status"] == "pending"
    assert no_contact_anywhere(res)

    # The junior's own list: still no contact.
    assert no_contact_anywhere(client.get("/api/requests", headers=junior))

    # The mentor's inbox: sees the request, but no emails and no junior name.
    mentor = mentor_headers(client, "Ananya Rao")
    inbox = client.get("/api/requests", headers=mentor)
    assert no_contact_anywhere(inbox)
    assert "Demo Junior" not in inbox.get_data(as_text=True)
    assert len(inbox.get_json()) == 2               # sample request + this one


# --- Case 3: the mentor declines ----------------------------------------------
def test_declined_request_never_unlocks_contact(client):
    junior = sign_in(client, JUNIOR_A)
    request_id = send_request(client, junior).get_json()["id"]
    mentor = mentor_headers(client, "Ananya Rao")

    res = client.post(f"/api/requests/{request_id}/decision", json={"decision": "decline"}, headers=mentor)
    assert res.status_code == 200 and res.get_json()["status"] == "declined"
    assert no_contact_anywhere(res)
    assert no_contact_anywhere(client.get(f"/api/requests/{request_id}", headers=junior))
    assert no_contact_anywhere(client.get("/api/requests", headers=junior))


# --- Case 4: the mentor accepts -> both emails unlock, for those two people only
def test_accepted_request_unlocks_both_emails_for_both_people(client):
    junior = sign_in(client, JUNIOR_A)
    request_id = send_request(client, junior).get_json()["id"]
    mentor = mentor_headers(client, "Ananya Rao")
    res = client.post(f"/api/requests/{request_id}/decision", json={"decision": "accept"}, headers=mentor)
    assert res.status_code == 200

    for who in (junior, mentor):
        view = client.get(f"/api/requests/{request_id}", headers=who).get_json()
        assert view["status"] == "accepted"
        assert view["contact"]["mentorEmail"] == "ananya.rao" + DOMAIN
        assert view["contact"]["juniorEmail"] == JUNIOR_A


# --- Case 5: other people are denied ------------------------------------------
def test_other_junior_and_other_mentor_are_denied(client):
    junior = sign_in(client, JUNIOR_A)
    request_id = send_request(client, junior).get_json()["id"]
    ananya = mentor_headers(client, "Ananya Rao")
    client.post(f"/api/requests/{request_id}/decision", json={"decision": "accept"}, headers=ananya)

    other_junior = sign_in(client, JUNIOR_C)
    res = client.get(f"/api/requests/{request_id}", headers=other_junior)
    assert res.status_code == 403 and not has_email(res.get_data(as_text=True))
    assert all(r["id"] != request_id for r in client.get("/api/requests", headers=other_junior).get_json())

    other_mentor = mentor_headers(client, "Rohan Kulkarni")
    assert client.get(f"/api/requests/{request_id}", headers=other_mentor).status_code == 403
    assert client.get("/api/requests", headers=other_mentor).get_json() == []

    # An unrelated mentor cannot answer someone else's request either.
    sample_id = client.get("/api/requests", headers=ananya).get_json()[-1]["id"]
    res = client.post(f"/api/requests/{sample_id}/decision", json={"decision": "accept"}, headers=other_mentor)
    assert res.status_code == 403


# --- Swati's bug: refresh must show the real saved state ----------------------
def test_refresh_keeps_real_state_and_reset_restores_demo(client):
    junior = sign_in(client, JUNIOR_A)
    request_id = send_request(client, junior).get_json()["id"]
    mentor = mentor_headers(client, "Ananya Rao")
    client.post(f"/api/requests/{request_id}/decision", json={"decision": "accept"}, headers=mentor)

    # "Refresh" = sign in again from scratch and read the list.
    fresh = sign_in(client, JUNIOR_A)
    mine = client.get("/api/requests", headers=fresh).get_json()
    assert mine[0]["status"] == "accepted" and "contact" in mine[0]

    # A decision is final: it cannot be flipped by a second click.
    again = client.post(f"/api/requests/{request_id}/decision", json={"decision": "decline"}, headers=mentor)
    assert again.status_code == 409

    # Reset brings back the clean demo state: no request for Junior A, sample one still pending.
    assert client.post("/api/demo/reset").status_code == 200
    fresh = sign_in(client, JUNIOR_A)
    assert client.get("/api/requests", headers=fresh).get_json() == []
    inbox = client.get("/api/requests", headers=mentor_headers(client, "Ananya Rao")).get_json()
    assert [r["status"] for r in inbox] == ["pending"]


# --- Other rules ---------------------------------------------------------------
def test_duplicate_busy_and_role_rules(client):
    junior = sign_in(client, JUNIOR_A)
    assert send_request(client, junior).status_code == 201
    assert send_request(client, junior).status_code == 409                      # duplicate
    assert send_request(client, junior, KARTHIK_BUSY).status_code == 409        # mentor at capacity
    mentor = mentor_headers(client, "Rohan Kulkarni")
    assert send_request(client, mentor, ANANYA).status_code == 403              # mentors cannot ask
    assert client.post("/api/requests", json={"mentor_id": 999}, headers=junior).status_code == 404


def test_busy_toggle_blocks_new_requests(client):
    mentor = mentor_headers(client, "Rohan Kulkarni")
    assert client.patch("/api/me/availability", json={"busy": True}, headers=mentor).status_code == 200
    assert send_request(client, sign_in(client, JUNIOR_A), ROHAN).status_code == 409
    client.patch("/api/me/availability", json={"busy": False}, headers=mentor)
    assert send_request(client, sign_in(client, JUNIOR_A), ROHAN).status_code == 201


def test_pending_request_limit(client):
    # Re-open Karthik so there are 6 mentors available; a junior may keep only 5 pending requests.
    karthik = mentor_headers(client, "Karthik M")
    client.patch("/api/me/availability", json={"busy": False}, headers=karthik)
    junior = sign_in(client, JUNIOR_A)
    assert all(send_request(client, junior, m).status_code == 201 for m in (1, 2, 3, 4, 5))
    assert send_request(client, junior, KARTHIK_BUSY).status_code == 429


def test_registration_only_for_college_email(client):
    bad = client.post("/api/register", json={"name": "Test Student", "email": "x@gmail.com", "password": "longenough1"})
    assert bad.status_code == 400
    good = client.post("/api/register", json={"name": "Test Student", "email": "x@nie.ac.in", "password": "longenough1"})
    assert good.status_code == 201 and good.get_json()["user"]["role"] == "junior"
    assert client.post("/api/register", json={"name": "Test Student", "email": "x@nie.ac.in",
                                              "password": "longenough1"}).status_code == 409


def test_demo_endpoints_are_off_when_demo_mode_is_off(tmp_path):
    app = create_app({"DB_PATH": str(tmp_path / "prod.db"), "DEMO_MODE": False, "TESTING": True})
    client = app.test_client()
    assert client.post("/api/demo-login", json={"user_id": 1}).status_code == 404
    assert client.post("/api/demo/reset").status_code == 404
