import dblp

authors = dblp.search('Jimmy Lin')

jimmy = authors[0]

# print (len(jimmy.publications))
print(jimmy.publications[0].title)
print(jimmy.publications[0])