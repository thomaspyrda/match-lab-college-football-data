"""Complete the official archive search with classic SIDEARM HTML panels."""
import backfill_cbb_official_paint_legacy_batch as batch
from backfill_cbb_sidearm_html_paint import parse_html

classic=batch.classic
batch.classic=lambda body,school,team: parse_html(body,school,team) or classic(body,school,team)

if __name__=='__main__':batch.main()
