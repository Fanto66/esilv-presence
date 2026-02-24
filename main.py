from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from datetime import datetime, timedelta
import random
import time
from dotenv import load_dotenv
import os
import requests

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

SESSION_FILE = "session.json"

WEEKDAY_START_TIMES = [
    "08:15",
    "10:00",
    "11:45",
    "13:30",
    "15:15",
    "17:00",
    "18:45",
]

SATURDAY_START_TIMES = [
    "09:00",
    "10:45",
]

CLASS_DURATION = timedelta(minutes=90)
CHECK_START_EARLY_MIN = 5

EARLY_POLL_MIN = 25
EARLY_POLL_MAX = 40

LATE_POLL_MIN = 45
LATE_POLL_MAX = 75

EARLY_ATTENDANCE_WINDOW_MIN = 10

RETRY_SLEEP_MIN = 3
RETRY_SLEEP_MAX = 8


def human_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))


def notify(message: str):
    url = "https://ntfy.sh/esilv_attendance_romain"
    requests.post(url, data=message)


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


def build_schedule_for_date(target_date, start_times):
    schedule = []
    for start_time in start_times:
        start_dt = datetime.strptime(
            f"{target_date} {start_time}", "%Y-%m-%d %H:%M"
        )
        end_dt = start_dt + CLASS_DURATION
        schedule.append((start_dt, end_dt))
    return schedule


def get_start_times_for_date(target_date):
    weekday = target_date.weekday()
    if weekday == 6:
        return None
    if weekday == 5:
        return SATURDAY_START_TIMES
    return WEEKDAY_START_TIMES


def is_logged_out(page):
    if "login" in page.url:
        return True
    return page.locator("#login").count() > 0


def ensure_logged_in(page, context):
    if is_logged_out(page):
        login(page)
        context.storage_state(path=SESSION_FILE)
        print("💾 Session saved")


def safe_goto(page, url, retries=3):
    for attempt in range(retries):
        try:
            page.goto(url)
            return True
        except Exception as exc:
            print(f"⚠️ Navigation error ({attempt + 1}/{retries}): {exc}")
            time.sleep(random.uniform(RETRY_SLEEP_MIN, RETRY_SLEEP_MAX))
    return False


def open_presences_page(page, context):
    if not safe_goto(page, "https://my.devinci.fr/student/presences/"):
        return False
    if is_logged_out(page):
        login(page)
        context.storage_state(path=SESSION_FILE)
        if not safe_goto(page, "https://my.devinci.fr/student/presences/"):
            return False
    page.wait_for_selector("#body_presences")
    return True


def find_class_by_time(page, start_time_str):
    """
    Find a class row by its start time (e.g., "08:15" or "10:00")
    Returns the tr element if found, None otherwise.
    """
    try:
        # Find all table rows in the presences table
        rows = page.query_selector_all("#body_presences tr")
        
        for row in rows:
            # Get the first td which contains the time range
            time_cell = row.query_selector("td:first-child")
            if not time_cell:
                continue
            
            time_text = time_cell.inner_text().strip()
            
            # Check if this row's time matches our target time
            # Format could be "08:15 -09:45" or just "08:15"
            if time_text.startswith(start_time_str):
                return row
        
        return None
    except Exception as exc:
        print(f"⚠️ Error finding class by time: {exc}")
        return None


def get_attendance_link_from_row(row, page_url):
    """
    Extract the attendance link from a class row.
    Returns the full URL or None.
    """
    try:
        # The attendance button is in the 4th td, within an <a> tag
        button = row.query_selector("td:nth-child(4) a")
        if not button:
            return None
        
        raw_link = button.get_attribute("href")
        if not raw_link:
            return None
        
        return urljoin(page_url, raw_link)
    except Exception as exc:
        print(f"⚠️ Error getting attendance link: {exc}")
        return None


def is_attendance_open(page):
    locator = page.locator("span.set-presence")
    if locator.count() == 0:
        return False
    try:
        return locator.is_visible(timeout=0)
    except Exception:
        return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        # Load session if it exists
        if os.path.exists(SESSION_FILE):
            print("📂 Using saved session")
            context = browser.new_context(storage_state=SESSION_FILE)
        else:
            print("🆕 No session found, creating new one")
            context = browser.new_context()

        page = context.new_page()

        # Check if already logged in
        safe_goto(page, "https://my.devinci.fr/")
        human_delay()

        ensure_logged_in(page, context)

        while True:
            today = datetime.now().date()
            start_times = get_start_times_for_date(today)

            if start_times is None:
                print("📅 Sunday: no checks")
                next_day = datetime.combine(today + timedelta(days=1), datetime.min.time())
                sleep_seconds = (next_day - datetime.now()).total_seconds()
                time.sleep(max(0, sleep_seconds))
                continue

            schedule = build_schedule_for_date(today, start_times)

            for start_dt, end_dt in schedule:
                now = datetime.now()
                if now > end_dt:
                    continue

                # Wait until CHECK_START_EARLY_MIN before class starts
                early_start = start_dt - timedelta(minutes=CHECK_START_EARLY_MIN)
                if now < early_start:
                    sleep_seconds = (early_start - now).total_seconds()
                    print(f"⏳ Waiting until {early_start.strftime('%H:%M')} to check for class at {start_dt.strftime('%H:%M')}")
                    time.sleep(max(0, sleep_seconds))

                start_time_str = start_dt.strftime("%H:%M")
                print(f"\n🔍 Looking for class starting at {start_time_str}")

                # Open the presences page and find the class by time
                if not open_presences_page(page, context):
                    print("⚠️ Could not load presences page")
                    continue

                class_row = find_class_by_time(page, start_time_str)
                
                if not class_row:
                    print(f"❌ No class found for time slot {start_time_str}")
                    continue

                print(f"✅ Found class at {start_time_str}")

                # Get the attendance link from this specific row
                attendance_link = get_attendance_link_from_row(class_row, page.url)
                
                if not attendance_link:
                    print("❌ No attendance button found for this class")
                    continue

                print(f"🔗 Attendance link: {attendance_link}")

                # Navigate to the attendance page
                if not safe_goto(page, attendance_link):
                    print("⚠️ Could not navigate to attendance page")
                    continue

                print("📋 On attendance page, polling until it opens...")

                # Poll the attendance page until it opens or class ends
                while datetime.now() < end_dt:
                    # Re-login if needed
                    if is_logged_out(page):
                        print("🔐 Session expired, logging back in...")
                        login(page)
                        context.storage_state(path=SESSION_FILE)
                        safe_goto(page, attendance_link)

                    # Check if attendance is open
                    if is_attendance_open(page):
                        success_msg = f"✅ Attendance is OPEN for {start_time_str} class!"
                        print(success_msg)
                        notify(success_msg)
                        
                        # Optional: You could add auto-click here
                        # presence_button = page.query_selector("span.set-presence")
                        # if presence_button:
                        #     presence_button.click()
                        #     print("✅ Clicked attendance button")
                        
                        break

                    # Reload the page to check again
                    try:
                        page.reload()
                    except Exception as exc:
                        print(f"⚠️ Reload error: {exc}")

                    # Calculate appropriate sleep time based on how far into the class we are
                    elapsed = datetime.now() - start_dt
                    if elapsed <= timedelta(minutes=EARLY_ATTENDANCE_WINDOW_MIN):
                        sleep_min = EARLY_POLL_MIN
                        sleep_max = EARLY_POLL_MAX
                    else:
                        sleep_min = LATE_POLL_MIN
                        sleep_max = LATE_POLL_MAX

                    sleep_time = random.uniform(sleep_min, sleep_max)
                    print(f"⏱️  Sleeping {sleep_time:.1f}s before next check...")
                    time.sleep(sleep_time)

                else:
                    # Loop ended because we reached end_dt
                    print(f"⏱️ Class ended at {end_dt.strftime('%H:%M')} - attendance never opened")
                    notify(f"⚠️ Class at {start_time_str} ended without attendance opening")

            # All classes for today are done, sleep until tomorrow
            print("\n📅 All classes for today processed. Sleeping until tomorrow...")
            next_day = datetime.combine(today + timedelta(days=1), datetime.min.time())
            sleep_seconds = (next_day - datetime.now()).total_seconds()
            time.sleep(max(0, sleep_seconds))

        browser.close()


if __name__ == "__main__":
    main()