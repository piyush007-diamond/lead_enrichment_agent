
import requests
from bs4 import BeautifulSoup
import random

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def search_bing(query):
    try:
        url = f"https://www.bing.com/search?q={query}"
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Bing results are usually in <li class="b_algo"> <h2> <a href="...">
        for li in soup.find_all('li', class_='b_algo'):
            h2 = li.find('h2')
            if h2:
                a = h2.find('a')
                if a and 'href' in a.attrs:
                    link = a['href']
                    if not any(x in link for x in ['microsoft', 'bing', 'facebook', 'yelp']):
                        return link
    except Exception as e:
        print(f"Bing error: {e}")
    return None

def search_yahoo(query):
    try:
        url = f"https://search.yahoo.com/search?p={query}"
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Yahoo results in <div class="algo"> <h3 class="title"> <a href="...">
        for div in soup.find_all('div', class_='algo'):
            h3 = div.find('h3', class_='title')
            if h3:
                a = h3.find('a')
                if a and 'href' in a.attrs:
                    link = a['href']
                    if not any(x in link for x in ['yahoo', 'facebook', 'yelp']):
                        return link
    except Exception as e:
        print(f"Yahoo error: {e}")
    return None

query = "Arizona Biltmore Dentistry official site"
print(f"Testing search for: {query}")

print("Bing:", search_bing(query))
print("Yahoo:", search_yahoo(query))
