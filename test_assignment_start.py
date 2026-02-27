from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
response = client.post("/assignment/start", json={"email":"pk6304144791@gmail.com","assignment_exam_key":"DCW9UH4J"})
print(response.status_code)
print(response.json() if response.status_code != 500 else response.text)
