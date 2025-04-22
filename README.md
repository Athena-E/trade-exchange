# Trade Exchange Project

A simple trade exchange using TCP connections between an info service, orderbook service and risk limits service.

1. **Application Module**: A module providing a BaseApplication class implementing the minimum requirements of this project and some conveniences, like logging and signal handling.

2. **Connection Library**: A library providing TCP connectivity, enabling communication between different components or external systems.

## Starting Up

Run `uv sync` to create/update the virtual environment. Then active it with `source .venv/bin/activate`.

[comment]: <> (## Deploying)

[comment]: <> (Once you're ready to deploy your application into our testing environment, run the command `deploy.sh` at the root of your project.)

[comment]: <> (Before doing this, make sure to edit your `project.toml` to enable the components `order-book`, `info` and `risk-gateway`.)
