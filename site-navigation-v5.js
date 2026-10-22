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
    style.textContent = `
      .underdog-hero-banner{display:grid;grid-template-columns:112px minmax(0,1fr);align-items:center;gap:20px;box-sizing:border-box;width:min(1194px,calc(100% - 32px));height:96px;margin:10px auto 0;padding:6px 14px;overflow:hidden;border:1px solid rgba(255,255,255,.25);border-radius:20px;background:repeating-radial-gradient(ellipse at 50% 0,transparent 0 16px,rgba(255,255,255,.08) 17px 19px,transparent 20px 34px),linear-gradient(105deg,#31b7e9,#169bd7);color:#071522;font-family:inherit;text-decoration:none;box-shadow:0 3px 12px rgba(0,0,0,.15)}
      .underdog-hero-banner:hover{filter:brightness(1.04)}
      .underdog-hero-banner:focus-visible{outline:3px solid #f6e923;outline-offset:3px}
      .underdog-hero-banner__image{display:block;width:112px;height:82px;object-fit:cover;object-position:center 24%;border-radius:13px;box-shadow:0 2px 8px rgba(0,0,0,.22)}
      .underdog-hero-banner__copy{display:flex;align-items:baseline;gap:8px;min-width:0;font-size:clamp(20px,2.5vw,32px);font-weight:900;line-height:1.08;letter-spacing:-.025em}
      .underdog-hero-banner__brand{flex:none;font-size:.78em;font-weight:950;letter-spacing:.015em}
      .underdog-hero-banner__offer{color:#fff;white-space:nowrap}
      .underdog-hero-banner__offer em{color:#fff127;font-style:normal}
      .underdog-hero-terms{box-sizing:border-box;width:min(1194px,calc(100% - 32px));margin:6px auto 22px;color:#aeb9b3;font-family:inherit;font-size:12px;line-height:1.45}
      .underdog-hero-terms summary{display:inline-flex;align-items:center;min-height:30px;padding:0 13px;border:1px solid rgba(255,255,255,.27);border-radius:999px;color:#e8ece9;font-size:11px;font-weight:700;cursor:pointer;list-style:none}
      .underdog-hero-terms summary::-webkit-details-marker{display:none}
      .underdog-hero-terms summary:after{content:"+";margin-left:7px;font-size:15px;line-height:1}
      .underdog-hero-terms[open] summary:after{content:"−"}
      .underdog-hero-terms__copy{max-width:900px;margin:7px 0 0;color:#aeb9b3;font-size:11px;line-height:1.5}
      @media(max-width:700px){.underdog-hero-banner{grid-template-columns:84px minmax(0,1fr);gap:11px;width:calc(100% - 24px);height:76px;margin-top:8px;padding:5px 8px;border-radius:15px}.underdog-hero-banner__image{width:84px;height:64px;border-radius:10px}.underdog-hero-banner__copy{display:block;font-size:clamp(15px,4vw,21px);letter-spacing:-.02em}.underdog-hero-banner__brand{margin-right:4px}.underdog-hero-banner__offer{white-space:normal}.underdog-hero-terms{width:calc(100% - 24px);margin:5px auto 18px;font-size:11px}.underdog-hero-terms__copy{font-size:10px}}
      @media(max-width:360px){.underdog-hero-banner{grid-template-columns:70px minmax(0,1fr);gap:8px}.underdog-hero-banner__image{width:70px;height:62px}.underdog-hero-banner__copy{font-size:14px}}
    `;
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
    banner.setAttribute("aria-label", "Underdog — $50 Bonus + A Rips Pack");
    banner.innerHTML = '<img class="underdog-hero-banner__image" src="https://matchlab.parlaycalculator.bet/assets/underdog-pack-strip.webp" alt="Underdog Sports Starter Pack"><span class="underdog-hero-banner__copy"><strong class="underdog-hero-banner__brand">UNDERDOG -</strong><span class="underdog-hero-banner__offer">$50 Bonus + <em>A Rips Pack</em></span></span>';
    const terms = document.createElement("details");
    terms.className = "underdog-hero-terms";
    terms.innerHTML = '<summary>Terms</summary><p class="underdog-hero-terms__copy">Sign up through our link. New users are eligible for a 50% deposit match. After a qualifying first entry, the referral offer includes $50 in bonus funds and a Sports Starter Pack for you and your friend. Pack maximum value is $150 and is not guaranteed; view pack odds in Rips. A deposit and first entry are required for rewards. Packs are unavailable in Nevada and Canada. Eligibility and full offer terms apply. You\'re welcome.</p>';
    hero.insertAdjacentElement("afterend", banner);
    banner.insertAdjacentElement("afterend", terms);
  });
})();