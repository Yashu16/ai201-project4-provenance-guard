import requests

TEXT = """
Artificial intelligence represents a transformative paradigm shift in modern society. 
It is important to note that while the benefits of AI are numerous, it is equally 
essential to consider the ethical implications. Furthermore, stakeholders across 
various sectors must collaborate to ensure responsible deployment.
"""

response = requests.post(
    "http://localhost:5000/api/submit",
    json={"creator_id": "test-user-1", "text": TEXT.strip()}
)

data = response.json()
print(f"submission_id      : {data['submission_id']}")
print(f"attribution        : {data['attribution']}")
print(f"confidence         : {data['confidence']}")
print(f"label              : {data['label']}")

# Pull signal breakdown from audit log
log = requests.get("http://localhost:5000/api/log").json()
entry = next((e for e in reversed(log["entries"]) if e["submission_id"] == data["submission_id"]), None)
if entry:
    print(f"llm_score          : {entry['llm_score']}")
    print(f"stylometric_score  : {entry['stylometric_score']}")
