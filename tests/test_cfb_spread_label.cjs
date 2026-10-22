const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'cfb-dashboard-preview/app.js'),'utf8');
const expression=source.match(/^const spreadLabel=(.*);$/m)[1];
const label=new Function('abbr','return '+expression)(team=>team.abbr||team.name);
const game=spread=>({away:{abbr:'IU'},home:{abbr:'MICH'},market:{spread}});
test('away favorite carries its own negative spread',()=>assert.equal(label(game(7)),'IU -7'));
test('home favorite retains its negative spread',()=>assert.equal(label(game(-7.5)),'MICH -7.5'));
test('pickem and unavailable lines are not labeled as favorites',()=>{
 assert.equal(label(game(0)),'PK');
 for(const value of [null,undefined,'','unavailable'])assert.equal(label(game(value)),'—');
});
test('all published slate labels agree with the moneyline favorite',()=>{
 const {games}=JSON.parse(fs.readFileSync(path.join(root,'cfb-dashboard-preview/data/dashboard.json'),'utf8'));
 let checked=0;
 for(const g of games){
  const m=g.market||{},h=m.home_moneyline,a=m.away_moneyline;
  if(m.spread==null||m.spread===0||h==null||a==null||h===a)continue;
  const favorite=h<a?g.home:g.away;
  assert.equal(label(g),`${favorite.abbr||favorite.name} -${Math.abs(m.spread)}`,g.game_id);
  checked++;
 }
 assert.ok(checked>0);
 console.log(`Checked ${checked} published spreads against moneyline favorites`);
});
