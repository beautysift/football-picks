import requests
import json
import os
from datetime import datetime, timezone

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY")
MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID")

def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }
    r = requests.get(url, params=params)
    return r.json()

def prepare_match_summary(match):
    bookmakers = match.get("bookmakers", [])
    if not bookmakers:
        return None
    home = match["home_team"]
    away = match["away_team"]
    league = match.get("sport_title", "")
    commence = match.get("commence_time", "")
    odds_list = {"home": [], "draw": [], "away": [], "over": [], "under": []}
    for bm in bookmakers:
        for market in bm.get("markets", []):
            if market["key"] == "h2h":
                for o in market["outcomes"]:
                    if o["name"] == home: odds_list["home"].append(o["price"])
                    elif o["name"] == away: odds_list["away"].append(o["price"])
                    elif o["name"] == "Draw": odds_list["draw"].append(o["price"])
            elif market["key"] == "totals":
                for o in market["outcomes"]:
                    if o["name"] == "Over": odds_list["over"].append(o["price"])
                    elif o["name"] == "Under": odds_list["under"].append(o["price"])
    def avg(lst): return round(sum(lst)/len(lst),2) if lst else None
    return {"id": match["id"], "home": home, "away": away, "league": league, "commence": commence,
            "odds": {"home": avg(odds_list["home"]), "draw": avg(odds_list["draw"]), "away": avg(odds_list["away"]), "over25": avg(odds_list["over"]), "under25": avg(odds_list["under"])},
            "bookmaker_count": len(bookmakers)}

def analyze_with_minimax(matches_data):
    url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    headers = {"Authorization": f"Bearer {MINIMAX_API_KEY}", "Content-Type": "application/json"}
    matches_text = json.dumps(matches_data, ensure_ascii=False, indent=2)
    payload = {"model": "abab6.5s-chat", "messages": [
        {"role": "system", "content": "แกคือเด็กสตรีทนักวิเคราะห์ พูดสั้น กระแทก ตรงประเด็น สไตล์ วัย ลุี โคตรพถลิงแทว่ารัปบุณบนำเดิมพันงาน ใช้คำว่า ค้ืบระเฤ็น JSON เท่านั้น ห้าม markdown ห้าม backtick"},
        {"role": "user", "content": f"ข้อมูล odds วี่น:{matches_text}แรั่กปร 3 ค่ป ตอบเป็น JSON array: [{\"home\":\"ชื่อทีมเหย้૲า\",\"away\":\"ชื่อวตีมเฮืกดั\",\"league\":\"ชื่อลีก\",\"commence\":\"เวลาแข่ง\",\"home_win_pct\":55,\"draw_pct\":25,\"away_win_pct\":20,\"bet\":\"สิ่งที่แนะนำเดิมพัน\",\"odds_target\":1.85,\"confidence\":\"high\",\"analysis\":\"วิเคราะห์\",\"odds_home\":1.75,\"odds_draw\":3.20,\"odds_away\":4.50}]"}
    ], "max_tokens": 1500}
    r = requests.post(url, headers=headers, json=payload)
    data = r.json()
    text = ""
    for block in data.get("choices",[{}])[0].get("message",{}).get("content",[]):
        if isinstance(block, dict): text += block.get("text","")
        elif isinstance(block, str): text += block
    return json.loads(text.strip().replace("```json","").replace("```","").strip())

def main():
    print("กำลังดึงข้อมูล odds...")
    raw = fetch_odds()
    matches = [s for m in raw if (s := prepare_match_summary(m)) and s["odds"]["home"]]
    print(f"เจอ {len(matches)} แมตช์")
    if len(matches) < 3:
        print("แมตช์ไม่พอ")
        return
    top = sorted(matches, key=lambda x: x["bookmaker_count"], reverse=True)[:15]
    print("กำลังวิเคราะ...")
    picks = analyze_with_minimax(top)
    output = {"date": datetime.now(timezone.utc).strftime("%d/%m/%Y"), "updated_at": datetime.now(timezone.utc).isoformat(), "picks": picks}
    os.makedirs("web", exist_ok=True)
    with open("web/picks.json", "w", encoding="utf-8") as f: json.dump(output, f, ensure_ascii=False, indent=2)
    print("เขอน ที่!")
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
