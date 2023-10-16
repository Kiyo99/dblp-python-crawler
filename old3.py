import requests
from bs4 import BeautifulSoup
import json
import unicodedata
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Function to preprocess author names
def preprocess_author_name(author_name):
    author_name = "".join(
        char
        for char in unicodedata.normalize("NFKD", author_name)
        if not unicodedata.combining(char)
    )
    return author_name

# Function to retrieve a list of authors who published at a conference
def get_icse_authors(conference_name):
    url = f"http://dblp.uni-trier.de/search/publ?q={conference_name}:"

    # Set up the Selenium web driver
    driver = webdriver.Chrome()  # You may need to install ChromeDriver
    driver.get(url)

    # Wait for the initial page to load
    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".publ-list")))

    # Keep scrolling and loading more data until no more data is available or year is 2013
    while True:
        # Scroll down to trigger more data loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        time.sleep(5)  # Add a delay to allow content loading
        
        # Check for the "Reached the end of the page" message
        if "Reached the end of the page" in driver.page_source:
            break

        # Check if the year is 2013
        if "2015" in driver.page_source:
            break

    # Get the page source with all the loaded data
    page_source = driver.page_source
    driver.quit()

    print("Page loaded")

    # Process the loaded page source with BeautifulSoup as before
    soup = BeautifulSoup(page_source, "html.parser")

    authors = {}
    authorlist = []
    author_elements = soup.find_all("span", itemprop="author")
    for author_element in author_elements:
        author_name = author_element.find("span", itemprop="name").text
        author_name = preprocess_author_name(author_name)
        author_url = author_element.find("a", itemprop="url")["href"]
        authors[author_name] = {
            "author_name": author_name,
            "url": author_url,
            "coauthors": set(),
        }

    print("Authors loaded")

    return authors

# Function to retrieve co-authors for a given author
def get_coauthors(author_data, authors):
    print("get_coauthors")
    author_name = author_data["author_name"]
    author_url = author_data["url"]

    response = requests.get(author_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        coauthors = set()
        coauthor_elements = soup.find_all("span", itemprop="author")
        for coauthor_element in coauthor_elements:
            coauthor_name = coauthor_element.find("span", itemprop="name").text
            coauthors.add(coauthor_name)

        coauthors.discard(author_name)
        valid_coauthors = [coauthor for coauthor in coauthors if coauthor in authors]

        return valid_coauthors
    else:
        print(
            f"Failed to retrieve data from DBLP for {author_name}. Status code: {response.status_code}"
        )
        return []

def main():
    authors = get_icse_authors("ICSE")
    nodes = []
    links = []

    for author_name, author_data in authors.items():
        coauthors = get_coauthors(author_data, authors)
        nodes.append({"id": author_name})

        for coauthor in coauthors:
            links.append({"source": author_name, "target": coauthor})
            authors[coauthor]["coauthors"].add(author_name)

    nodes = [author for author in nodes if authors[author["id"]]["coauthors"]]
    links = [
        link
        for link in links
        if link["source"] in authors and link["target"] in authors
    ]

    graph_data = {"nodes": nodes, "links": links}

    print(json.dumps(graph_data, indent=2))

    with open("coauthors_collab_filtered2.json", "w") as f:
        json.dump(graph_data, f)

    print("File saved to coauthors_collab_filtered.json")

if __name__ == "__main__":
    main()
