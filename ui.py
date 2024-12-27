from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from tkinter import scrolledtext
from selenium import webdriver
from datetime import datetime
from bs4 import BeautifulSoup
import tkinter as tk
import threading
import requests
import logging
import time


class ScraperUI:
    def __init__(self, master=None):
        self.sleep_time = 10
        self.scraper_running = False
        self.master = master
        self.master.wm_iconbitmap("./data/diamond_icon.ico")
        self.master.title("Craigslist Scraper V1.0")
        self.frame = tk.Frame(self.master)
        self.frame.pack(fill="both", expand=True)

        self.text_area_frame = tk.Frame(self.frame)
        self.text_area_frame.pack(fill="both", expand=True)

        self.info_text_area = scrolledtext.ScrolledText(
            self.text_area_frame, width=40, height=20)
        self.info_text_area.pack(side="left", fill="both", expand=True)
        self.info_text_area.config(state="disabled")

        self.ui_frame = tk.Frame(self.text_area_frame)
        self.ui_frame.pack(side="right", fill="both", expand=True)

        self.time_entry_frame = tk.Frame(self.ui_frame)
        self.time_entry_frame.pack(side="top", padx=25, pady=25)

        self.time_label = tk.Label(
            self.time_entry_frame, text=f"Scrape interval [in minutes]> {self.sleep_time} <")
        self.time_label.pack(side="left")

        self.time_entry_label = tk.Label(
            self.time_entry_frame, text="")
        self.time_entry_label.pack(side="right")

        self.time_entry = tk.Entry(self.time_entry_frame, width=5)
        self.time_entry.pack(side="left")

        self.set_time_button = tk.Button(
            self.time_entry_frame, text="Set", command=self.set_sleep_time)
        self.set_time_button.pack(side="right")

        self.toggle_button = tk.Button(
            self.ui_frame, text="Start", command=self.start)
        self.toggle_button.pack(side="left")

    def set_sleep_time(self):
        try:
            temp_time = int(self.time_entry.get())
            if temp_time > 1:
                self.sleep_time = temp_time
                self.time_label['text'] = f"Scrape interval [in minutes]> {self.sleep_time} <"
            else:
                self.write_to_info(
                    "Scrape Interval:\n\tMin: 2 minutes\n")
        except ValueError:
            self.write_to_info("Invalid input. Please enter a valid number.")

    def write_to_info(self, message):
        self.info_text_area.config(state="normal")
        self.info_text_area.insert(tk.END, message + "\n")
        self.info_text_area.see(tk.END)
        self.info_text_area.config(state="disabled")

    def start(self):
        if not self.scraper_running:
            if len(self.get_links()) > 0:
                self.write_to_info("Starting up . . .\n")
                self.scrape_thread = threading.Thread(
                    target=self.scrape_and_send)
                self.scrape_thread.daemon = True
                self.scrape_thread.start()
                self.scraper_running = True
            else:
                self.write_to_info(
                    "No links found, add links and retry")
        else:
            self.write_to_info(
                "Already running . . .")

    def scrape_and_send(self):
        while True:
            try:
                seen_listings = self.get_seen_listings()
                self.write_to_info("Getting links . . .\n")
                links = self.get_links()
                for link in links:
                    self.write_to_info(f"Now scraping: \n{link}")
                    cars = self.scrape_craigslist(link)
                    self.write_to_info(
                        f"Finished scraping @ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n"
                    )
                    for car in cars:
                        listing_id = car['link'].split('/')[-1]
                        if listing_id not in seen_listings:
                            self.write_to_info(
                                f"\nNew listing found: {listing_id}, sending to discord.")
                            message = self.construct_payload(car)
                            self.send_discord_message(message)
                            self.add_seen_listing(listing_id)
                self.write_to_info(
                    f"\nNow waiting {self.sleep_time} minutes until next scrape . . .")
                time.sleep(self.sleep_time * 60)
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                return

    def get_discord_login(self, file_path='./discord.txt'):
        try:
            with open(file_path, 'r') as file:
                channel_url = file.readline()
                auth = file.readline()
            return channel_url, auth
        except Exception as e:
            self.write_to_info(f"\nError: {e}")
            return

    def get_links(self, file_path='./links.txt'):
        try:
            with open(file_path, 'r') as file:
                links = file.read()
                links = links.splitlines()
            return links
        except FileNotFoundError:
            self.write_to_info(f"File {file_path} not found.")
            return []

    def get_seen_listings(self, file_path='./data/seen_listings.txt'):
        try:
            with open(file_path, 'r') as file:
                seen_listings = file.read().splitlines()
            return seen_listings
        except FileNotFoundError:
            return []

    def add_seen_listing(self, listing_id):
        with open('./data/seen_listings.txt', 'a') as file:
            file.write(f"{listing_id}\n")

    def send_discord_message(self, message):
        self.write_to_info(message)
        channel_url, auth = self.get_discord_login()
        payload = {"content": message}
        headers = {"Authorization": auth}
        response = requests.post(
            channel_url, json=payload, headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to send Discord message: {response.text}")

    def construct_payload(self, car):
        try:
            message = (
                f"Title: {car.get('title', 'Not Available')}\n"
                f"Odometer: {car.get('odometer', 'Not Available')}\n"
                f"Date: {car.get('date', 'Not Available')}\n"
                f"Price: {car.get('price', 'Not Available')}\n"
                f"Link: {car.get('link', 'Not Available')}"
            )
        except Exception as e:
            self.write_to_info(f"Error: {e}")
            message = None
        return message

    def scrape_craigslist(self, link):
        try:
            content = get_html_selenium(link)
            soup = BeautifulSoup(content, 'html.parser')
            cars = get_cars(soup)
            return cars
        except requests.exceptions.RequestException as e:
            self.write_to_info(f"Error during web request: {e}")
            return None
        except Exception as e:
            self.write_to_info(f"An error occurred: {e}")
            return None


def get_html_selenium(url):
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(2)
    html = driver.page_source
    driver.quit()
    return html


def get_cars(soup):
    cars = []
    for div in soup.find_all('div', {"class": "gallery-card"}):
        car = {}

        link = div.find('a').get('href').strip()
        car['link'] = link

        title = div.find('span', class_='label')
        if title:
            title = title.text.strip()
            car['title'] = title

        price = div.find('span', class_='priceinfo')
        if price:
            price = price.text.strip()
            car['price'] = price

        info = div.find('div', class_='meta')
        if info:
            info = info.text.strip()
            date = get_date(info)
            car['date'] = date
            odometer = get_odometer(date, info)
            car['odometer'] = f"{odometer} mi"

        cars.append(car)
    return cars


def get_date(info):
    date_str = info[:5]
    try:
        date = datetime.strptime(date_str, '%m/%d')
        return date.strftime('%m/%d')
    except ValueError:
        date = info[:4]
        return date


def get_odometer(date, info):
    info = info.replace(date, "").split()
    return info[0]
