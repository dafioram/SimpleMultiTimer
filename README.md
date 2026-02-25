# Activity Timer - API Documentation

## Database Backup API

You can trigger a manual database backup (forcing a WAL checkpoint and copying the SQLite database) by sending a `POST` request to the backup endpoint.
Example cronjob:

```bash
0 2 * * * curl -s -X POST http://127.0.0.1:5000/api/backup -H "X-API-Key: your_super_secret_key_here" >> /home/pi/timer_backup.log 2>&1

### Configuration

Before using the API, you must configure a secure API key. 
Create a `.env` file in the root directory of the application and add your key:

```ini
API_BACKUP_KEY=your_super_secret_key_here