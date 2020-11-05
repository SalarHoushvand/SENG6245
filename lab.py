from bs4 import BeautifulSoup as soup
from urllib.request import urlopen as uReq

# html = open("http://127.0.0.1:5000/pre_quiz").read()
#soup = BeautifulSoup(html)
# print(soup)  # My home address



my_url = "http://127.0.0.1:5000/pre_quiz"

uClient = uReq(my_url)
page_html = uClient.read()
uClient.close()

page_soup = soup(page_html, "html.parser")
containers = page_soup.findAll("option")
for i in containers:
    print(i.text)