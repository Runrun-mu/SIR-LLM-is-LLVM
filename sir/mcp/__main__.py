"""Allow running with: python -m sir.mcp"""

from sir.mcp.server import app

app.run(transport="stdio")
