import urllib.request
import xml.etree.ElementTree as ET

url = "https://www.reddit.com/r/python/new.rss?limit=2"
req = urllib.request.Request(url, headers={'User-Agent': 'python:sandman.reddit2md:testing'})
with urllib.request.urlopen(req) as response:
    xml_data = response.read()

ns = {'atom': 'http://www.w3.org/2005/Atom'}
root = ET.fromstring(xml_data)
entries = root.findall('atom:entry', ns)

print("First batch:")
last_id = None
for entry in entries:
    id_text = entry.find('atom:id', ns).text
    print(id_text)
    last_id = id_text
    
print("---")
# Last ID is probably something like 't3_1hxxxx'.
# Let's try the next page
url_next = f"https://www.reddit.com/r/python/new.rss?limit=2&after={last_id}"
req2 = urllib.request.Request(url_next, headers={'User-Agent': 'python:sandman.reddit2md:testing'})
with urllib.request.urlopen(req2) as response:
    xml_data2 = response.read()

root2 = ET.fromstring(xml_data2)
entries2 = root2.findall('atom:entry', ns)
print("Second batch:")
for entry in entries2:
    id_text = entry.find('atom:id', ns).text
    print(id_text)

