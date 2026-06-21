# tppr-backend

This is the backend, which stores the database and the past paper questions. 

on launch, you can take a look at the API documentation (powered by swagger) at [localhost:5000/api/docs/](http://localhost:5000/api/docs/)

## running

this requires **uv** to be installed.

```bash
# Either set a full URL:
export DATABASE_URL="postgresql+psycopg2://user:password@host:5432/dbname?sslmode=require"

# Or set the individual parts:
export DB_USER="user"
export DB_PASSWORD="password"
export DB_HOST="host"
export DB_PORT="5432"
export DB_NAME="dbname"
uv run src/main.py
```

The database must be PostgreSQL. If `DATABASE_URL` is not set, the backend builds
one from `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, and `DB_NAME`.

this will launch the backend as an API. for the frontend, you should use the [frontend](../frontend/README.md) folder and launch with those instructions
