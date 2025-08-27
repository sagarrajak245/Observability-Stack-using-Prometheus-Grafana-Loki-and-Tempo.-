from locust import HttpUser, task, between
import random

class APIUser(HttpUser):
    wait_time = between(1, 3)
    token = None
    email = f"user{random.randint(1, 10000)}@example.com"
    password = "password123"

    def on_start(self):
        """On start, signup and login to get a token."""
        # Signup
        self.client.post("/signup/", json={"email": self.email, "password": self.password})
        
        # Login
        response = self.client.post("/login/", json={"email": self.email, "password": self.password})
        if response.status_code == 200:
            self.token = response.json()["access_token"]  

    @task
    def get_root(self):
        self.client.get("/")

    @task
    def get_user_profile(self):
        if self.token:
            self.client.get("/users/me/", headers={"Authorization": f"Bearer {self.token}"})
