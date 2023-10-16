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
            coauthors.append({"name": coauthor_name, "pid": coauthor_pid, "count": 0})

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
                            coauthor["pid"] in author.get("pid")
                            for author in article_authors
                        ):
                            coauthor["count"] += 1

        # Sort coauthors by count in descending order
        coauthors.sort(key=lambda x: x["count"], reverse=True)

        # Get the top 5 coauthors
        top_5_coauthors = coauthors[:5]

        # For each coauthor, fetch their top 5 collaborators
        for coauthor in top_5_coauthors:
            coauthor["collaborators"] = get_top_collaborators(coauthor["pid"])

        return top_5_coauthors

    return None


# Function to retrieve top 5 collaborators for a coauthor within ESE
def get_top_collaborators(coauthor_pid):
    url = f"https://dblp.uni-trier.de/pid/{coauthor_pid}.xml?view=collaborators"

    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        collaborators = []
        author_elements = soup.find_all("author")

        for author_element in author_elements:
            collaborator_name = preprocess_author_name(author_element.text)
            collaborator_pid = author_element.get("pid")
            collaborators.append(
                {"name": collaborator_name, "pid": collaborator_pid, "count": 0}
            )

        # Fetch ESE publications for the coauthor
        coauthor_url = f"https://dblp.uni-trier.de/pid/{coauthor_pid}.xml"
        coauthor_response = requests.get(coauthor_url)
        if coauthor_response.status_code == 200:
            coauthor_soup = BeautifulSoup(coauthor_response.text, "lxml")
            ese_publications = coauthor_soup.find_all(
                "journal", text="Empir. Softw. Eng."
            )
            for publication in ese_publications:
                # Find all authors of the publication
                publication_authors = publication.find_all("author")
                for collaborator in collaborators:
                    if any(
                        collaborator["pid"] in author.get("pid")
                        for author in publication_authors
                    ):
                        collaborator["count"] += 1

        # Sort collaborators by count in descending order
        collaborators.sort(key=lambda x: x["count"], reverse=True)

        # Get the top 5 collaborators
        return collaborators[:5]

    return None


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
            "children": get_top_collaborators(coauthor["pid"]),
        }
        author_node["children"].append(coauthor_node)

    sunburst_data["children"].append(author_node)

# Save the final JSON
with open("final_ese_coauthors.json", "w") as f:
    json.dump(sunburst_data, f, indent=2)

print("File saved to final_ese_coauthors.json")
