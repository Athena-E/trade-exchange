# Career Kickstarter - Project Framework

This repository contains the base of your application.

## Template Code Overview

The template includes the following components:

1. **Application Module**: A module providing a BaseApplication class implementing the minimum requirements of this project and some conveniences, like logging and signal handling.

2. **Connection Library**: A library providing TCP connectivity, enabling communication between different components or external systems.

3. **Sample Application**: A `sample_app` demonstrating how to use the application module and connection library together. This serves as a reference implementation to help you get started quickly.

Use these components as a foundation to build and expand your project.

## Starting Up

After you checkout this repo, you can run `uv sync` to create/update the virtual environment. Then active it with `source .venv/bin/activate`.

## Deploying

Once you're ready to deploy your application into our testing environment, run the command `deploy.sh` at the root of your project.

Before doing this, make sure to edit your `project.toml` to enable the components `order-book`, `info` and `risk-gateway`.
