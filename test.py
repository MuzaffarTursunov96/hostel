# import requests

# URL = "https://hmsuz.com/api/auth/login"

# payload = {
#     "username": "admin",
#     "password": "admin123"
# }

# headers = {
#     "Content-Type": "application/json"
# }

# response = requests.post(URL, json=payload, headers=headers)

# print("Status:", response.status_code)
# print("Response:", response.text)

# import requests

# TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo3OCwiaXNfYWRtaW4iOnRydWUsImJyYW5jaF9pZCI6NiwibGFuZ3VhZ2UiOiJydSIsInRlbGVncmFtX2lkIjoxMzQzODQyNTM1LCJleHAiOjE3NjkwMjcyNzB9.bEB5T_LOBoe7wbpPMG0OWaclG9fV93RzA7Il9l72Duo"

# resp = requests.get(
#     "https://hmsuz.com/api/branches/",
#     headers={
#         "Authorization": f"Bearer {TOKEN}"
#     },
#     timeout=20
# )

# print("Status:", resp.status_code)
# print("Response:", resp.text)

import websocket

ws = websocket.WebSocket()
ws.connect("wss://hmsuz.com/ws/")
print("CONNECTED")
print(ws.recv())
