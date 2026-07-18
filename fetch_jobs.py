#!/usr/bin/env python3
"""
Automata álláskereső – Jooble API alapú, legális állás-aggregátorral.

Kétszer hetente (GitHub Actions cron) lefut:
1. Lekérdezi a Jooble API-t több helyszínre és kulcsszóra.
2. Duplikátumszűri és a docs/jobs.json fájlba menti (ez adja a GitHub Pages weboldal adatát).
3. Email digestet küld az új (előző futás óta megjelent) találatokról.

Szükséges környezeti változók (GitHub Secrets-ben állítva):
  JOOBLE_API_KEY      – Jooble API kulcs (https://jooble.org/api/about)
  GMAIL_USER          – a küldő Gmail cím
  GMAIL_APP_PASSWORD  – Gmail alkalmazásjelszó (nem a normál jelszó!)
  RECIPIENT_EMAIL     – ide megy a digest (lehet ugyanaz, mint GMAIL_USER)
"""

import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# KERESÉSI KRITÉRIUMOK – itt tudod testre szabni
# ---------------------------------------------------------------------------
KEYWORDS = "informatikai vezető, IT infrastruktúra vezető, projektvezető IT, beszerzési előkészítés IT"

LOCATIONS = [
    "Székesfehérvár",
    "Budapest",
    "Győr",
    "Várpalota",
    "Tata",
    "Tatabánya",
    "Veszprém",
]

RADIUS_KM = "26"  # Jooble csak ezeket az értékeket fogadja: 0, 4, 8, 16, 26, 40, 80

# ---------------------------------------------------------------------------
DATA_FILE = Path(__file__).parent / "docs" / "jobs.json"
JOOBLE_API_KEY = os.environ.get("JOOBLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_USER)


DEBUG_LOG = []


def fetch_jobs_for_location(location: str) -> list[dict]:
    """Egy adott helyszínre lekéri a Jooble találatokat."""
    url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
    payload = {"keywords": KEYWORDS, "location": location, "radius": RADIUS_KM}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        entry = {
            "location": location,
            "status_code": resp.status_code,
            "request_payload": payload,
            "response_snippet": resp.text[:1500],
        }
        DEBUG_LOG.append(entry)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
        entry["total_count_reported"] = data.get("totalCount")
        entry["jobs_returned"] = len(jobs)
        for job in jobs:
            job["search_location"] = location
        return jobs
    except requests.RequestException as exc:
        print(f"[HIBA] {location}: {exc}", file=sys.stderr)
        DEBUG_LOG.append({"location": location, "error": str(exc)})
        return []


def dedupe(jobs: list[dict]) -> list[dict]:
    """Link alapján szűri a duplikátumokat (több helyszínen is felbukkanhat ugyanaz)."""
    seen = {}
    for job in jobs:
        link = job.get("link")
        if link and link not in seen:
            seen[link] = job
    return list(seen.values())


def load_previous_links() -> set[str]:
    if not DATA_FILE.exists():
        return set()
    try:
        old = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return {job["link"] for job in old.get("jobs", []) if job.get("link")}
    except (json.JSONDecodeError, KeyError):
        return set()


def send_email_digest(new_jobs: list[dict]) -> None:
    if not (GMAIL_USER and GMAIL_APP_PASSWORD and RECIPIENT_EMAIL):
        print("Email küldés kihagyva: hiányzó GMAIL_USER / GMAIL_APP_PASSWORD / RECIPIENT_EMAIL.")
        return
    if not new_jobs:
        print("Nincs új találat, email nem megy ki.")
        return

    subject = f"{len(new_jobs)} új álláshirdetés – {datetime.now():%Y.%m.%d}"

    lines_html = []
    lines_text = []
    for job in new_jobs:
        title = job.get("title", "Nincs cím")
        company = job.get("company", "")
        loc = job.get("location") or job.get("search_location", "")
        link = job.get("link", "#")
        lines_html.append(
            f'<li><a href="{link}">{title}</a> — {company} ({loc})</li>'
        )
        lines_text.append(f"- {title} — {company} ({loc}): {link}")

    html_body = f"""
    <html><body>
      <h2>{len(new_jobs)} új álláshirdetés</h2>
      <ul>{''.join(lines_html)}</ul>
      <p>Teljes lista a webes felületen is elérhető.</p>
    </body></html>
    """
    text_body = f"{len(new_jobs)} új álláshirdetés:\n\n" + "\n".join(lines_text)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [RECIPIENT_EMAIL], msg.as_string())
    print(f"Email elküldve: {len(new_jobs)} új találat -> {RECIPIENT_EMAIL}")


def main() -> None:
    if not JOOBLE_API_KEY:
        print("HIBA: hiányzik a JOOBLE_API_KEY környezeti változó.", file=sys.stderr)
        sys.exit(1)

    previous_links = load_previous_links()

    all_jobs: list[dict] = []
    for location in LOCATIONS:
        all_jobs.extend(fetch_jobs_for_location(location))

    all_jobs = dedupe(all_jobs)
    all_jobs.sort(key=lambda j: j.get("updated", ""), reverse=True)

    new_jobs = [j for j in all_jobs if j.get("link") not in previous_links]

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(
            {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_count": len(all_jobs),
                "jobs": all_jobs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Mentve: {len(all_jobs)} állás összesen, ebből {len(new_jobs)} új.")

    debug_file = DATA_FILE.parent / "debug.json"
    debug_file.write_text(
        json.dumps(DEBUG_LOG, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    send_email_digest(new_jobs)


if __name__ == "__main__":
    main()
