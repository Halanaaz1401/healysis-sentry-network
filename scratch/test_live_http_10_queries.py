import json
import urllib.request
import time

base = 'http://127.0.0.1:8000/api/v1/advisor/chat'
headers = {
    'Authorization': 'Bearer TEST-TOKEN-UID-ADMIN-99',
    'Content-Type': 'application/json'
}

qs = [
    "What is the stock in West Bengal facilities?",
    "Why is West Bengal at critical risk?",
    "What is the ORS stock in West Bengal?",
    "What is the insulin stock in West Bengal?",
    "Which West Bengal facilities have active alerts?",
    "Which Odisha facilities are at risk?",
    "Compare stock between Behala and Pipli.",
    "Compare insulin between Behala and Pipli.",
    "Which facilities have critical ORS risk?",
    "What should we do about the current stock situation?"
]

print("=== LIVE HTTP TESTING: 10 QUERIES ===")
for i, q in enumerate(qs):
    req = urllib.request.Request(base, data=json.dumps({'message': q}).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"\n==================================================")
        print(f"TEST {i+1}: '{q}'")
        print(f"==================================================")
        print("ANSWER:\n" + data['answer'])
        print("\nSEVERITY: " + data['severity'])
    time.sleep(0.5)

print("\n=== ALL 10 LIVE HTTP TESTS COMPLETED SUCCESSFULLY ===")
