# Thribhu's Past Paper Repository

**tppr** _(Thribhu's Past Paper Repository)_ is a repository that holds NESA past papers. This is my Year 12 Software Engineering Major Project for 2026, and was requested by my math tutor to be made.

The project uses both <font color="red"><u>**_PYTHON_**</u></font> (looking at you Mr Jones) for the backend and `Typescript/React` for a beautiful frontend.

## to run online

~~This website is online at [placeholder_link](https://google.com)~~
This website is currently in development and not able to be hosted yet. Try running this locally with your own files if you wish with the provided steps.

## to run locally

firstly, you need to set your env variables. set it by copying [.env](.env) and setting the variables. you could also copy it and keep it as the default (but I don't think that's very secure).

```bash
cp .env-example .env
```

this project requires **uv** for the backend and **bun** or **node** for the frontend. for specific info, refer to their respective README.md files for [frontend](frontend/README.md) and [backend](backend/README.md).

launch with the [launch.py](launch.py) script, which deals with all the dependencies for you. 

```bash
uv run launch.py # deals with building and serving
```

where it will be launched at [localhost:5000](localhost:5000)

## self hosting

if you want to provide a system like this for your school, you can do so as the frontend and the backend can be run independently, so you are able to host your backend within the network and the frontend that already exists online.

if you want to serve the backend and the frontend separately, use the launch script with `--split` as so:

```bash
uv run launch.py --split
```

it will launch the frontend at [localhost:5173](http://localhost:5173) and the backend at [localhost:5000](http://localhost:5000).

> [!NOTE]
> Currently not available as of this moment, but a couple tweaks can get it working.
