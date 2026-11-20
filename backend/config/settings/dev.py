from .base import *  # noqa: F401,F403
from .base import SECRET_KEY

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]
SECRET_KEY = SECRET_KEY or "dev-only-secret"  # noqa: A001
