import threading
import time
import requests
import socket
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os


class SafeList:
    def __init__(self):
        self.list = []
        self.mutex = threading.Lock()

    def insert(self, item):
        with self.mutex:
            self.list.append(item)

    def batch_insert(self, item_list):
        with self.mutex:
            self.list.extend(item_list)

    def pop(self):
        with self.mutex:
            return self.list.pop()

    def is_empty(self):
        return len(self.list) == 0


class SafeSet:
    def __init__(self):
        self._set = set()
        self.mutex = threading.Lock()

    def batch_insert(self, item_list):
        with self.mutex:
            for item in item_list:
                self._set.add(item)

    def insert(self, item):
        with self.mutex:
            self._set.add(item)

    def contains(self, item):
        return item in self._set


class Site:
    def __init__(self, url, ip, geolocation, resp_time):
        self.url = url
        self.ip = ip
        self.geolocation = geolocation
        self.response_time = resp_time


class Scrapper:
    def __init__(self, safe_set: SafeSet, safe_list: SafeList):
        self.safe_set = safe_set
        self.safe_list = safe_list

        with open("scraped.txt", "w") as f:
            f.write("")

    def write(self, s: Site):
        mutex = threading.Lock()
        with mutex:
            with open("scraped.txt", "a") as f:
                f.write(f"{s.response_time}, {s.geolocation}, {s.ip}, {s.url}\n")

    def get_ip(self, url: str):
        hostname = urlparse(url).hostname
        ip = socket.gethostbyname(hostname)
        return ip

    def get_location(self, ip):
        if ip == "":
            return "Country Not Found"

        country = None
        # try 5 times
        for _ in range(5):
            try:
                response = requests.get(f"http://ip-api.com/json/{ip}").json()

                if response.get("status") != "success":
                    print(response)
            except Exception as e:
                print(e)
                continue
            country = response.get("country")

            if country:
                return country
            time.sleep(1)

            return "Country Not Found"

    def run(self):
        while not self.safe_list.is_empty():
            url = self.safe_list.pop()

            start = time.time()
            try:
                print(url)
                resp = requests.get(url)
            except Exception as e:
                print(f"Erroneous url: {url}")
                print(e)
                continue

            time_taken = str(round((time.time() - start), 2))
            ip = self.get_ip(url)
            location = self.get_location(ip)
            self.write(Site(url, ip, location, time_taken))

            soup = BeautifulSoup(resp.content, "html.parser")
            links = soup.select("a[href]")
            for link in links:
                url_string = link["href"]
                parsed = urlparse(url_string)
                if parsed.hostname == "" or parsed.hostname is None:
                    continue

                if parsed.scheme == "" or parsed.scheme is None:
                    continue

                if not self.safe_set.contains(url_string):
                    self.safe_set.insert(url_string)
                    self.safe_list.insert(url_string)

            time.sleep(2)


def main():
    safe_set = SafeSet()
    safe_list = SafeList()

    number_threads = 3
    thread_list = []

    # Initialize and read from a file of urls
    with open("initial.txt", "r") as f:
        urls = f.read().splitlines()
        safe_list.batch_insert(urls)
        safe_set.batch_insert(urls)

    # print("Starting URLs:\n")
    # print(urls)
    # initialize threads and start them
    for _ in range(number_threads):
        scrapper = Scrapper(safe_set, safe_list)
        thread = threading.Thread(target=scrapper.run)
        thread_list.append(thread)

        thread.start()


if __name__ == "__main__":
    main()
