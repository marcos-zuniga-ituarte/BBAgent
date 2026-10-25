import requests


BASE_URL = "http://127.0.0.1:8000"


class UserManager:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = f"{base_url}/auth"

    def _handle_response(self, response: requests.Response) -> dict:
        try:
            data = response.json()
        except ValueError:
            raise Exception(
                f"Respuesta no válida ({response.status_code}): {response.text}"
            )

        if not response.ok:
            detail = data.get("detail", data)
            raise Exception(f"Error {response.status_code}: {detail}")

        return data

    def create_user(self, login: str, password: str) -> str:
        response = requests.post(
            f"{self.base_url}/users",
            json={
                "login": login,
                "password": password,
            },
        )

        data = self._handle_response(response)
        return data["id"]

    def change_password(self, login: str, old_password: str, new_password: str) -> str:
        response = requests.put(
            f"{self.base_url}/users",
            json={
                "login": login,
                "password": old_password,
                "new_password": new_password,
            },
        )

        data = self._handle_response(response)
        return data["id"]

    def delete_user(self, login: str, password: str) -> str:
        response = requests.delete(
            f"{self.base_url}/users",
            json={
                "login": login,
                "password": password,
            },
        )

        data = self._handle_response(response)
        return data["result"]

    def login(self, login: str, password: str) -> str:
        response = requests.post(
            f"{self.base_url}/login",
            json={
                "login": login,
                "password": password,
            },
        )

        data = self._handle_response(response)
        return data["access_token"]

    def logout(self, access_token: str) -> str:
        response = requests.post(
            f"{self.base_url}/logout",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        data = self._handle_response(response)
        return data["result"]
