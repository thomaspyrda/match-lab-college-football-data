/* Shared sport navigation. Native details support touch and keyboard toggling. */
(() => {
  const sportPath = location.pathname.split("/")[1].toUpperCase();
  const site = location.hostname.startsWith("nfl.") ? "NFL" : (["MLB", "NBA", "CBB"].includes(sportPath) ? sportPath : "CFB");
  const sports = {
    MLB: [["MLB Dashboard", "https://matchlab.parlaycalculator.bet/mlb/dashboard/"], ["MLB Teams", "https://matchlab.parlaycalculator.bet/mlb/teams/"]],
    CBB: [["CBB Dashboard", "https://matchlab.parlaycalculator.bet/cbb/dashboard/"], ["CBB Teams", "https://matchlab.parlaycalculator.bet/cbb/teams/"]],
    NFL: [["NFL Dashboard", "https://nfl.parlaycalculator.bet/"], ["NFL Teams", "https://nfl.parlaycalculator.bet/teams.html"], ["Rankings", "https://nfl.parlaycalculator.bet/nfl-team-strength-rankings/"]],
    NBA: [["NBA Dashboard", "https://matchlab.parlaycalculator.bet/nba/dashboard/"], ["NBA Teams", "https://matchlab.parlaycalculator.bet/nba/teams/"], ["Rankings", "https://matchlab.parlaycalculator.bet/nba/rankings/"]],
    CFB: [["CFB Dashboard", "https://matchlab.parlaycalculator.bet/cfb-dashboard-preview/"], ["CFB Teams", "https://matchlab.parlaycalculator.bet/teams.html"], ["CFB Match Lab", "https://matchlab.parlaycalculator.bet/"], ["Rankings", "https://matchlab.parlaycalculator.bet/college-football-team-strength-rankings/"]]
  };
  const menu = label => `<details class="sport-menu${site===label?' active-sport':''}"><summary>${label}<span aria-hidden="true">⌄</span></summary><div class="sport-dropdown">${sports[label].map(([text,url]) => `<a href="${url}">${text}</a>`).join("")}</div></details>`;
  const links = `<a href="https://parlaycalculator.bet/betwise/">Why BetWise?</a>${menu("NFL")}${menu("CFB")}${menu("MLB")}${menu("NBA")}${menu("CBB")}<a href="https://parlaycalculator.bet/#calculator">Parlay Calculator</a><a href="https://parlaycalculator.bet/resources/">All Resources</a>`;
  document.querySelectorAll('.site-nav, .mobile-menu > nav').forEach(nav => {
    nav.innerHTML = links;
    nav.querySelectorAll('a').forEach(link => {
      const url = new URL(link.href);
      if (url.origin===location.origin && url.pathname.replace(/\/$/,'')===location.pathname.replace(/\/$/,'')) {
        link.classList.add('active'); link.setAttribute('aria-current','page');
      }
    });
    nav.querySelectorAll('a').forEach(link => {
      const url = new URL(link.href);
      if (url.origin === location.origin && ['MLB', 'NBA', 'CBB'].includes(site) && location.pathname.startsWith(`/${site.toLowerCase()}/teams/`) && url.pathname === `/${site.toLowerCase()}/teams/`) link.classList.add('active');
    });
    nav.querySelectorAll('.sport-menu').forEach(details => details.addEventListener('toggle', () => {
      if (details.open) nav.querySelectorAll('.sport-menu').forEach(other => { if (other!==details) other.open=false; });
    }));
  });
  document.addEventListener('click', event => {
    document.querySelectorAll('.sport-menu[open]').forEach(menu => { if (!menu.contains(event.target)) menu.open=false; });
    document.querySelectorAll('.mobile-menu[open]').forEach(menu => { if (!menu.contains(event.target)) menu.open=false; });
  });
  document.addEventListener('keydown', event => {
    if (event.key!=="Escape") return;
    const open = [...document.querySelectorAll('.sport-menu[open], .mobile-menu[open]')];
    const focused = open.find(menu => menu.contains(document.activeElement));
    open.forEach(menu => menu.open=false);
    focused?.querySelector('summary')?.focus();
  });
})();


/* Match each individual archive to its own team-color gradient. */
(() => {
  const individual=document.body.classList.contains("team-page")||document.getElementById("team-season-data")||document.getElementById("teamSeasonData");
  if(!individual||document.getElementById("team-color-script"))return;
  const script=document.createElement("script");script.id="team-color-script";script.src="https://matchlab.parlaycalculator.bet/sports-research/team-theme.js?v=1";document.head.appendChild(script);
})();


/* Underdog promotional banner directly below each sport hero image. */
(() => {
  const styleId="underdog-hero-banner-style";
  if (!document.getElementById(styleId)) {
    const style=document.createElement("style");
    style.id=styleId;
    style.textContent=`
      .underdog-hero-banner{--ud-cyan:#25b9ef;--ud-yellow:#f5e21b;position:relative;isolation:isolate;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:18px;max-width:1180px;margin:14px auto 28px;padding:clamp(18px,3vw,28px) clamp(18px,3.5vw,34px);overflow:hidden;border:1px solid rgba(37,185,239,.72);border-radius:18px;background:radial-gradient(ellipse at 92% 8%,rgba(245,226,27,.16),transparent 28%),linear-gradient(112deg,#13394a,#111d2b 70%,#142d3e);color:#f8fbff;box-shadow:0 12px 34px rgba(0,0,0,.28);font-family:inherit}
      .underdog-hero-banner:before{content:"";position:absolute;z-index:-1;inset:0;background:repeating-linear-gradient(165deg,transparent 0 26px,rgba(37,185,239,.055) 27px 32px)}
      .underdog-hero-banner__copy{min-width:0}
      .underdog-hero-banner__label{display:inline-block;margin:0 0 8px;padding:5px 9px;border-radius:999px;background:rgba(37,185,239,.14);color:#73d9ff;font-size:10px;font-weight:900;letter-spacing:.13em;text-transform:uppercase}
      .underdog-hero-banner h2{margin:0 0 7px;color:var(--ud-yellow);font-size:clamp(21px,3vw,32px);font-weight:900;line-height:1.08;letter-spacing:-.025em}
      .underdog-hero-banner__message{margin:0;color:#f4f7fb;font-size:clamp(14px,1.6vw,17px);line-height:1.45}
      .underdog-hero-banner__button{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:13px 21px;border:0;border-radius:10px;background:var(--ud-yellow);color:#101622!important;font-size:14px;font-weight:900;text-align:center;text-decoration:none!important;white-space:nowrap;box-shadow:0 5px 18px rgba(0,0,0,.2);transition:transform .15s ease,filter .15s ease}
      .underdog-hero-banner__button:hover,.underdog-hero-banner__button:focus-visible{filter:brightness(1.06);transform:translateY(-1px)}
      .underdog-hero-banner__terms{grid-column:1/-1;margin:0;color:#d1dbe4;font-size:11px;line-height:1.45}
      @media(max-width:620px){.underdog-hero-banner{grid-template-columns:1fr;gap:12px;margin:10px auto 22px;padding:18px 16px;border-radius:14px}.underdog-hero-banner h2{font-size:23px}.underdog-hero-banner__button{width:100%;min-height:46px}.underdog-hero-banner__terms{font-size:10px}}
    `;
    document.head.appendChild(style);
  }
  const selector=".nfl-hero-image,.rank-hero,.cfb-hero-art,.hero-media";
  document.querySelectorAll(selector).forEach(hero=>{
    if(!hero.querySelector("img")||hero.nextElementSibling?.classList.contains("underdog-hero-banner"))return;
    const banner=document.createElement("aside");
    banner.className="underdog-hero-banner";
    banner.setAttribute("aria-label","Sponsored Underdog offer");
    banner.innerHTML='<div class="underdog-hero-banner__copy"><p class="underdog-hero-banner__label">Sponsored offer · Underdog</p><h2>Rip a bonus pack worth up to $150 on us!</h2><p class="underdog-hero-banner__message">Sign up for Underdog with our link, new user 50% deposit match included. You\'re welcome.</p></div><a class="underdog-hero-banner__button" href="https://play.underdogsports.com/vgwg/hayhqoz9" target="_blank" rel="sponsored nofollow noopener noreferrer">Claim your offer <span aria-hidden="true">&nbsp;↗</span></a><p class="underdog-hero-banner__terms">New users only. Deposit and first entry required. Pack maximum value is not guaranteed. Not available in Nevada or Canada. Offer terms apply.</p>';
    hero.insertAdjacentElement("afterend",banner);
  });
})();
