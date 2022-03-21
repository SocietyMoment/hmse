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


# Production

This is not complete, its more for me to rememeber stuff.

1. Install docker-compose version 1.27.4
2. In prod env, update web_env and .env with prod stuff
3. Make cert and stonk-icons folders
4. add certs with `host.pem` and `host-key.pem`
3. run `docker-compose up mariadb` and close once db created
5. run admin commands with `docker-compose run orderbook flask admin`
6. run `docker-compose up` (optionally with `-d`)

To get shell on running container its `docker-compose exec nginx sh`

To connect to db, either connect to mariadb container with `bash`
or use port 3001 exposed externally (`mariadb -P3001 -h 127.0.0.1 -uwebapp -psecret`).

View nginx status stuff:
`curl https://localhost/nginx_status -k -H "Host: hmse.cash"`

