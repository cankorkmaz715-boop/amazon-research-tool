# PostgreSQL – Amazon Research Tool

## Connection details

- **Host:** `127.0.0.1` (or `localhost` when the app runs on this server)
- **Port:** `5433` (system PostgreSQL; port 5432 is used by Docker on this server)
- **Database:** `amazon_research`
- **User:** `amazon_user`
- **Password:** `AmzR3s3archS3cureP4ss`

---

## Connection string for your application

**URL format (use in `DATABASE_URL` or `POSTGRES_URL`):**

```
postgresql://amazon_user:AmzR3s3archS3cureP4ss@127.0.0.1:5433/amazon_research
```

**With SSL disabled (typical for local/same-server):**

```
postgresql://amazon_user:AmzR3s3archS3cureP4ss@127.0.0.1:5433/amazon_research?sslmode=disable
```

**Example `.env.local` (Next.js / Node):**

```env
DATABASE_URL="postgresql://amazon_user:AmzR3s3archS3cureP4ss@127.0.0.1:5433/amazon_research"
```

**If the app runs on another machine**, replace `127.0.0.1` with this server’s public IP or hostname. Ensure PostgreSQL is allowed to accept remote connections (e.g. in `pg_hba.conf` and `listen_addresses`) and that port **5433** is open in the firewall.

---

## Security

- Do not commit the password or this file to public repositories.
- Prefer storing the connection string in environment variables (e.g. `.env.local`) and adding `.env*` to `.gitignore`.
- To change the password:  
  `sudo -u postgres psql -c "ALTER USER amazon_user WITH PASSWORD 'your_new_password';"`
