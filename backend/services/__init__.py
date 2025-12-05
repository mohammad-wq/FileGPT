"""Services package initialization."""

# Core services used by the application
from . import searchEngine
from . import file_watcher
from . import metadata_db
from . import fileParser
from . import background_worker
from . import embeddingGeneration
from . import summary_service
from . import router_service

# Optional services
try:
    from . import categorization_service
except ImportError:
    categorization_service = None
