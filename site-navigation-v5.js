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


/* Compact Underdog offer strip directly below each sport hero image. */
(() => {
  if (document.getElementById("underdog-hero-banner-style")) return;
  const style = document.createElement("style");
  style.id = "underdog-hero-banner-style";
  style.textContent = `
    .underdog-hero-banner{--ud-blue:#1aa6df;display:grid;grid-template-columns:88px minmax(0,1fr) auto auto;align-items:center;gap:14px;box-sizing:border-box;width:min(1180px,calc(100% - 32px));min-height:80px;margin:10px auto 0;padding:7px 14px;overflow:hidden;border:1px solid rgba(255,255,255,.24);border-radius:14px;background:repeating-radial-gradient(ellipse at 50% 0,transparent 0 16px,rgba(255,255,255,.075) 17px 19px,transparent 20px 34px),linear-gradient(105deg,#34b8eb,#169bd7);color:#071522;font-family:inherit;text-decoration:none;box-shadow:0 5px 18px rgba(0,0,0,.18)}
    .underdog-hero-banner:hover{filter:brightness(1.04)}
    .underdog-hero-banner:focus-visible{outline:3px solid #f6e923;outline-offset:3px}
    .underdog-hero-banner__image{display:block;width:88px;height:64px;object-fit:cover;object-position:center;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.2)}
    .underdog-hero-banner__copy{display:grid;min-width:0;gap:2px}
    .underdog-hero-banner__copy strong{font-size:11px;font-weight:900;line-height:1.1;letter-spacing:.09em;text-transform:uppercase}
    .underdog-hero-banner__copy span{font-size:clamp(18px,2.4vw,27px);font-weight:950;line-height:1.05;letter-spacing:-.025em;text-transform:uppercase;white-space:nowrap}
    .underdog-hero-banner__match{padding:8px 11px;border:1px solid rgba(5,41,61,.34);border-radius:999px;background:rgba(255,255,255,.18);font-size:11px;font-weight:900;letter-spacing:.04em;text-align:center;white-space:nowrap}
    .underdog-hero-banner__button{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 16px;border-radius:8px;background:#f6e923;color:#111!important;font-size:12px;font-weight:950;letter-spacing:.06em;text-decoration:none!important;white-space:nowrap}
    .underdog-hero-terms{box-sizing:border-box;width:min(1180px,calc(100% - 32px));margin:5px auto 22px;color:#aeb9b3;font-size:11px;line-height:1.45}
    @media(max-width:700px){.underdog-hero-banner{grid-template-columns:58px minmax(0,1fr) auto;gap:9px;width:calc(100% - 24px);min-height:68px;padding:5px 8px;border-radius:12px}.underdog-hero-banner__image{width:58px;height:56px;border-radius:7px}.underdog-hero-banner__copy strong{font-size:9px;letter-spacing:.05em}.underdog-hero-banner__copy span{font-size:clamp(14px,4.5vw,19px);white-space:normal}.underdog-hero-banner__match{display:none}.underdog-hero-banner__button{min-height:34px;padding:0 9px;font-size:10px}.underdog-hero-terms{width:calc(100% - 24px);margin:5px auto 18px;font-size:10px}}
    @media(max-width:360px){.underdog-hero-banner{grid-template-columns:48px minmax(0,1fr) auto;gap:7px}.underdog-hero-banner__image{width:48px;height:52px}.underdog-hero-banner__copy span{font-size:14px}.underdog-hero-banner__button{padding:0 7px;font-size:9px}}
  `;
  const selector = ".nfl-hero-image,.rank-hero,.cfb-hero-art,.hero-media";
  document.querySelectorAll(selector).forEach(hero => {
    if (!hero.querySelector("img") || hero.nextElementSibling?.classList.contains("underdog-hero-banner")) return;
    const banner = document.createElement("a");
    banner.className = "underdog-hero-banner";
    banner.href = "https://play.underdogsports.com/vgwg/hayhqoz9";
    banner.target = "_blank";
    banner.rel = "sponsored nofollow noopener noreferrer";
    banner.setAttribute("aria-label", "Sign up for Underdog: bonus pack worth up to $150 and a new-user 50% deposit match");
    banner.innerHTML = '<img class="underdog-hero-banner__image" src="https://matchlab.parlaycalculator.bet/assets/underdog-pack-strip.webp" alt="Underdog Sports Starter Pack"><span class="underdog-hero-banner__copy"><strong>Rip a bonus pack</strong><span>Up to $150 on us</span></span><span class="underdog-hero-banner__match">50% DEPOSIT MATCH</span><span class="underdog-hero-banner__button">SIGN UP <span aria-hidden="true">↗</span></span>';
    const terms = document.createElement("p");
    terms.className = "underdog-hero-terms";
    terms.innerHTML = "Sign up for Underdog with our link for a new-user 50% deposit match. Rip a bonus pack worth up to $150 on us! You&apos;re welcome. New users only; deposit and first entry required. Pack value varies and $150 is not guaranteed. Packs are not available in Nevada or Canada. Offer terms apply.";
    hero.insertAdjacentElement("afterend", banner);
    banner.insertAdjacentElement("afterend", terms);
  });
})();
