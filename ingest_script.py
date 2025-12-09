import requests
import time
import sys


def ingest():
    url = "http://localhost:8000/ingest"
    health_url = "http://localhost:8000/health"

    print("Waiting for backend to start...")
    # Wait up to 20 minutes (120 * 10s)
    max_retries = 120

    for i in range(max_retries):
        try:
            # Check health first
            requests.get(health_url, timeout=5)

            # If healthy, trigger ingest
            print(f"\nBackend is ready! Triggering ingestion...")
            response = requests.post(url, timeout=30)
            if response.status_code == 200:
                print("Ingestion triggered successfully!")
                print("Response:", response.json())
                return
            else:
                print(
                    f"Failed to trigger ingestion. Status code: {response.status_code}"
                )
                print("Response:", response.text)
                return
        except requests.exceptions.ConnectionError:
            sys.stdout.write(".")
            sys.stdout.flush()
        except Exception as e:
            print(f"\nError connecting: {e}")

        time.sleep(10)

    print("\nTimeout: Backend did not start within 20 minutes.")


if __name__ == "__main__":
    ingest()
