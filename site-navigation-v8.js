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


/* Underdog referral strip below each sports hero; expandable offer terms. */
(() => {
  const styleId = "underdog-hero-banner-style";
  if (!document.getElementById(styleId)) {
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = ".underdog-hero-banner{display:block;position:relative;container-type:inline-size;box-sizing:border-box;width:min(1194px,calc(100% - 32px));aspect-ratio:1194/98;margin:10px auto 0;padding:0;overflow:hidden;border:0;border-radius:999px;background-image:url(https://matchlab.parlaycalculator.bet/assets/underdog-original-blue-banner.jpg);background-size:108.0402% 183.6735%;background-position:50% 71.9512%;background-repeat:no-repeat;color:#fff;font-family:inherit;text-decoration:none}.underdog-hero-banner:hover{filter:brightness(1.04)}.underdog-hero-banner:focus-visible{outline:3px solid #f6e923;outline-offset:3px}.underdog-hero-banner__copy{position:absolute;inset:2% 18.5%;display:flex;align-items:center;justify-content:center;min-width:0;color:#fff;background-image:url(https://matchlab.parlaycalculator.bet/assets/underdog-original-blue-banner.jpg);background-size:171.5% 1000%;background-position:50% 40%;text-align:center;font-size:clamp(6px,2.2cqw,27px);font-weight:900;line-height:1;letter-spacing:-.025em;white-space:nowrap}.underdog-hero-terms{box-sizing:border-box;width:min(1194px,calc(100% - 32px));margin:6px auto 22px;color:#aeb9b3;font-family:inherit;font-size:12px;line-height:1.45}\n.underdog-hero-terms summary{display:inline-flex;align-items:center;min-height:30px;padding:0 13px;border:1px solid rgba(255,255,255,.27);border-radius:999px;color:#e8ece9;font-size:11px;font-weight:700;cursor:pointer;list-style:none}\n.underdog-hero-terms summary::-webkit-details-marker{display:none}\n.underdog-hero-terms summary:after{content:\"+\";margin-left:7px;font-size:15px;line-height:1}\n.underdog-hero-terms[open] summary:after{content:\"\u2212\"}\n.underdog-hero-terms__copy{max-width:900px;margin:7px 0 0;color:#aeb9b3;font-size:11px;line-height:1.5}\n@media(max-width:700px){.underdog-hero-banner{width:calc(100% - 24px);margin-top:8px}.underdog-hero-terms{width:calc(100% - 24px);margin:5px auto 18px}.underdog-hero-terms__copy{font-size:10px}}";
    document.head.appendChild(style);
  }
  const selector = ".nfl-hero-image,.rank-hero,.cfb-hero-art,.hero-media";
  document.querySelectorAll(selector).forEach(hero => {
    if (!hero.querySelector("img") || hero.nextElementSibling?.classList.contains("underdog-hero-banner")) return;
    const banner = document.createElement("a");
    banner.className = "underdog-hero-banner";
    banner.href = "https://play.underdogsports.com/vgwg/hayhqoz9";
    banner.target = "_blank";
    banner.rel = "sponsored nofollow noopener noreferrer";
    banner.setAttribute("aria-label", "$50 BONUS + A RIPS PACK WORTH UP TO $150");
    banner.innerHTML = "<span class=\"underdog-hero-banner__copy\">$50 BONUS + A RIPS PACK WORTH UP TO $150</span>";
    const terms = document.createElement("details");
    terms.className = "underdog-hero-terms";
    terms.innerHTML = "<summary>Terms</summary><p class=\"underdog-hero-terms__copy\">This is an offer for Underdog. Sign up through our link. New users are eligible for a 50% deposit match. After a qualifying first entry, the referral offer includes $50 in bonus funds and a Sports Starter Pack for you and your friend. Pack maximum value is $150 and is not guaranteed; view pack odds in Rips. A deposit and first entry are required for rewards. Packs are unavailable in Nevada and Canada. Eligibility and full offer terms apply. You are welcome.</p>";
    hero.insertAdjacentElement("afterend", banner);
    banner.insertAdjacentElement("afterend", terms);
  });
})();