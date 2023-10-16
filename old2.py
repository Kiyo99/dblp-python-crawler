import requests
from bs4 import BeautifulSoup
import json
import unicodedata

# Function to preprocess author names
def preprocess_author_name(author_name):
    # Remove special characters and convert to ASCII
    author_name = ''.join(char for char in unicodedata.normalize('NFKD', author_name) if not unicodedata.combining(char))
    return author_name

# Function to retrieve a list of authors who published at a conference
def get_icse_authors(conference_name):
    dblp_url = f"http://dblp.uni-trier.de/search/publ?q={conference_name}:"
    response = requests.get(dblp_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the author information and their URLs
        authors = {}
        author_elements = soup.find_all("span", itemprop="author")
        for author_element in author_elements:
            author_name = author_element.find("span", itemprop="name").text
            author_name = preprocess_author_name(author_name)
            author_url = author_element.find("a", itemprop="url")["href"]
            authors[author_name] = {"author_name": author_name,"url": author_url, "coauthors": set()}

        return authors
    else:
        print(f"Failed to retrieve data from DBLP. Status code: {response.status_code}")
        return {}

# Function to retrieve co-authors for a given author
def get_coauthors(author_data, authors):
    author_name = author_data["author_name"]
    author_url = author_data["url"]

    response = requests.get(author_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the co-authors
        coauthors = set()
        coauthor_elements = soup.find_all("span", itemprop="author")
        for coauthor_element in coauthor_elements:
            coauthor_name = coauthor_element.find("span", itemprop="name").text
            coauthors.add(coauthor_name)

        # Remove duplicates
        coauthors.discard(author_name)

        # Return only the co-authors that are in the list of authors
        valid_coauthors = [coauthor for coauthor in coauthors if coauthor in authors]

        return valid_coauthors
    else:
        print(f"Failed to retrieve data from DBLP for {author_name}. Status code: {response.status_code}")
        return []

def main():
    authors = get_icse_authors("MSR")
    nodes = []  # Create an empty list for nodes
    links = []  # Create an empty list for links

    for author_name, author_data in authors.items():
        coauthors = get_coauthors(author_data, authors)

        # Add the author as a node
        nodes.append({"id": author_name})

        # Add links to co-authors
        for coauthor in coauthors:
            links.append({"source": author_name, "target": coauthor})
            authors[coauthor]["coauthors"].add(author_name)

    # Filter out co-authors that don't have any co-authorship links
    nodes = [author for author in nodes if authors[author["id"]]["coauthors"]]
    links = [link for link in links if link["source"] in authors and link["target"] in authors]

    # Create a JSON object with nodes and links
    graph_data = {"nodes": nodes, "links": links}

    # Print the JSON object as a string
    print(json.dumps(graph_data, indent=2))

    with open("coauthors_collab_filtered.json", "w") as f:
        json.dump(graph_data, f)

    print("File saved to coauthors_collab_filtered.json")

if __name__ == "__main__":
    main()

