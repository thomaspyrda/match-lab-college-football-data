export function getPregameRecognitionAndStrength(lookup, season, week, team) {
  const row=lookup?.data?.[String(season)]?.[String(week)]?.[team];
  if(!row) return {available:false,ap:null,strength:null};
  return {available:true,ap:row.ap_rank==null?{ranked:false,rank:null}:{ranked:true,rank:row.ap_rank},strength:row.strength_score==null?null:{score:row.strength_score,tier:row.strength_tier,topPercent:row.top_percent}};
}
export function getGamePregameRecognitionAndStrength(lookup, gameId, team) {
  const row=lookup?.data?.[String(gameId)]?.[team];
  if(!row) return {available:false,ap:null,strength:null};
  return {available:true,ap:row.ap_rank==null?{ranked:false,rank:null}:{ranked:true,rank:row.ap_rank},strength:row.strength_score==null?null:{score:row.strength_score,tier:row.strength_tier,topPercent:row.top_percent}};
}
export function formatTeamStrength(s){return s?`${s.score}/100 · ${s.tier} · Top ${s.topPercent}%`:"Unavailable"}
