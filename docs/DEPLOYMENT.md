# Deployment

To deploy this project for yourself, you will need the following things: 

- Google Cloud Platform (optional, can try to host yourself but GCP is recommended)
- Supabase Account (again, can be self-hosted, but Supabase is specifically required for auth and db)

## GCP
If you are using Google Cloud Platform, you can easily deploy using the launch script:

```bash
uv run launch.py --deploy gcp
```

It will run you through the steps for deployment, or it might just error out and you will have to debug it :/

## Other cloud platforms
Host the frontend as a static website:

```bash
cd frontend
bun install
bun run build
```

Then copy the `frontend/dist/` folder.

For the backend, just upload the folder and launch with `uv`. 

> [!NOTE]
> I have not attempted to deploy to any other platform than either local or GCP. If you can pull it off, please update the launch.py script and open a PR, or just open a PR and add instructions and I will change it. 