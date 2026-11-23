# Mentor Link

A frontend prototype for finding peer mentors at NIE Mysuru. Juniors can browse mentor profiles, search by name or topic, save mentors, and send a short request. Requests remain pending until the mentor accepts. Contact details appear only after acceptance.

## Run locally

Requires Node.js and npm. From this folder:

```bash
npm install
npm run dev
```

Dependencies are installed in this workspace. The app is currently running locally at `http://127.0.0.1:5173/`.

## Try the prototype

1. In **Find a mentor**, search or choose a topic, then open a mentor card.
2. Send a request. It appears under **My requests** as pending; contact is not shown.
3. Use the **Junior demo / Mentor demo** switch to open the mentor inbox and accept or decline the request.
4. Switch back to Junior demo. After acceptance, the request shows a demo contact. The sample contact is generated for demonstration and is not a real person's contact information.

Requests and saved mentors persist in this browser using `localStorage`. The mentor profiles are illustrative sample data, not verified NIE student profiles or interview findings.

## User research provided by the team

Interview evidence is recorded by role only, with permission:

- **1st-year CSE student:** “Honestly, the hesitation of bothering them out of the blue without knowing if they are busy, have exams, or are even open to answering doubts.”
- **1st-year CSE student:** “CGPA.” (What they want to see on a senior's profile.)
- **3rd-year senior:** “I'd selectively choose the requests which are aligning with the task I'd be doing to answer and ignore the rest during that time.”

These findings inform the Connect page: mentors show whether they are open or at capacity; juniors can filter by interests or search for a skill; requests include a topic so mentors can decide whether it fits what they can help with. CGPA is shown as an optional, mentor-shared profile detail. The displayed CGPA values are labeled demo values and must be replaced with consented profile data before any real deployment.

## Privacy behavior

No contact detail is displayed on public mentor cards. The request state is `pending`, `accepted`, or `declined`; the demo reveals a contact placeholder only in the junior's accepted request. The production version should enforce the same rule in the Flask API and database, since frontend-only hiding is not a security boundary.

## Suggested authentication for the Flask + SQLite version

Use campus email verification if NIE provides a reliable student email domain or verification process. Store a password hash (Argon2id or bcrypt), never the password, use Flask's signed server-side session cookie with `HttpOnly`, `Secure`, and `SameSite=Lax`, and authorize every request by the signed-in user's ID and role. Keep contact information out of public mentor API responses; return it only after checking an accepted mentor-mentee relationship on the server. Add rate limits to login and request creation. For a short prototype without verified campus identity, use a named demo profile or one-time code sent to email, and label it clearly as a demo.

## Stack

- React, JavaScript, HTML, CSS, and Vite for the frontend
- Planned backend: Python + Flask
- Planned database: SQLite
- `lucide-react` icons; Google Fonts are loaded remotely

The Flask API and SQLite persistence are not implemented in this frontend-first prototype. AI/tool use should be disclosed by the team in its final submission.
