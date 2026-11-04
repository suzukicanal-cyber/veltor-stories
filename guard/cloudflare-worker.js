// VELTOR guard — Cloudflare Worker version (runs outside Russia, free plan).
// Telegram sends every group event of @VELTOR_moderator_bot here (webhook):
//  1. "X проголосовал(а) за группу" (boost) notices are deleted at once;
//  2. a post with text in the "Мото" topic starts the stories build on GitHub.
//
// Secrets (Worker → Settings → Variables and Secrets, type "Secret"):
//   BOT_TOKEN       token of @VELTOR_moderator_bot (group admin with "Delete messages")
//   GITHUB_TOKEN    fine-grained token, repo veltor-stories, Actions: read & write
//   WEBHOOK_SECRET  any long random string you make up (only letters and digits)
//
// One-time setup after deploying: open
//   https://<worker-address>/setup?key=<WEBHOOK_SECRET>
// in the browser — the worker registers itself as the bot's webhook.

const GROUP = "koreamotocycles_veltor";
const MOTO_TOPIC_ID = 8;
const REPO = "suzukicanal-cyber/veltor-stories";
const WORKFLOW = "stories.yml";

async function tg(env, method, params) {
  const r = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return r.json();
}

async function startBuild(env) {
  await new Promise((r) => setTimeout(r, 20000)); // let the whole album arrive first
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "veltor-guard",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  console.log("stories build:", r.status);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/setup") {
      if (url.searchParams.get("key") !== env.WEBHOOK_SECRET) return new Response("wrong key", { status: 403 });
      const me = await tg(env, "getMe", {});
      const res = await tg(env, "setWebhook", {
        url: `${url.origin}/hook`,
        secret_token: env.WEBHOOK_SECRET,
        allowed_updates: ["message", "edited_message"],
        drop_pending_updates: true,
      });
      return new Response(JSON.stringify({ bot: me.result && me.result.username, webhook: res }, null, 2),
        { headers: { "Content-Type": "application/json; charset=utf-8" } });
    }

    if (url.pathname !== "/hook" || request.method !== "POST") return new Response("VELTOR guard is running");
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET)
      return new Response("forbidden", { status: 403 });

    const update = await request.json();
    const m = update.message || update.edited_message;
    if (!m || ((m.chat && m.chat.username) || "").toLowerCase() !== GROUP) return new Response("ok");

    if (m.boost_added) {
      const res = await tg(env, "deleteMessage", { chat_id: m.chat.id, message_id: m.message_id });
      console.log("boost notice", m.message_id, res.ok ? "deleted" : JSON.stringify(res));
    } else if (m.message_thread_id === MOTO_TOPIC_ID && m.caption && update.message) {
      ctx.waitUntil(startBuild(env));   // one build per post (the album caption)
    }
    return new Response("ok");
  },
};
