from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK, SECRET_KEY

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]
SECRET_KEY = SECRET_KEY or "dev-only-secret"  # noqa: A001

# Local development and the test suite make many rapid requests; production
# keeps the rate limits configured in base.py.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}
