## Development Environment
1. Using `kubectl -n p-debug exec -it debug-rsv-jeonghunpark-20260417-f36863 -- bash`, you can access the H200-attached kubernetes pod. You may use this pod to serve LLM to evaluate with portforwarding. It has its own directory layout based on the GPU cluster. You can find documents about this in `~/code/snupi/mlxp/docs` like `overview.md` and `user-guide.md`. You can freely use this pod. You can install any necessary things in it.

2. prefer `uv` for python manager.