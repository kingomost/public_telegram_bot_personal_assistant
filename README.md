# Telegram Bot Personal Assistant

An early single-user personal assistant prototype with daily plans, tasks,
a backlog, goals, habits, rituals, reminders, and reports.

## Secure Docker setup

Requires Docker Engine and Docker Compose v2.

1. Create a local configuration file:

   ```bash
   cp .env.example .env
   ```

2. Set your actual `BOT_TOKEN` and numeric Telegram `OWNER_ID` in `.env`.
   Git ignores `.env`, and it is excluded from the Docker build context.

3. Build and start the container:

   ```bash
   docker compose up --detach --build
   ```

4. View the startup logs:

   ```bash
   docker compose logs --follow telegram-bot
   ```

5. Stop the container without deleting stored data:

   ```bash
   docker compose down
   ```

Data is stored in the named Docker volume
`telegram-bot-personal-assistant-data`. Do not run a second instance of the bot
with the same token at the same time: Telegram long polling allows only one
active receiver of updates.

The container runs as an unprivileged user with a read-only root filesystem
and no Linux capabilities. Writes are allowed only in the `/app/.data` volume
and the temporary `/tmp` directory.

## Local testing

The project targets Python 3.12.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --requirement requirements.txt
python -m unittest discover -s tests -v
```

## License

This project is licensed under the [BSD Zero Clause License (0BSD)](LICENSE).
You may use, copy, modify, and distribute the code for any purpose, including
commercial use, without attribution requirements. The software is provided
without warranty.
