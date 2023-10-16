import requests
from bs4 import BeautifulSoup


# Function to retrieve a list of authors who published at a conference
def get_icse_authors(conference_name):
    print("get_icse_authors")
    dblp_url = f"http://dblp.uni-trier.de/search/publ?q={conference_name}:"
    response = requests.get(dblp_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the author information and their URLs
        authors = []
        author_elements = soup.find_all("span", itemprop="author")
        for author_element in author_elements:
            author_name = author_element.find("span", itemprop="name").text
            author_url = author_element.find("a", itemprop="url")["href"]
            author_data = {"author": author_name, "url": author_url}
            authors.append(author_data)
        return authors
    else:
        print(f"Failed to retrieve data from DBLP. Status code: {response.status_code}")
        return []


# Function to retrieve co-authors for a given author
def get_coauthors(author_data):
    author_name = author_data["author"]
    author_url = author_data["url"]

    response = requests.get(author_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the co-authors
        coauthors = []
        coauthor_elements = soup.find_all("span", itemprop="author")
        for coauthor_element in coauthor_elements:
            coauthor_name = coauthor_element.find("span", itemprop="name").text
            coauthors.append(coauthor_name)

        # Remove duplicates by converting to a set and then back to a list
        coauthors = list(set(coauthors))
        coauthors.remove(author_name)

        return coauthors
    else:
        print(
            f"Failed to retrieve data from DBLP for {author_name}. Status code: {response.status_code}"
        )
        return []


def main():
    icse_authors = get_icse_authors("ICSE")
    for author in icse_authors:
        coauthors = get_coauthors(author)
        print(f"Author: {author['author']}, Co-authors: {coauthors}")


if __name__ == "__main__":
    main()