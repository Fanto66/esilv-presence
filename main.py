from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import random
import time
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

SESSION_FILE = "session.json"


def human_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))


def login(page):
    print("🔐 Performing login...")

    page.goto("https://my.devinci.fr/")

    page.type("#login", EMAIL, delay=random.randint(50, 150))
    human_delay()
    page.click("#btn_next")

    page.wait_for_url("**adfs.devinci.fr**")

    page.type("#passwordInput", PASSWORD, delay=random.randint(70, 180))
    human_delay()
    page.click("#submitButton")

    page.wait_for_url("https://my.devinci.fr/**")

    print("✅ Logged in")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        # 👇 Load session if it exists
        if os.path.exists(SESSION_FILE):
            print("📂 Using saved session")
            context = browser.new_context(storage_state=SESSION_FILE)
        else:
            print("🆕 No session found, creating new one")
            context = browser.new_context()

        page = context.new_page()

        # 👇 Check if already logged in
        page.goto("https://my.devinci.fr/")
        human_delay()

        if "login" in page.url or page.locator("#login").count() > 0:
            login(page)

            # 👇 Save session after login
            context.storage_state(path=SESSION_FILE)
            print("💾 Session saved")

        else:
            print("✅ Already logged in")

        # 6. Go to attendance page
        human_delay()
        page.goto("https://my.devinci.fr/student/presences/")

        page.wait_for_selector("#body_presences")

        # 7. Find the current class
        current_class = page.query_selector("tr.warning")

        if current_class:
            print("⚠️ Current class found")

            button = current_class.query_selector("td:nth-child(4) a")

            if button:
                raw_link = button.get_attribute("href")
                link = urljoin(page.url, raw_link)

                print("Attendance link:", link)
                human_delay()
                page.goto(link)

                print("Navigated to attendance page")

            else:
                print("No attendance button found")
        else:
            print("No current class")

        time.sleep(10)

        browser.close()


if __name__ == "__main__":
    main()
