import requests
import json
import os
from datetime import datetime, timezone

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds"
    params = {"apiKey": ODDS_API_KEY, "regions": "eu", "markets": "h2h,totals", "oddsFormat": "decimal", "dateFormat": "iso"}
    r = requests.get(url, params=params)
    data = r.json()
    print("API status:", r.status_code)
    if isinstance(data, dict):
        print("API error:", json.dumps(data))
        return []
    print("Got", len(data), "matches")
    return data

def prepare_match(match):
    if not isinstance(match, dict): return None
    bookmakers = match.get("bookmakers", [])
    if not bookmakers: return None
    home = match["home_team"]
    away = match["away_team"]
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
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    return {"id": match["id"], "home": home, "away": away,
            "league": match.get("sport_title", ""), "commence": match.get("commence_time", ""),
            "odds_home": avg(odds_list["home"]), "odds_draw": avg(odds_list["draw"]),
            "odds_away": avg(odds_list["away"]), "odds_over25": avg(odds_list["over"]),
            "odds_under25": avg(odds_list["under"]), "bookmaker_count": len(bookmakers)}

def calc_value_score(odds, bookmaker_count):
    """
    คำนวณ value score จริงๆ จาก:
    - implied probability จาก odds
    - margin ของ bookmaker (overround)
    - จำนวน bookmaker ที่เห็นด้วย
    - sweet spot ของ odds (ไม่สูงหรือต่ำเกิน)
    """
    if not odds or odds <= 1.0: return 0
    # Implied probability
    impl_prob = 1 / odds
    # Sweet spot: odds 1.6-2.8 ดีที่สุด
    if odds < 1.4 or odds > 4.0: return 0
    sweet = 1.0
    if odds < 1.6: sweet = 0.6
    elif odds < 1.8: sweet = 0.8
    elif odds <= 2.5: sweet = 1.0
    elif odds <= 3.0: sweet = 0.85
    else: sweet = 0.7
    # Bookmaker confidence: ยิ่งเยอะยิ่งดี
    bm_score = min(bookmaker_count / 10, 1.0)
    # Final score 0-100
    score = round(impl_prob * sweet * bm_score * 100, 1)
    return score

def pick_best_bet(m):
    bm = m["bookmaker_count"]
    candidates = []
    # Home win
    if m["odds_home"]:
        s = calc_value_score(m["odds_home"], bm)
        if s > 0:
            candidates.append({"bet": m["home"] + " ชนะ", "odds_target": m["odds_home"],
                "score": s, "type": "home"})
    # Away win
    if m["odds_away"]:
        s = calc_value_score(m["odds_away"], bm)
        if s > 0:
            candidates.append({"bet": m["away"] + " ชนะ", "odds_target": m["odds_away"],
                "score": s, "type": "away"})
    # Over 2.5
    if m["odds_over25"]:
        s = calc_value_score(m["odds_over25"], bm)
        if s > 0:
            candidates.append({"bet": "Over 2.5 ประตู", "odds_target": m["odds_over25"],
                "score": s, "type": "over"})
    if not candidates: return None
    best = max(candidates, key=lambda x: x["score"])
    # คำนวณ win prob จาก odds
    best["home_win_pct"] = round(1/m["odds_home"]*100) if m["odds_home"] else 0
    best["draw_pct"] = round(1/m["odds_draw"]*100) if m["odds_draw"] else 0
    best["away_win_pct"] = round(1/m["odds_away"]*100) if m["odds_away"] else 0
    return best

def confidence_label(score):
    if score >= 45: return "high"
    if score >= 30: return "medium"
    return "low"

def analysis_text(m, bet):
    score = bet["score"]
    bm = m["bookmaker_count"]
    odds = bet["odds_target"]
    impl = round(100/odds)
    if score >= 45:
        tone = f"โคตรเข้าเว้ย! value score {score} คะแนน"
    elif score >= 30:
        tone = f"น่าเล่นอ่ะ value score {score} คะแนน"
    else:
        tone = f"ลองดู value score {score} คะแนน"
    return f"{tone} · {bm} เจ้ามั่นใจ · implied prob {impl}% · odds {odds}"

def main():
    print("Fetching odds...")
    raw = fetch_odds()
    if not raw: return
    matches = [s for m in raw if (s := prepare_match(m)) and s["odds_home"]]
    print("Valid matches:", len(matches))
    top = sorted(matches, key=lambda x: x["bookmaker_count"], reverse=True)[:20]
    scored = [(m, b) for m in top if (b := pick_best_bet(m))]
    if len(scored) < 3:
        scored = [(m, {"bet": m["home"]+" ชนะ", "odds_target": m["odds_home"],
            "score": calc_value_score(m["odds_home"], m["bookmaker_count"]),
            "home_win_pct": round(1/m["odds_home"]*100) if m["odds_home"] else 0,
            "draw_pct": round(1/m["odds_draw"]*100) if m["odds_draw"] else 0,
            "away_win_pct": round(1/m["odds_away"]*100) if m["odds_away"] else 0}) for m in top[:3]]
    scored.sort(key=lambda x: x[1]["score"], reverse=True)
    picks = []
    for m, bet in scored[:3]:
        picks.append({
            "home": m["home"], "away": m["away"],
            "league": m["league"], "commence": m["commence"],
            "home_win_pct": bet["home_win_pct"],
            "draw_pct": bet["draw_pct"],
            "away_win_pct": bet["away_win_pct"],
            "bet": bet["bet"],
            "odds_target": bet["odds_target"],
            "value_score": bet["score"],
            "confidence": confidence_label(bet["score"]),
            "analysis": analysis_text(m, bet),
            "odds_home": m["odds_home"],
            "odds_draw": m["odds_draw"],
            "odds_away": m["odds_away"],
        })
    output = {"date": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
              "updated_at": datetime.now(timezone.utc).isoformat(), "picks": picks}
    os.makedirs("web", exist_ok=True)
    with open("web/picks.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\nDone! 3 picks:")
    for p in picks:
        print(f"  {p['home']} vs {p['away']} → {p['bet']} @ {p['odds_target']} [score:{p['value_score']}]")

if __name__ == "__main__":
    main()
