/* Top-hero-only banner release; publish with refreshed source page references. */
/* Shared sport navigation. Native details support touch and keyboard toggling. */
(() => {
  const sportPath = location.pathname.split("/")[1].toUpperCase();
  const site = location.hostname.startsWith("nfl.") ? "NFL" : (["MLB", "NBA", "CBB"].includes(sportPath) ? sportPath : "CFB");
  const sports = {
    MLB: [["MLB Dashboard", "https://matchlab.parlaycalculator.bet/mlb/dashboard/"], ["MLB Teams", "https://matchlab.parlaycalculator.bet/mlb/teams/"], ["Rankings", "https://matchlab.parlaycalculator.bet/mlb/rankings/"]],
    CBB: [["CBB Dashboard", "https://matchlab.parlaycalculator.bet/cbb/dashboard/"], ["CBB Teams", "https://matchlab.parlaycalculator.bet/cbb/teams/"], ["CBB Match Lab", "https://matchlab.parlaycalculator.bet/cbb/match-lab/"], ["Rankings", "https://matchlab.parlaycalculator.bet/cbb/rankings/"]],
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
  // Canonical banner sizing is maintained only in the shared stylesheet.
  const bannerCssId = "underdog-banner-canonical-css";
  if (!document.getElementById(bannerCssId)) {
    const link = document.createElement("link");
    link.id = bannerCssId;
    link.rel = "stylesheet";
    link.href = "https://matchlab.parlaycalculator.bet/assets/underdog-banner.css?v=20261102-canonical-v1";
    document.head.appendChild(link);
  }
  const selector = ".nfl-hero-image,.rank-hero,.cfb-hero-art,.hero-media";
  const salesSelector = ".betwise-cta,.betwise-slate,.betwise-slate-cta,.betwise-collage";
  const addBanner = hero => {
    if (hero.closest(salesSelector) || !hero.querySelector("img") || hero !== [...document.querySelectorAll(selector)].find(candidate => !candidate.closest(salesSelector) && candidate.querySelector("img")) || hero.nextElementSibling?.classList.contains("underdog-hero-banner")) return;
    const banner = document.createElement("a");
    banner.className = "underdog-hero-banner";
    banner.href = "https://play.underdogsports.com/vgwg/e2bt5xbz";
    banner.target = "_blank";
    banner.rel = "sponsored nofollow noopener noreferrer";
    banner.setAttribute("aria-label", "GET A $50 BONUS + A RIPS PACK WORTH UP TO $150!");
    banner.innerHTML = '<span class="underdog-hero-banner__copy">GET A $50 BONUS\n+ A RIPS PACK WORTH UP TO $150!</span>';
    const terms = document.createElement("details");
    terms.className = "underdog-hero-terms";
    terms.innerHTML = "<summary>Terms</summary><p class=\"underdog-hero-terms__copy\">This is an offer for Underdog. Sign up through our link. After a qualifying first entry, the advertised referral offer includes $50 in bonus funds and a Sports Starter Pack for you and your friend. Pack maximum value is $150 and is not guaranteed; view pack odds in Rips. Eligibility, qualifying actions, geographic restrictions, pack availability, and all reward conditions are determined by Underdog. Verify the current offer terms on the linked destination before participating.</p>";
    hero.insertAdjacentElement("afterend", banner);
    banner.insertAdjacentElement("afterend", terms);
  };
  // Repair legacy banners already present on the page instead of leaving old offers active.
  const repairExisting = () => {
    document.querySelectorAll(".underdog-hero-banner").forEach(banner => {
      banner.href = "https://play.underdogsports.com/vgwg/e2bt5xbz";
      banner.setAttribute("aria-label", "GET A $50 BONUS + A RIPS PACK WORTH UP TO $150!");
      banner.innerHTML = '<span class="underdog-hero-banner__copy">GET A $50 BONUS\n+ A RIPS PACK WORTH UP TO $150!</span>';
      const terms = banner.nextElementSibling;
      if (terms?.classList.contains("underdog-hero-terms")) {
        terms.innerHTML = '<summary>Terms</summary><p class="underdog-hero-terms__copy">This is an offer for Underdog. Sign up through our link. After a qualifying first entry, the advertised referral offer includes $50 in bonus funds and a Sports Starter Pack for you and your friend. Pack maximum value is $150 and is not guaranteed; view pack odds in Rips. Eligibility, qualifying actions, geographic restrictions, pack availability, and reward conditions are determined by Underdog. Verify the offer terms on the linked destination before participating.</p>';
      }
    });
  };
  repairExisting();
  document.querySelectorAll(selector).forEach(addBanner);
  // Mobile banners track half the rendered height of their own hero image.
  // Desktop uses the original CSS aspect ratio, without inline height overrides.
  // Consistent mobile banner dimensions across all sports: 90vw at 5.2:1.
  const clearLegacyMobileHeight=()=>document.querySelectorAll(".underdog-hero-banner").forEach(banner=>{banner.style.removeProperty("--underdog-mobile-height");banner.style.removeProperty("height")});
  clearLegacyMobileHeight();
  window.addEventListener("load",clearLegacyMobileHeight);
  new MutationObserver(records => {
    records.forEach(record => record.addedNodes.forEach(node => {
      if (node.nodeType !== 1) return;
      if (node.matches(selector)) addBanner(node);
      node.querySelectorAll(selector).forEach(addBanner);
    }));
  }).observe(document.body, {childList:true,subtree:true});
})();


/* Independent offer settings: future promotions never require a sports data rebuild. */
(() => {
  if (document.getElementById("underdog-offer-config-script")) return;
  const script = document.createElement("script");
  script.id = "underdog-offer-config-script";
  script.src = "https://matchlab.parlaycalculator.bet/assets/underdog-offer.js?v=" + Date.now();
  document.head.appendChild(script);
})();

/* Shared ranking headers across every sport, including legacy page templates. */
(() => {
 if (!/(?:^|[/-])rankings(?:\/|$)/.test(location.pathname) || document.getElementById('ranking-sticky-headers-script')) return;
 const script=document.createElement('script');
 script.id='ranking-sticky-headers-script';
 script.src='https://matchlab.parlaycalculator.bet/sports-research/rankings-sticky-headers.js?v=20261104-2';
 document.head.appendChild(script);
})();
