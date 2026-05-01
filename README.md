# tppr

**tppr** *(Thribhu's Past Paper Repository)* is a repository that holds NESA past papers. This is my Year 12 Software Engineering Major Project for 2026, and was requested by my math tutor to be made. 

The project uses both <font color="red"><u>***PYTHON***</u></font> (looking at you Mr Jones) for the backend and `Typescript/React` for a beautiful frontend. 

## to run online
~~This website is online at [placeholder_link](https://google.com)~~
This website is currently in development and not able to be hosted yet. Try running this locally with your own files if you wish with the provided steps. 

## to run locally

this python-typescript project uses **uv** for the backend and **bun** or **node** for the frontend. for specific info, refer to their respective README.md files for [frontend](frontend/README.md) and [backend](backend/README.md). 

firstly, you need to compile the frontend so it can be served by the backend:
```bash
cd frontend
bun run build
# or
npm run build
# then
cd ..
```

then, you can serve the website:
```bash
cd backend
uv run src/main.py
```

or even better:
```bash
python launch.py # deals with building and serving
```

## self hosting
if you want to provide a system like this for your school, you can do so as the frontend and the backend can be run independently, so you are able to host your backend within the network and the frontend that already exists online. 

if you want to serve the backend and the frontend separately, use the launch script with `--split` as so:
```bash
python launch.py --split
```

> [!NOTE]
> Currently not available as of this moment, but a couple tweaks can get it working. 