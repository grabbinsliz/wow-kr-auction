import os
import json
import urllib.request
import statistics

API_KEY = os.environ["TUE_API_KEY"]

# 추적할 WoW 재료
# 지금은 야행성 연꽃 테스트용
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
        if row.get("price") is not None
        and row.get("price", 0) > 0
    ]

    if not values:
        return None

    return round(statistics.median(values), 4)


results = {}
last_updates = []

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

    hourly = hourly_data.get("result", {}).get(
        "hourly",
        []
    )

    price_copper = now.get("price")

    last_updated = now.get("lastUpdated")

    if last_updated is not None:
        last_updates.append(last_updated)

    results[str(item_id)] = {
        "name": name,
        "itemId": item_id,

        "currentGold":
            round(price_copper / 10000, 4)
            if price_copper is not None
            else None,

        "quantity":
            now.get("quantity"),

        "median24hGold":
            median_gold(hourly, 24),

        "median7dGold":
            median_gold(hourly, 24 * 7),

        "median14dGold":
            median_gold(hourly),

        "tueLastUpdated":
            last_updated,

        "tueLastSeen":
            now.get("lastSeen"),
    }


output = {
    "source": "The Undermine Exchange",
    "region": "KR",

    # 실행 시간은 넣지 않음.
    # 가격 데이터가 실제로 바뀔 때만 GitHub에 새 커밋이 생기게 하기 위함.
    "latestTUEUpdate":
        max(last_updates)
        if last_updates
        else None,

    "items": results,
}


# -----------------------------------------
# 1. 저장소 최상단 prices.json
#    -> ChatGPT가 GitHub 연결로 직접 읽는 파일
# -----------------------------------------

with open(
    "prices.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2,
    )


# -----------------------------------------
# 2. GitHub Pages용
# -----------------------------------------

os.makedirs(
    "_site",
    exist_ok=True
)

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

<p>
Source:
The Undermine Exchange
</p>

<p>
Region:
KR
</p>

<p>
<a href="prices.json">
prices.json
</a>
</p>

</body>
</html>
""")


print("prices.json 생성 완료")
