#!/usr/bin/env python3
"""Compile MLB major award winners from SABR/Lahman, attributing awards to franchises."""
import csv,io,json,urllib.request,collections
from pathlib import Path
BASE="https://raw.githubusercontent.com/corbtastik/lahman-baseball-db/main/"
ROOT=Path(__file__).resolve().parent
CATEGORIES={"Most Valuable Player":"mvp","Cy Young Award":"cy_young","Rookie of the Year":"rookie_of_the_year","Gold Glove":"gold_glove","Silver Slugger":"silver_slugger"}
SLUGS={"ARI":"arizona-diamondbacks","ATL":"atlanta-braves","BAL":"baltimore-orioles","BOS":"boston-red-sox","CHC":"chicago-cubs","CHW":"chicago-white-sox","CIN":"cincinnati-reds","CLE":"cleveland-guardians","COL":"colorado-rockies","DET":"detroit-tigers","HOU":"houston-astros","KCR":"kansas-city-royals","LAA":"los-angeles-angels","LAD":"los-angeles-dodgers","FLA":"miami-marlins","MIL":"milwaukee-brewers","MIN":"minnesota-twins","NYM":"new-york-mets","NYY":"new-york-yankees","OAK":"athletics","PHI":"philadelphia-phillies","PIT":"pittsburgh-pirates","SDP":"san-diego-padres","SFG":"san-francisco-giants","SEA":"seattle-mariners","STL":"st-louis-cardinals","TBD":"tampa-bay-rays","TEX":"texas-rangers","TOR":"toronto-blue-jays","WSN":"washington-nationals"}
def load(name):
    with urllib.request.urlopen(urllib.request.Request(BASE+name+".csv",headers={"User-Agent":"BetWiseHistoricalResearch/1.0"}),timeout=90) as r: return list(csv.DictReader(io.StringIO(r.read().decode("utf-8-sig"))))
def main():
    teams=load("Teams");awards=load("AwardsPlayers");people=load("People");appearances=load("Appearances")
    team_to_franchise={(int(t["yearID"]),t["teamID"]):t["franchID"] for t in teams}
    current={t["teamID"]:t["franchID"] for t in teams if t["yearID"]=="2025"}
    # 2025 Teams.csv IDs use historical Lahman shorthand; map via its stable retrospective abbreviation
    expected={"ARI":"ARI","ATL":"ATL","BAL":"BAL","BOS":"BOS","CHC":"CHN","CHW":"CHA","CIN":"CIN","CLE":"CLE","COL":"COL","DET":"DET","HOU":"HOU","KCR":"KCA","LAA":"LAA","LAD":"LAN","FLA":"MIA","MIL":"MIL","MIN":"MIN","NYM":"NYN","NYY":"NYA","OAK":"ATH","PHI":"PHI","PIT":"PIT","SDP":"SDN","SFG":"SFN","SEA":"SEA","STL":"SLN","TBD":"TBA","TEX":"TEX","TOR":"TOR","WSN":"WAS"}
    franchise_slug={current[v]:SLUGS[k] for k,v in expected.items()}
    assert len(franchise_slug)==30,(len(franchise_slug),current)
    names={p["playerID"]:" ".join(filter(None,[p.get("nameFirst"),p.get("nameLast")])) for p in people}
    appearances_by_player=collections.defaultdict(lambda:collections.Counter())
    for a in appearances:
        key=(int(a["yearID"]),a["playerID"])
        franchise=team_to_franchise.get((int(a["yearID"]),a["teamID"]))
        if franchise:
            appearances_by_player[key][franchise]+=int(a.get("G_all") or 0)
    output={slug:{k:[] for k in CATEGORIES.values()} for slug in SLUGS.values()}
    unresolved=[]
    for a in awards:
        cat=CATEGORIES.get(a["awardID"])
        if not cat:continue
        year=int(a["yearID"])
        if year>2025:continue
        counts=appearances_by_player.get((year,a["playerID"]),{})
        if not counts:
            unresolved.append({"year":year,"name":a["playerID"],"award":cat,"reason":"no_team_appearance"});continue
        highest=max(counts.values())
        leaders=[fid for fid,n in counts.items() if n==highest]
        # Award-year multi-franchise attribution needs manual evidence; never silently assign to largest split.
        if len(counts)>1 or len(leaders)!=1 or leaders[0] not in franchise_slug:
            unresolved.append({"year":year,"name":a["playerID"],"award":cat,"teams":dict(counts),"reason":"multiple_or_unsupported_franchises"});continue
        slug=franchise_slug[leaders[0]]
        output[slug][cat].append({"year":year,"player":names.get(a["playerID"],a["playerID"]),"league":a["lgID"],"position":a.get("notes") or None,"player_id":a["playerID"],"source":BASE+"AwardsPlayers.csv"})
    for team in output.values():
        for cat in team:team[cat].sort(key=lambda x:(x["year"],x["player"],str(x["position"])))
    result={"schema_version":1,"through":2025,"status":"partial_requires_crosscheck","source":"SABR Lahman Baseball Database 1871–2025","source_url":"https://sabr.org/lahman-database/","awards":output,"unresolved":unresolved}
    path=ROOT/"data/mlb/award-winners.json";path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n")
    print("Teams",len(output),"awards",sum(len(a) for team in output.values() for a in team.values()),"unresolved",len(unresolved))
    assert len(output)==30
if __name__=="__main__":main()
