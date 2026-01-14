from fastmcp import FastMCP
from middleware.auth import AuthenticationMiddleware

mcp = FastMCP("LibreChat Server")

mcp.add_middleware(AuthenticationMiddleware)


@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run()
