const repository = "thomaspyrda/match-lab-college-football-data";
const api = `https://api.github.com/repos/${repository}`;
const requestPath = "/contents/data/automation/primary-request.json";
const eastern = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

function local(time) {
  const parts = Object.fromEntries(eastern.formatToParts(time).map(({ type, value }) => [type, value]));
  return { date: `${parts.year}-${parts.month}-${parts.day}`, hour: Number(parts.hour), minute: Number(parts.minute) };
}

export async function submitMorning(scheduledTime, now, token, fetcher = fetch) {
  const slot = local(scheduledTime);
  const previousHour = local(scheduledTime - 3_600_000);
  const springForward = slot.hour === 3 && previousHour.hour === 1;
  if (slot.minute !== 30 || (slot.hour !== 2 && !springForward)) return "other UTC offset";
  const current = local(now);
  if (now < scheduledTime || current.date !== slot.date || current.hour >= 11) return "outside today's morning window";
  if (!token) throw new Error("Missing GitHub scheduler secret");

  async function github(path, options = {}) {
    const response = await fetcher(api + path, {
      redirect: "error",
      ...options,
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "User-Agent": "WiseStats-morning-scheduler",
        "X-GitHub-Api-Version": "2022-11-28",
      },
    });
    if (!response.ok && !(options.method === "PUT" && response.status === 409)) {
      throw new Error(`GitHub ${options.method || "GET"} ${path} returned ${response.status}`);
    }
    return response;
  }

  const existing = async () => (await github(`${requestPath}?ref=main`)).json();
  const sameRequest = file => {
    const request = JSON.parse(atob(file.content.replace(/\s/g, "")));
    return request.date === slot.date && request.cycle === "morning";
  };
  const file = await existing();
  if (sameRequest(file)) return "request already submitted";

  const workflows = ["start-daily-primary.yml", "coordinate-sport-data.yml"];
  const results = await Promise.all(workflows.map(async name => {
    const response = await github(`/actions/workflows/${name}/runs?branch=main&per_page=100`);
    return (await response.json()).workflow_runs;
  }));
  const [launchers, coordinators] = results;
  if (launchers.concat(coordinators).some(run => run.status !== "completed")) return "workflow already active";
  if (coordinators.some(run => run.display_title === "morning daily data pipeline" && local(Date.parse(run.created_at)).date === slot.date)) {
    return "coordinator already ran today";
  }

  const response = await github(requestPath, {
    method: "PUT",
    body: JSON.stringify({
      branch: "main",
      sha: file.sha,
      message: `Start ${slot.date} Eastern WiseStats morning refresh`,
      content: btoa(JSON.stringify({ date: slot.date, cycle: "morning" }) + "\n"),
    }),
  });
  if (response.status === 409) {
    if (sameRequest(await existing())) return "request already submitted by another writer";
    throw new Error("GitHub rejected the request SHA; no retry attempted");
  }
  return "dated morning request submitted";
}

export default {
  async scheduled(controller, env) {
    console.log(await submitMorning(controller.scheduledTime, Date.now(), env.GITHUB_SCHEDULER_TOKEN));
  },
};
