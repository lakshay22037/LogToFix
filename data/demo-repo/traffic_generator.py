import random
import threading
import time

import requests

BASE_URL = "http://localhost:5001"


def hit_orders():
    order_id = random.choice(["1", "2", "3", "99", "1' OR '1'='1", "abc"])
    requests.get(f"{BASE_URL}/orders/{order_id}")


def hit_users():
    body = random.choice([
        {"email": "user@example.com"},
        {"name": "no email field"},
        {},
    ])
    requests.post(f"{BASE_URL}/users", json=body)


def hit_items():
    page = random.choice([0, 1, 2, 3, 50])
    requests.get(f"{BASE_URL}/items/page/{page}")


def hit_counter_concurrently():
    def bump():
        requests.post(f"{BASE_URL}/counter/increment")

    threads = [threading.Thread(target=bump) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    requests.get(f"{BASE_URL}/counter/check", params={"expected": 20})


def hit_reports():
    requests.get(f"{BASE_URL}/reports/summary")


ACTIONS = [hit_orders, hit_users, hit_items, hit_counter_concurrently, hit_reports]


def main():
    print(f"Generating traffic against {BASE_URL} — Ctrl+C to stop")
    while True:
        action = random.choice(ACTIONS)
        try:
            action()
        except requests.exceptions.ConnectionError:
            print("Demo app not reachable yet, retrying...")
        time.sleep(random.uniform(0.5, 2.0))


if __name__ == "__main__":
    main()
