# How to run for dev

1. Setup virtualenv: `python3 -m venv ./venv`
2. Add environment variables:
```
export DB_NAME="..."
export BASE_URL="http://localhost/"
export CLIENT_ID="..."
export HOLDING_ACCOUNT_USERNAME="..."
export HOLDING_ACCOUNT_ACCESS_TOKEN="..."
```
3. Activate venv: `source venv/bin/activate`
4. Install libs: `pip install -r requirements.txt`
5. Setup mysql or mariadb if you haven't already
6. Create tables: `flask admin reset-db`
7. Run orderbook: `flask orderbook run`
8. Run server in separate terminal: `flask run`

Other admin commands are available with `flask admin`
