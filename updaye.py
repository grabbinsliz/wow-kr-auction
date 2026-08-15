import os
import json
import urllib.request
import statistics
from datetime import datetime, timezone

API_KEY = os.environ["TUE_API_KEY"]

# 우리가 추적할 WoW 재료
# 우선 테스트용 야행성 연꽃 하나.
# 작동 확인 후 한밤 약초/광석 전체를 여기에 추가하면 됨.
ITEMS = {
    236780: "야행성 연꽃",
}

BASE = "https://api.undermine.exchange/v1/region/kr/commodities"


def tue_get(url):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"ApiKey {API_KEY}",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def median_gold(rows, count=None):
    if count:
        rows = rows[-count:]

    values = [
        row["price"] / 10000
        for row in rows
        if row.get("price") is not None and row.get("price", 0) > 0
    ]

    if not values:
        return None

    return round(statistics.median(values), 4)


results = {}

for item_id, name in ITEMS.items():

    print(f"조회 중: {name} ({item_id})")

    # 현재 가격
    now_data = tue_get(
        f"{BASE}/{item_id}/now.json"
    )

    now = now_data.get("result", {})

    # 최근 약 14일 데이터
    hourly_data = tue_get(
        f"{BASE}/{item_id}/hourly.json"
    )

    hourly = hourly_data.get("result", {}).get("hourly", [])

    price_copper = now.get("price")

    results[str(item_id)] = {
        "name": name,
        "itemId": item_id,

        "currentGold":
            round(price_copper / 10000, 4)
            if price_copper is not None
            else None,

        "quantity": now.get("quantity"),

        "median24hGold":
            median_gold(hourly, 24),

        "median7dGold":
            median_gold(hourly, 24 * 7),

        "median14dGold":
            median_gold(hourly),

        "tueLastUpdated":
            now.get("lastUpdated"),

        "tueLastSeen":
            now.get("lastSeen"),
    }


output = {
    "source": "The Undermine Exchange",
    "region": "KR",

    "generatedAt":
        datetime.now(timezone.utc).isoformat(),

    "items": results,
}


os.makedirs("_site", exist_ok=True)

with open(
    "_site/prices.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2,
    )


# 브라우저에서 기본 주소를 열었을 때 보여줄 페이지
with open(
    "_site/index.html",
    "w",
    encoding="utf-8"
) as f:

    f.write("""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>WoW KR Auction API</title>
</head>

<body>
<h1>WoW KR Auction Price API</h1>

<p>Source: The Undermine Exchange</p>
<p>Region: KR</p>

<p>
<a href="prices.json">
prices.json
</a>
</p>

</body>
</html>
""")

print("prices.json 생성 완료")
