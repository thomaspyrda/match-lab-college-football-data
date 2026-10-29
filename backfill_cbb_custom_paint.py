"""Read only linked official custom StatCrew archives missed by modern boxes."""
import runpy,sys
if __name__=='__main__':
 sys.argv.append('--custom-only')
 runpy.run_module('backfill_cbb_period_paint',run_name='__main__')
