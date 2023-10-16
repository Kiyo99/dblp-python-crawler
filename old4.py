import requests
from bs4 import BeautifulSoup
import json
import unicodedata
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from collections import Counter


# Function to preprocess author names
def preprocess_author_name(author_name):
    author_name = "".join(
        char
        for char in unicodedata.normalize("NFKD", author_name)
        if not unicodedata.combining(char)
    )
    return author_name


# Function to retrieve a list of authors who published at a conference within the last 5 years
def get_icse_authors_last_5_years(conference_name):
    url = f"http://dblp.uni-trier.de/search/publ?q={conference_name}:"

    # Set up the Selenium web driver
    driver = webdriver.Chrome()  # You may need to install ChromeDriver
    driver.get(url)

    # Wait for the initial page to load
    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".publ-list")))

    # Keep scrolling and loading more data until no more data is available
    while True:
        # Scroll down to trigger more data loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        time.sleep(5)  # Add a delay to allow content loading

        # Check for the "Reached the end of the page" message
        if "Reached the end of the page" in driver.page_source:
            break

        # Check if the year is 2018
        if "2020" in driver.page_source:
            break

    # Get the page source with all the loaded data
    page_source = driver.page_source
    driver.quit()

    print("Page loaded")

    # Process the loaded page source with BeautifulSoup as before
    soup = BeautifulSoup(page_source, "html.parser")

    authors = {}
    author_elements = soup.find_all("span", itemprop="author")
    for author_element in author_elements:
        author_name = author_element.find("span", itemprop="name").text
        author_name = preprocess_author_name(author_name)
        author_url = author_element.find("a", itemprop="url")["href"]
        authors[author_name] = {
            "author_name": author_name,
            "url": author_url,
            "coauthors": [],
            "most_collaborated_with": None,
            "children": [],
        }

    print("Authors loaded")

    return authors


# Function to check if two authors have collaborated within the last 5 years
def has_collaborated_last_5_years(coauthor_name, author_name, current_year):
    # Define the URL format for the author's DBLP profile page
    author_url_format = "http://dblp.uni-trier.de/pers/xx/{author_slug}"

    # Create author slugs from their names (replace spaces with '_')
    coauthor_slug = coauthor_name.replace(" ", "_")
    author_slug = author_name.replace(" ", "_")

    # Generate URLs for both authors' DBLP profile pages
    coauthor_url = author_url_format.format(author_slug=coauthor_slug)
    author_url = author_url_format.format(author_slug=author_slug)

    # Get the DBLP profile pages for both authors
    coauthor_page = requests.get(coauthor_url)
    author_page = requests.get(author_url)

    # Check if both pages were retrieved successfully
    if coauthor_page.status_code == 200 and author_page.status_code == 200:
        # Parse the HTML content of the profile pages
        coauthor_soup = BeautifulSoup(coauthor_page.text, "html.parser")
        author_soup = BeautifulSoup(author_page.text, "html.parser")

        # Find and extract the publication years of co-authored papers
        coauthored_years = set()

        # Extract publication years from the co-author's page
        coauthored_paper_elements = coauthor_soup.find_all("span", itemprop="headline")
        for paper_element in coauthored_paper_elements:
            paper_title = paper_element.text
            publication_year = get_publication_year(coauthor_soup, paper_title)
            if publication_year:
                coauthored_years.add(publication_year)

        # Check if any co-authored papers were published within the last 5 years
        for year in coauthored_years:
            if int(year) >= current_year - 5:
                return True  # Collaboration found within the last 5 years

        # If no recent collaborations were found on the co-author's page,
        # check for recent collaborations on the author's page as well
        author_years = set()
        author_paper_elements = author_soup.find_all("span", itemprop="headline")
        for paper_element in author_paper_elements:
            paper_title = paper_element.text
            publication_year = get_publication_year(author_soup, paper_title)
            if publication_year:
                author_years.add(publication_year)

        for year in author_years:
            if int(year) >= current_year - 5:
                return True  # Collaboration found within the last 5 years

    # If no recent collaborations were found on either page, return False
    return False


# Function to extract publication year from a paper title
def get_publication_year(soup, paper_title):
    # Search for the paper title in the HTML content
    paper_element = soup.find("span", itemprop="headline", text=paper_title)

    if paper_element:
        # If found, navigate to the parent element (containing publication year)
        parent_element = paper_element.find_parent("li", class_="publ")

        if parent_element:
            # Extract and parse the publication year
            year_element = parent_element.find("span", class_="year")
            if year_element:
                year = year_element.text.strip()
                try:
                    return int(year)
                except ValueError:
                    return None

    return None


# Function to retrieve co-authors and track their collaborations
def get_coauthors_and_collaborations(author_data, authors, current_year, depth):
    print("Getting co-authors for", author_data["author_name"])
    print(f"author data: {author_data}")

    if depth <= 0:
        return

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

        for coauthor in valid_coauthors:
            collaborated_recently = has_collaborated_last_5_years(
                coauthor, author_name, current_year
            )
            if collaborated_recently:
                author_data["coauthors"].append(
                    {
                        "author_name": coauthor,
                        "most_collaborated_with": None,
                        "coauthors": [],
                    }
                )
            else:
                author_data["children"].append(coauthor)

        for coauthor_data in author_data["coauthors"]:
            get_coauthors_and_collaborations(
                coauthor_data, authors, current_year, depth - 1
            )


def find_most_collaborated(authors):
    for author in authors.values():
        coauthors = author["coauthors"]
        if coauthors:
            coauthor_counts = Counter()
            for coauthor in coauthors:
                coauthor_counts[coauthor["author_name"]] += 1
                find_most_collaborated(coauthor["coauthors"])
            most_collaborated_with = coauthor_counts.most_common(1)
            if most_collaborated_with:
                author["most_collaborated_with"] = most_collaborated_with[0][0]


def main():
    current_year = 2023  # Replace with the current year
    authors = get_icse_authors_last_5_years("ICSE")

    for author_data in authors.values():
        get_coauthors_and_collaborations(author_data, authors, current_year, depth=4)

    find_most_collaborated(authors)

    graph_data = {
        "name": "ICSE Authors (Last 5 Years)",
        "children": list(authors.values()),
    }

    print(json.dumps(graph_data, indent=2))

    with open("icse_authors_last_5_years.json", "w") as f:
        json.dump(graph_data, f)

    print("File saved to icse_authors_last_5_years.json")


if __name__ == "__main__":
    main()

# data = [
#     "Ahmed E. Hassan",
#     "Lionel C. Briand",
#     "David Lo 0001",
#     "Foutse Khomh",
#     "Massimiliano Di Penta",
#     "Victor R. Basili",
#     "Bram Adams",
#     "Xin Xia 0001",
#     "Tim Menzies",
#     "Cor-Paul Bezemer",
#     "Weiyi Shang",
#     "Alexander Serebrenik",
#     "Ying Zou 0001",
#     "Jeffrey C. Carver",
#     "Yann-Gaël Guéheneuc",
#     "Giuliano Antoniol",
#     "Gabriele Bavota",
#     "Claes Wohlin",
#     "Burak Turhan",
#     "Emad Shihab",
#     "Daniel M. Germán",
#     "Sven Apel",
#     "Per Runeson",
#     "Rocco Oliveto",
#     "Fabio Palomba",
#     "Ken-ichi Matsumoto",
#     "Laurie A. Williams",
#     "Christoph Treude",
#     "Martin Monperrus",
#     "Natalia Juristo Juzgado",
#     "Yasutaka Kamei",
#     "Steffen Herbold",
#     "Abram Hindle",
#     "Andrea De Lucia",
#     "Arie van Deursen",
#     "Andy Zaidman",
#     "Sebastiano Panichella",
#     "Shane McIntosh",
#     "Romain Robbes",
#     "Alberto Bacchelli",
#     "Filippo Lanubile",
#     "Barbara A. Kitchenham",
#     "Tse-Hsun (Peter) Chen",
#     "Tegawendé F. Bissyandé",
#     "Meiyappan Nagappan",
#     "Chanchal Kumar Roy",
#     "Zhenchang Xing",
#     "Sira Vegas",
#     "Jacques Klein",
#     "Taghi M. Khoshgoftaar",
#     "James Miller 0001",
#     "Andrea Arcuri",
#     "Raula Gaikovina Kula",
# ]



import json
import re
from xml.dom import minidom
import requests
from bs4 import BeautifulSoup


# Function to preprocess author name
def preprocess_author_name(name):
    # Add any preprocessing steps if needed
    return name


# Function to get author's pid
def get_pid(name):
    # Remove numbers and parentheses from the author name
    author_name = re.sub(r"\(\d+\)", "", name).strip()
    url = "https://dblp.uni-trier.de/search/author?xauthor=" + author_name
    response = requests.get(url)

    xmldoc = minidom.parseString(response.content)
    author_elements = xmldoc.getElementsByTagName("author")

    for item in author_elements:
        item_name = item.firstChild.nodeValue.strip()
        if item.hasAttribute("pid") and item_name == author_name:
            return item.attributes["pid"].value

    return None


# Function to retrieve top 5 coauthors within ESE for an author using their PID
def get_top_coauthors(pid):
    url = f"https://dblp.uni-trier.de/pid/{pid}.xml?view=coauthor"

    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        coauthors = []
        author_elements = soup.find_all("author")

        for author_element in author_elements:
            coauthor_name = preprocess_author_name(author_element.text)
            coauthor_pid = author_element.get("pid")
            coauthors.append(
                {"name": coauthor_name, "pid": coauthor_pid, "value": 100, "count": 0}
            )

        # Fetch ESE publications for the main author
        author_url = f"https://dblp.uni-trier.de/pid/{pid}.xml"
        author_response = requests.get(author_url)
        if author_response.status_code == 200:
            author_soup = BeautifulSoup(author_response.text, "lxml")
            articles = author_soup.find_all("r")

            for article in articles:
                article_authors = article.find_all("author")
                ese_publication = article.find("journal", text="Empir. Softw. Eng.")
                if ese_publication:
                    for coauthor in coauthors:
                        if any(
                            coauthor["name"] == author.get("pid")
                            for author in article_authors
                        ):
                            coauthor["count"] += 1

        # Sort coauthors by count in descending order
        coauthors.sort(key=lambda x: x["count"], reverse=True)

        # Get the top 5 coauthors
        top_5_coauthors = coauthors[:5]

        # For each coauthor, fetch their top 5 collaborators
        for coauthor in top_5_coauthors:
            coauthor["collaborators"] = get_top_collaborators(coauthor["name"])

        return top_5_coauthors

    return None


# Function to retrieve top 5 collaborators for a coauthor within ESE
def get_top_collaborators(coauthor_name):
    url = f"https://dblp.uni-trier.de/search/author?xauthor={coauthor_name}"
    response = requests.get(url)

    xmldoc = minidom.parseString(response.content)
    author_elements = xmldoc.getElementsByTagName("author")

    for item in author_elements:
        item_name = item.firstChild.nodeValue.strip()
        if item.hasAttribute("pid") and item_name == coauthor_name:
            coauthor_pid = item.attributes["pid"].value
            url = f"https://dblp.uni-trier.de/pid/{coauthor_pid}.xml?view=coauthor"
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                collaborators = []
                author_elements = soup.find_all("author")

                for author_element in author_elements:
                    collaborator_name = preprocess_author_name(author_element.text)
                    collaborators.append(
                        {
                            "name": collaborator_name,
                            "pid": author_element.get("pid"),
                            "value": 100,
                        }
                    )

                return collaborators

    return []


# Example usage:
authors = [
    "Ahmed E. Hassan (68)",
    "Lionel C. Briand (36)",
    "David Lo 0001 (35)",
    "Foutse Khomh (25)",
    "Massimiliano Di Penta (25)",
    "Victor R. Basili (24)",
    "Bram Adams (24)",
    "Xin Xia 0001 (22)",
    "Tim Menzies (21)",
    "Cor-Paul Bezemer (20)",
]

authors_data = {}

for author in authors:
    pid = get_pid(author)
    if pid:
        top_coauthors = get_top_coauthors(pid)
        authors_data[author] = {
            "name": author,
            "pid": pid,
            "most_collaborated": top_coauthors[0]["name"] if top_coauthors else "",
            "top_coauthors": top_coauthors,
        }

# Convert data to a format suitable for visualization
sunburst_data = {
    "name": "ICSE Authors",
    "children": [],
}

for author_name, author_info in authors_data.items():
    author_node = {
        "name": author_info["name"],
        "most_collaborated": author_info["most_collaborated"],
        "url": f"https://dblp.uni-trier.de/pid/{author_info['pid']}.html",
        "children": [],
    }

    for coauthor in author_info["top_coauthors"]:
        coauthor_node = {
            "name": f"{coauthor['name']} ({coauthor['count']})",
            "url": f"https://dblp.uni-trier.de/pid/{coauthor['pid']}.html",
            "value": 100,
            "children": get_top_collaborators(coauthor["name"]),
        }
        author_node["children"].append(coauthor_node)

    sunburst_data["children"].append(author_node)

# Save the final JSON
with open("final_ese_coauthors.json", "w") as f:
    json.dump(sunburst_data, f, indent=2)

print("File saved to final_ese_coauthors.json")
