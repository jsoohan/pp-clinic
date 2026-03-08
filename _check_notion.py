import os, json, requests
from dotenv import load_dotenv
load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY","")
NOTION_LOG_DB_ID = os.getenv("NOTION_LOG_DB_ID","")
headers = {"Authorization": f"Bearer {NOTION_API_KEY}", "Notion-Version": "2022-06-28"}
r = requests.get(f"https://api.notion.com/v1/databases/{NOTION_LOG_DB_ID}", headers=headers, timeout=10)
if r.status_code == 200:
    d = r.json()
    title = d.get("title",[{}])[0].get("plain_text","")
    parent = d.get("parent",{})
    print("DB 제목:", title)
    print("Parent:", parent)
    for k,v in d.get("properties",{}).items():
        print(f"  컬럼: {repr(k):<30} 타입: {v['type']}")
else:
    print("오류:", r.status_code, r.text[:300])
