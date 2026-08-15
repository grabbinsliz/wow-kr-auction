import os
import json
import gzip
import urllib.request
import urllib.error
import statistics

API_KEY = os.environ["TUE_API_KEY"]
BASE = "https://api.undermine.exchange/v1/region/kr/commodities"
TOKEN_URL = "https://data.wowtoken.app/v2/current/retail.json"

# Midnight 약초/채광으로 직접 얻거나 함께 획득하는 거래 가능 재료.
# quality: 1/2 = 재료 품질, None = 품질 구분 없음.
ITEMS = [
    # Herbalism
    {"id": 236761, "name": "Tranquility Bloom", "category": "herb", "quality": 1},
    {"id": 236767, "name": "Tranquility Bloom", "category": "herb", "quality": 2},
    {"id": 236770, "name": "Sanguithorn", "category": "herb", "quality": 1},
    {"id": 236771, "name": "Sanguithorn", "category": "herb", "quality": 2},
    {"id": 236774, "name": "Azeroot", "category": "herb", "quality": 1},
    {"id": 236775, "name": "Azeroot", "category": "herb", "quality": 2},
    {"id": 236776, "name": "Argentleaf", "category": "herb", "quality": 1},
    {"id": 236777, "name": "Argentleaf", "category": "herb", "quality": 2},
    {"id": 236778, "name": "Mana Lily", "category": "herb", "quality": 1},
    {"id": 236779, "name": "Mana Lily", "category": "herb", "quality": 2},
    {"id": 236780, "name": "Nocturnal Lotus", "category": "herb_rare", "quality": None},

    # Mining
    {"id": 237359, "name": "Refulgent Copper Ore", "category": "ore", "quality": 1},
    {"id": 237361, "name": "Refulgent Copper Ore", "category": "ore", "quality": 2},
    {"id": 237362, "name": "Umbral Tin Ore", "category": "ore", "quality": 1},
    {"id": 237363, "name": "Umbral Tin Ore", "category": "ore", "quality": 2},
    {"id": 237364, "name": "Brilliant Silver Ore", "category": "ore", "quality": 1},
    {"id": 237365, "name": "Brilliant Silver Ore", "category": "ore", "quality": 2},
    {"id": 237366, "name": "Dazzling Thorium", "category": "ore_rare", "quality": None},

    # Infused/themed node side-gathers (약초/채광 공통)
    {"id": 236949, "name": "Mote of Light", "category": "mote", "quality": None},
    {"id": 236950, "name": "Mote of Primal Energy", "category": "mote", "quality": None},
    {"id": 236951, "name": "Mote of Wild Magic", "category": "mote", "quality": None},
    {"id": 236952, "name": "Mote of Pure Void", "category": "mote", "quality": None},

    # Patch 12.1 / Season 2 Coiled Isle
    {"id": 274777, "name": "Neutralized Venom Clot", "category": "season2", "quality": None},
    {"id": 274781, "name": "Cursebound Globe", "category": "season2", "quality": None},
]


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def tue_get(url):
    return get_json(
        url,
        {
            "Authorization": f"ApiKey {API_KEY}",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        },
    )


def median_gold(rows, count=None):
    if count:
        rows = rows[-count:]
    values = [
        row["price"] / 10000
        for row in rows
        if row.get("price") is not None and row.get("price", 0) > 0
    ]
    return round(statistics.median(values), 4) if values else None


def pct_vs(current, reference):
    if current is None or reference in (None, 0):
        return None
    return round((current / reference - 1) * 100, 2)


def fetch_item(meta):
    item_id = meta["id"]
    name = meta["name"]
    print(f"조회 중: {name} ({item_id})")

    try:
        now_data = tue_get(f"{BASE}/{item_id}/now.json")
        now = now_data.get("result", {}) or {}
    except Exception as e:
        print(f"  현재가 오류: {name} ({item_id}) - {e}")
        now = {}

    try:
        hourly_data = tue_get(f"{BASE}/{item_id}/hourly.json")
        hourly = (hourly_data.get("result", {}) or {}).get("hourly", []) or []
    except Exception as e:
        print(f"  추이 오류: {name} ({item_id}) - {e}")
        hourly = []

    price_copper = now.get("price")
    current_gold = round(price_copper / 10000, 4) if price_copper is not None else None
    m24 = median_gold(hourly, 24)
    m7 = median_gold(hourly, 24 * 7)
    m14 = median_gold(hourly)

    return {
        "name": name,
        "itemId": item_id,
        "category": meta["category"],
        "quality": meta["quality"],
        "currentGold": current_gold,
        "quantity": now.get("quantity"),
        "median24hGold": m24,
        "median7dGold": m7,
        "median14dGold": m14,
        "vs24hPct": pct_vs(current_gold, m24),
        "vs7dPct": pct_vs(current_gold, m7),
        "vs14dPct": pct_vs(current_gold, m14),
        "tueLastUpdated": now.get("lastUpdated"),
        "tueLastSeen": now.get("lastSeen"),
    }


def fetch_wow_token():
    # wowtoken.app는 Blizzard 공식 토큰 API를 이용해 지역별 값을 제공한다.
    try:
        data = get_json(TOKEN_URL)
        kr = data.get("kr")
        if not kr or len(kr) < 2:
            raise ValueError("KR token data missing")
        return {
            "region": "KR",
            "game": "retail",
            "priceGold": int(kr[1]),
            "updatedAt": kr[0],
            "source": "wowtoken.app (Blizzard API)",
        }
    except Exception as e:
        print(f"WoW 토큰 조회 오류: {e}")
        return {
            "region": "KR",
            "game": "retail",
            "priceGold": None,
            "updatedAt": None,
            "source": "wowtoken.app (Blizzard API)",
            "error": str(e),
        }


results = {}
last_updates = []

for meta in ITEMS:
    item = fetch_item(meta)
    results[str(meta["id"])] = item
    if item.get("tueLastUpdated") is not None:
        last_updates.append(item["tueLastUpdated"])

categories = {}
for meta in ITEMS:
    categories.setdefault(meta["category"], []).append(meta["id"])

output = {
    "source": "The Undermine Exchange",
    "region": "KR",
    "latestTUEUpdate": max(last_updates) if last_updates else None,
    "categories": categories,
    "items": results,
    "wowToken": fetch_wow_token(),
}

with open("prices.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

os.makedirs("_site", exist_ok=True)
with open("_site/prices.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

with open("_site/index.html", "w", encoding="utf-8") as f:
    f.write("""
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>WoW KR Auction API</title></head>
<body><h1>WoW KR Auction Price API</h1><p>Source: The Undermine Exchange</p>
<p>Region: KR</p><p><a href="prices.json">prices.json</a></p></body></html>
""")

print(f"prices.json 생성 완료 - 재료 {len(ITEMS)}개 + KR WoW Token")
