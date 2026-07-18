import os, json, requests

KEY = os.environ["JOOBLE_API_KEY"]
url = f"https://jooble.org/api/{KEY}"

tests = [
    {"keywords": "IT", "location": "Budapest"},
    {"keywords": "informatikai", "location": "Budapest"},
    {"keywords": "manager", "location": "Budapest"},
    {"keywords": "IT manager", "location": "Budapest, Hungary"},
    {"keywords": "developer", "location": "Budapest, Hungary"},
    {"keywords": "IT", "location": "Budapest, Hungary"},
    {"keywords": "informatikai vezető", "location": ""},
]

results = []
for t in tests:
    r = requests.post(url, json=t, timeout=30)
    results.append({"payload": t, "status": r.status_code, "body": r.text[:300]})

print(json.dumps(results, ensure_ascii=False, indent=2))
