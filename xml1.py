import json
import re
import requests
from bs4 import BeautifulSoup
from xml.dom import minidom


# Function to preprocess author name
def preprocess_author_name(name):
    # Add any preprocessing steps if needed
    return name


# Function to get author's pid
def get_urlpt(name):
    # Remove numbers and parentheses from the author name
    author_name = re.sub(r"\(\d+\)", "", name).strip()
    url = "https://dblp.uni-trier.de/search/author?xauthor=" + author_name
    response = requests.get(url)

    xmldoc = minidom.parseString(response.content)
    author_elements = xmldoc.getElementsByTagName("author")

    max_count = 0
    most_collaborated = None

    for item in author_elements:
        item_name = item.firstChild.nodeValue.strip()
        if item.hasAttribute("pid") and item_name == author_name:
            return item.attributes["pid"].value

    return None


# Function to retrieve top 5 coauthors for an author using their PID
def get_top_coauthors(pid):
    url = f"https://dblp.uni-trier.de/pid/{pid}.xml?view=coauthor"

    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        coauthors = []
        author_elements = soup.find_all("author")
        coauthor_list = []

        # Variables to track the most collaborated author
        max_collaborations = 0
        most_collaborated_author = None

        for author_element in author_elements:
            coauthor_name = preprocess_author_name(author_element.text)
            coauthor_count = int(author_element.get("count", 0))
            coauthor_list.append(
                {
                    "name": coauthor_name,
                    "count": coauthor_count,
                    "pid": author_element.get("pid"),
                }
            )

            # Update most collaborated author
            if coauthor_count > max_collaborations:
                max_collaborations = coauthor_count
                most_collaborated_author = coauthor_name

        # Sort coauthors by count in descending order
        coauthor_list.sort(key=lambda x: x["count"], reverse=True)
        coauthors = coauthor_list[:5]  # Get the top 5 coauthors

        # Add most collaborated author to each coauthor's data
        for coauthor in coauthors:
            coauthor["most_collaborated"] = most_collaborated_author

        return coauthors
    else:
        return None


# Function to convert author and coauthor data to the desired sunburst format
def convert_to_sunburst_data(authors_data):
    sunburst_data = {"name": "ICSE Authors", "children": []}

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
                "value": 60,
                "children": [],
            }

            coauthor_list = get_top_coauthors(
                coauthor["pid"]
            )  # Get top 5 coauthors for this co-author
            for coauthor_co in coauthor_list:
                coauthor_co_node = {
                    "name": f"{coauthor_co['name']} ({coauthor_co['count']})",
                    "value": 100,  # Set the value for co-authors' co-authors
                    "children": [],
                }
                coauthor_node["children"].append(coauthor_co_node)

            author_node["children"].append(coauthor_node)

        sunburst_data["children"].append(author_node)

    return sunburst_data


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
    pid = get_urlpt(author)
    if pid:
        top_coauthors = get_top_coauthors(pid)
        most_collaborated = max(top_coauthors, key=lambda x: x["count"])["name"]
        authors_data[author] = {
            "name": author,
            "pid": pid,
            "top_coauthors": top_coauthors,
            "most_collaborated": most_collaborated,
        }

# Get the top 10 authors for saving in JSON
top_10_authors = list(authors_data.keys())[:10]

# Remove numbers from author names for saving in JSON
for author in authors_data:
    for top_author in top_10_authors:
        if top_author in author:
            authors_data[author]["name"] = top_author

# Convert data to sunburst format
sunburst_data = convert_to_sunburst_data(authors_data)

# Save the final JSON with only the top 10 authors
with open("top_10_ese.json", "w") as f:
    json.dump(sunburst_data, f, indent=2)

print("File saved to top_10_ese.json")
