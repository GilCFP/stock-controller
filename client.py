import requests
response = requests.get(' http://127.0.0.1:5000/table')
if response.status_code == 200:
    message = response.json()
    print(message)
else:
    print(response.status_code)