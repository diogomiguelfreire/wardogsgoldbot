# WARDOGS Gold Price Bot

Posts the WARDOGS gold bar exchange rate (cash per gold bar) to a Discord channel at the top of every hour, with a price chart.
It also adds a `/gold` slash command that anyone can use, with an optional `7d` / `30d` / `90d` / `all` range.

## Where the price comes from

The price comes from **MetaForge's JSON endpoint**, `https://metaforge.app/api/wardogs/market`, the same one their [Gold Bar Market](https://metaforge.app/wardogs/market) page uses.
It is public: no API key, and their `robots.txt` allows it. It is **not** a documented OpenAPI, so it could change without notice.
Responses are cached for 5 minutes, so one call per hour is very light.

The in-game rate changes roughly **once a day**, so most hourly posts will show the same price.
Set `ONLY_POST_ON_CHANGE=true` if you'd rather the bot only post when the price actually moves.

## Free hosting with GitHub Actions (hourly post only)

GitHub runs `post_once.py` every hour. It posts the price through a channel webhook, then stops. There's no server and it costs nothing.
`/gold` doesn't work this way, because slash commands need the full bot running all the time.

1. **Create a webhook.** In Discord: channel settings → *Integrations* → *Webhooks* → *New Webhook* → *Copy Webhook URL*.
2. **Create a private repo** on GitHub (github.com → *New repository*, set to *Private*, leave it empty).
   Use a private repo: GitHub turns off scheduled runs in public repos after 60 days with no activity.
3. **Push this folder** to it (replace the URL with your repo's):

   ```bash
   git init
   git add .
   git commit -m "WARDOGS gold price poster"
   git branch -M main
   git remote add origin https://github.com/YOUR-NAME/YOUR-REPO.git
   git push -u origin main
   ```

   `.gitignore` keeps `.env` and `.venv` out of the repo.
4. **Add the webhook as a secret.** In the repo: *Settings* → *Secrets and variables* → *Actions* → *New repository secret*, with name `DISCORD_WEBHOOK_URL` and the URL as its value.
5. **Test it.** Open the *Actions* tab → *Post gold price* → *Run workflow*. A post should appear in the channel within a minute.

After that, it posts at about minute 5 of every hour. GitHub's scheduler often starts runs a few minutes late, sometimes 10–15 minutes at busy times.
Optional: under *Settings* → *Secrets and variables* → *Actions* → *Variables*, add `CHART_DAYS` or `ONLY_POST_ON_CHANGE=true`.
Each run takes about a minute, so a month of hourly runs fits within the free Actions minutes for private repos.

To preview the message locally without posting:

```bash
python post_once.py --dry-run
```

## Running the full bot (hourly post + `/gold`)

1. **Create the bot.** Go to the [Discord Developer Portal](https://discord.com/developers/applications) → *New Application* → *Bot* → *Reset Token*, and copy the token.
2. **Invite it.** Go to *OAuth2 → URL Generator*, tick the `bot` and `applications.commands` scopes, then the *Send Messages*, *Embed Links* and *Attach Files* permissions. Open the generated URL and add the bot to your server.
3. **Get the channel ID.** In Discord, turn on *Settings → Advanced → Developer Mode*, then right-click the channel → *Copy Channel ID*.
4. **Configure.** Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` and `CHANNEL_ID`.
5. **Install and run:**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows (macOS/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   python bot.py
   ```

Posts go out at minute :00 of every hour (UTC). The bot only posts while it is running, so keep it on a PC that stays on, or on a small VPS or hosting service.

## Settings (`.env`, or repo secrets/variables on GitHub)

| Variable | Default | What it does |
|---|---|---|
| `DISCORD_TOKEN` | full bot only | Bot token |
| `CHANNEL_ID` | full bot only | Channel for the hourly post |
| `DISCORD_WEBHOOK_URL` | webhook only | Webhook that `post_once.py` posts to |
| `CHART_DAYS` | `30` | Days shown in the main chart |
| `ONLY_POST_ON_CHANGE` | `false` | Skip the hourly post when the price hasn't changed |
| `ALERT_BELOW` | `200000` | Ping `@everyone` when the price drops below this. `0` turns it off |

## Low-price alert

When the price drops below `ALERT_BELOW` (default 200,000), the hourly post includes an `@everyone` ping.
It pings **once per drop**. While the price stays low, the posts go out without a ping. Once the price climbs back above the limit, the next drop below it pings again.

If the ping shows as plain text and doesn't notify anyone, the webhook isn't allowed to mention everyone in that channel.
In Discord, go to channel settings → *Permissions* → `@everyone` role and allow **Mention @everyone, @here, and All Roles**.
That setting also lets regular members ping `@everyone` in that channel. A channel where only admins can talk, such as an announcements channel, avoids that.

## Files

- `bot.py`: full bot with the hourly loop and the `/gold` command
- `post_once.py`: posts once through a webhook (used by GitHub Actions)
- `.github/workflows/gold-price.yml`: the hourly GitHub Actions schedule
- `message.py`: builds the embed and chart that both of them send
- `market.py`: fetches the price data and calculates the changes
- `chart.py`: draws the chart with matplotlib
- `state.json`: created at runtime; stores the last posted price for the "Since last post" field (cached between runs on GitHub)
