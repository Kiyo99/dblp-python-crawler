from xml.dom import minidom
import requests
from bs4 import BeautifulSoup

# Function to preprocess author names
def preprocess_author_name(author_name):
    return author_name.replace(" ", "_")

# Get Author's pid
def get_urlpt(name):
    url = 'http://dblp.uni-trier.de/search/author?xauthor='+name
    response = requests.get(url)
    
    xmldoc = minidom.parseString(response.content)
    item = xmldoc.getElementsByTagName('author')[0]
    
    if item.hasAttribute("pid"):
        return item.attributes['pid'].value
    
    return None

# Function to retrieve coauthors from DBLP in XML format
def get_coauthors_from_dblp(author_name):
    url = f"https://dblp.uni-trier.de/pid/{author_name}.xml?view=coauthor"
    
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        coauthors = {}
        author_elements = soup.find_all("author")
        for author_element in author_elements:
            coauthor_name = preprocess_author_name(author_element.text)
            coauthor_count = int(author_element["count"])
            coauthors[coauthor_name] = {
                "name": coauthor_name,
                "count": coauthor_count,
                "most_collaborated": None,
                "children": [],
            }
        return coauthors
    else:
        return None

# Filter authors with at least 10 papers for ese
authors = [
    'Ahmed E. Hassan', 'Lionel C. Briand', 'David Lo 0001', 'Foutse Khomh',
    'Massimiliano Di Penta', 'Victor R. Basili', 'Bram Adams', 'Xin Xia 0001',
    'Tim Menzies', 'Cor-Paul Bezemer', 'Weiyi Shang', 'Alexander Serebrenik',
    'Ying Zou 0001', 'Jeffrey C. Carver', 'Yann-Gaël Guéheneuc',
    'Giuliano Antoniol', 'Gabriele Bavota', 'Claes Wohlin', 'Burak Turhan',
    'Emad Shihab', 'Daniel M. Germán', 'Sven Apel', 'Per Runeson', 'Rocco Oliveto',
    'Fabio Palomba', 'Ken-ichi Matsumoto', 'Laurie A. Williams', 'Christoph Treude',
    'Martin Monperrus', 'Natalia Juristo Juzgado', 'Yasutaka Kamei', 'Steffen Herbold',
    'Abram Hindle', 'Andrea De Lucia', 'Arie van Deursen', 'Andy Zaidman',
    'Sebastiano Panichella', 'Shane McIntosh', 'Romain Robbes', 'Alberto Bacchelli',
    'Filippo Lanubile', 'Barbara A. Kitchenham', 'Tse-Hsun (Peter) Chen',
    'Tegawendé F. Bissyandé', 'Meiyappan Nagappan', 'Chanchal Kumar Roy',
    'Zhenchang Xing', 'Sira Vegas', 'Jacques Klein', 'Taghi M. Khoshgoftaar',
    'James Miller 0001', 'Andrea Arcuri', 'Raula Gaikovina Kula'
]

# Process and retrieve data for each author and their top collaborators
data = {}
for author_name in authors:
    data[author_name] = {"name": author_name, "children": []}
    coauthors = get_coauthors_from_dblp(preprocess_author_name(author_name))
    if coauthors:
        data[author_name]["children"] = list(coauthors.values())

# Print the data (You can save it to a JSON file if needed)
import json
print(json.dumps(data, indent=2))
