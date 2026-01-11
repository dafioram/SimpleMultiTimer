1. Run docker-compose up -d --build
2. http://YOUR-SERVER-IP:5000

Database backup made on app start up.

How to DB Restore
1. Stop App (docker compose down)
2. Delete timers.db*
3. Rename timers_backup*.db to timers.db and move to data folder
4. Start app (docker compose up -d)