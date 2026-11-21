"""Write the OpenAPI schema to a file (used to generate the web app's TypeScript types).

    python -m betteru.export_openapi ../web/src/api/openapi.json
"""

import sys
from pathlib import Path

from betteru.main import export_openapi

if __name__ == "__main__":
    export_openapi(Path(sys.argv[1]))
