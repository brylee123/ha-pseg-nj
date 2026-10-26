"""Constants for the PSE&G NJ integration."""

from datetime import timedelta

DOMAIN = "pseg_nj"
CONF_LABEL = "label"
CONF_METER = "meter"
CONF_COOKIE = "session_cookie"
SERVICE_IMPORT_CSV = "import_csv"
UPDATE_INTERVAL = timedelta(hours=12)
MAX_IMPORT_BYTES = 25_000_000
