"""Generate per-team gradients from the editable, sourced color registry."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
colors=json.loads((ROOT/'data/sports/team-colors.json').read_text())['teams']
css='''body.team-color-theme{background:radial-gradient(ellipse at 15% 0,color-mix(in srgb,var(--team-primary) 28%,transparent),transparent 65%),radial-gradient(ellipse at 95% 8%,color-mix(in srgb,var(--team-secondary) 17%,transparent),transparent 58%),#111!important}body.team-color-theme .team-hero,body.team-color-theme .team-research-heading{background:radial-gradient(ellipse at 100% 0,color-mix(in srgb,var(--team-secondary) 25%,transparent),transparent 70%),linear-gradient(120deg,#080808 0%,#111 48%,color-mix(in srgb,var(--team-primary) 48%,#111) 100%)!important;border-color:color-mix(in srgb,var(--team-primary) 65%,#555)!important}body.team-color-theme .team-research-heading{border-radius:18px}'''
js='''/* Team-page gradients only. Shared branding and semantic result colors remain intact. */
(() => {
 const themes=PALETTE;
 let path=location.pathname.replace(/\\/index\\.html$/,'/');
 if(!path.endsWith('.html')&&!path.endsWith('/'))path+='/';
 const theme=themes[path];
 if(!theme)return;
 if(!document.getElementById('teamSeasonData')&&!document.getElementById('team-season-data')&&!document.body.classList.contains('team-page'))return;
 if(!/^#[a-f0-9]{6}$/i.test(theme.primary)||!/^#[a-f0-9]{6}$/i.test(theme.secondary))return;
 document.body.style.setProperty('--team-primary',theme.primary);
 document.body.style.setProperty('--team-secondary',theme.secondary);
 document.body.classList.add('team-color-theme');
 const style=document.createElement('style');style.id='team-color-gradients';style.textContent=STYLES;document.head.appendChild(style);
})();
'''.replace('PALETTE',json.dumps(colors,separators=(',',':'))).replace('STYLES',json.dumps(css))
(ROOT/'sports-research/team-theme.js').write_text(js)
print(f'Generated gradients for {len(colors)} team pages')
