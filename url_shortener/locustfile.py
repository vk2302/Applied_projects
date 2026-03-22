import random
import string

from locust import HttpUser, task, between


def random_alias(length=8):
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


class URLShortenerUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def create_short_link(self):
        self.client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/load-test-page"
            },
        )

    @task(2)
    def create_custom_short_link(self):
        self.client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com/load-test-custom",
                "custom_alias": random_alias(),
            },
        )

    @task(1)
    def healthcheck(self):
        self.client.get("/health")
