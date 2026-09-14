export function getPregameRecognitionAndStrength(lookup, season, week, team) {
  const row = lookup?.data?.[String(season)]?.[String(week)]?.[team];
  if (!row) return { available: false, ap: null, elo: null };
  return {
    available: true,
    ap: row.ap_rank == null
      ? { ranked: false, rank: null }
      : { ranked: true, rank: row.ap_rank },
    elo: row.elo_rating == null
      ? null
      : { rating: row.elo_rating, rank: row.elo_rank, field: row.fbs_field_size },
  };
}

export function getGamePregameRecognitionAndStrength(gameLookup, gameId, team) {
  const row = gameLookup?.data?.[String(gameId)]?.[team];
  if (!row) return { available: false, ap: null, elo: null };
  return {
    available: true,
    ap: row.ap_rank == null
      ? { ranked: false, rank: null }
      : { ranked: true, rank: row.ap_rank },
    elo: row.pregame_elo == null
      ? null
      : { rating: row.pregame_elo, rank: row.pregame_elo_rank, field: row.fbs_field_size },
  };
}
