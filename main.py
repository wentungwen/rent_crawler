import json
import os
from twilio.rest import Client
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time


# Twilio account details
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
receiver_phone_number = os.environ.get('RECEIVER_PHONE_NUMBER')
url = os.environ.get('URL')
previous_listings_file = os.environ.get('PREVIOUS_LISTINGS_FILE')


# Function to send the SMS notification
def send_sms(msg):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        from_=f"{twilio_phone_number}",
        body=msg,
        to=f"{receiver_phone_number}"
    )
    print('SMS notification sent!')


# Function to load previously scraped listings from file
def load_previous_listings():
    try:
        with open(previous_listings_file, 'r') as file:
            previous_house_list = json.load(file)
    except FileNotFoundError:
        previous_house_list = []
        with open(previous_listings_file, 'w') as file:
            json.dump(previous_house_list, file)
    return previous_house_list


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
    # wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    scraped_new_houses = []
    housing_titles = driver.find_elements("xpath", "//span[contains(@class, 'address-part')]")
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


# Function to save updated listings to file
def update_listings(new_added):
    with open(previous_listings_file, 'r') as file:
        previous_houses = json.load(file)
    previous_houses.extend(new_added)
    with open(previous_listings_file, 'w') as file:
        json.dump(previous_houses, file, indent=4)


def new_added_houses(new, pre):
    added_houses = []
    for house in new:
        house_exists = False
        for prev_house in pre:
            if house["title"] == prev_house["title"] and house["location"] == prev_house["location"]:
                house_exists = True
                break
        if not house_exists:
            added_houses.append(house)
    return added_houses


def main():
    previous_houses = load_previous_listings()
    new_houses = search_for_new_houses()
    new_added = new_added_houses(new_houses, previous_houses)
    print(previous_houses, new_houses, new_added)
    if new_added:
        msg = generate_msg_text(new_added)
        # send_sms(msg)
        update_listings(new_added)
        print(f'{ len(new_added) } houses found!')
    else:
        print('No new houses found!')


main()
print('Done!')
