# Mentor Link

A privacy-first senior–junior mentor finder built for students at The National Institute of Engineering (NIE), Mysuru, for ALPHA Lab Recruitment 2026 (Task: TECH-06).

Juniors can browse senior mentor profiles by topic, save mentors, and send short mentorship requests regarding internships, electives, and hackathons. Seniors review incoming requests and selectively accept or decline them.

* **Repository:** https://github.com/shznomani/mentor-link

---

## Student Discovery (NIE Mysuru)
Before building, user research was conducted with NIE students to ground the solution in real campus friction:

* **1st-year CSE student:** *"Honestly, the hesitation of bothering them out of the blue without knowing if they are busy, have exams, or are even open to answering doubts."*
* **1st-year CSE student, on senior profiles:** *"CGPA."*
* **3rd-year senior:** *"I'd selectively choose the requests which are aligning with the task I'd be doing to answer and ignore the rest during that time."*

---

## Privacy-First Architecture (Special Requirement)
No phone numbers or personal email addresses are ever shown publicly.

* **Server-side enforcement:** Privacy filtering is enforced in Flask (`backend/app.py`), not merely hidden in CSS or client-side state.
* **Pending & declined state:** Both the junior's and senior's contact email IDs are withheld from API responses while a request is pending or declined.
* **Accepted state:** Only when a senior explicitly accepts does the backend unlock both emails.
* **Persistent storage:** State persists in SQLite across page refreshes, and a reset endpoint restores the initial demo state cleanly.
* **Automated test suite:** `backend/test_privacy.py` includes 12 automated unit tests validating server-side privacy masking and request lifecycles.

---

## Tech Stack
* **Frontend:** React, Vite (port `5173`)
* **Backend:** Python, Flask, Gunicorn (port `5000`)
* **Database:** SQLite
* **Testing:** Pytest (`12 passed`)

---

## Local Setup

### 1. Backend & Tests
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 app.py