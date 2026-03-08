"""Dump Naver Place HTML to file for inspection"""
import requests
from bs4 import BeautifulSoup
import json, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'https://m.place.naver.com/place/38673363',
}
place_id = '38673363'
r = requests.get(f'https://m.place.naver.com/place/{place_id}/review/visitor', headers=headers, timeout=8)
soup = BeautifulSoup(r.text, 'html.parser')

# Check for embedded JSON data
scripts = soup.find_all('script')
for s in scripts:
    content = s.string or ''
    if 'visitorReview' in content or 'reviewBody' in content or 'body' in content[:200]:
        print('[SCRIPT FOUND]', content[:300])
        break

# Find all text-bearing elements > 20 chars
print('\n--- Text Elements ---')
seen = set()
for el in soup.find_all(True):
    direct_text = ''.join(c for c in el.children if hasattr(c, '__str__') and not hasattr(c, 'children')).strip()
    if 20 < len(direct_text) < 300 and direct_text not in seen:
        cls = ' '.join(el.get('class', []))
        print(f'<{el.name} class="{cls[:30]}">{direct_text[:100]}')
        seen.add(direct_text)
    if len(seen) > 25:
        break

# Save raw HTML
with open('tmp_place_html.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
print('\nHTML saved to tmp_place_html.html')
print('Page size:', len(r.text), 'bytes')
