from twilio.rest import Client
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import psycopg2
import time
import json
import os


# Twilio account details
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")
receiver_phone_number = os.environ.get("RECEIVER_PHONE_NUMBER")
url = os.environ.get("URL")

# database
print(os.environ.get("DATABASE_URL"))
db_uri = os.environ.get("DATABASE_URL")

# connect to database
conn = psycopg2.connect(db_uri)
cur = conn.cursor()



def create_db():
    cur.execute(
        """ CREATE TABLE IF NOT EXISTS houses(
                id SERIAL PRIMARY KEY,
                title TEXT,
                location TEXT
    )"""
    )

create_db() 


def update_db(houses):
    houses_tuple = [(house["title"], house["location"]) for house in houses]
    # delete and recreate table
    cur.execute("DROP TABLE IF EXISTS houses")
    create_db()

    insert_script = "INSERT INTO houses(title, location) VALUES (%s, %s)"
    cur.executemany(insert_script, houses_tuple)
    conn.commit()


# Function to send the SMS notification
def send_sms(msg):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        from_=f"{twilio_phone_number}", body=msg, to=f"{receiver_phone_number}"
    )
    print("SMS notification sent!")


# Function to load previously housing from database
def load_previous_house():
    cur.execute("SELECT * FROM houses")
    previous_house = cur.fetchall()
    return previous_house



# Function to scrape new houses
def search_for_new_houses():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(15)

    scraped_new_houses = []
    housing_titles = driver.find_elements(
        "xpath", "//span[contains(@class, 'address-part')]"
    )
    current_idx = 0
    try:
        for idx, n in enumerate(housing_titles):
            if idx % 2 == 0:
                house = {}
                house["title"] = n.text
            else:
                house["location"] = n.text
                scraped_new_houses.append(house)
                current_idx += 1
        driver.quit()
        return scraped_new_houses
    except Exception as e:
        print(e)


def generate_msg_text(new_added):
    txt = f"New houses on {url}\n"
    for idx, house in enumerate(new_added):
        txt += f"{idx}. {house['title']}: {house['location']}\n"
    return txt


def new_added_houses(new, pre):
    print("new", new)
    print("pre", pre)
    added_houses = []
    for house in new:
        house_exists = False
        for prev_house in pre:
            if (
                house["title"] == prev_house[1]
                and house["location"] == prev_house[2]
            ):
                house_exists = True
                break
        if not house_exists:
            added_houses.append(house)
    return added_houses


def main():
    previous_houses = load_previous_house()
    new_houses = search_for_new_houses()
    new_added = new_added_houses(new_houses, previous_houses)
    print("previous_houses", previous_houses)
    print("new_houses", new_houses)
    print("new_added", new_added)
    if new_added:
        msg = generate_msg_text(new_added)
        send_sms(msg)
        update_db(new_houses)
        print(f"{ len(new_added) } houses found!")
    else:
        print("No new houses found!")


main()
cur.close()
conn.close()
