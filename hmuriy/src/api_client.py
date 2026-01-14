import requests
import json

class GnubgClient:
    def __init__(self, api_url):
        self.base_url = api_url.rstrip('/')
        self.session = requests.Session()

    def _post(self, endpoint, payload):
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(url, json=payload, timeout=25.0)
            
            if response.status_code == 422:
                print(f"🔥 [VALIDATION ERROR] {url}")
                try:
                    print(json.dumps(response.json(), indent=2))
                except:
                    print(response.text)

            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"🔥 [API ERROR] {url}: {e}")
            return None

    def get_optimal_move(self, board_data, match_data, dice):
        print('zaprosili optimal move!')
        payload = {
            "board": board_data,
            "match": match_data,
            "dice": dice,
            "double_offered": False
        }
        print(payload)
        return self._post("/get-optimal-move", payload)

    def get_double_decision(self, board_data, match_data, double_offered=False):
        payload = {
            "board": board_data,
            "match": match_data,
            "dice": [0, 0], 
            "double_offered": double_offered
        }
        return self._post("/get-double-decision", payload)