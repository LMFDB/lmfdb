# Timezone handling utilities
try:
    from datetime import UTC               # Py 3.11+
except ImportError:                         # Py ≤3.10
    from datetime import timezone as _tz
    UTC = _tz.utc

def utc_now_naive():
    """
    Return current UTC time as a naive datetime object (no timezone info).
    This is used for storing timestamps in databases which use
    'timestamp without time zone' columns but store all times as UTC.
    """
    from datetime import datetime
    return datetime.now(UTC).replace(tzinfo=None)

def ensure_naive_utc(dt):
    """
    Ensure datetime object is naive (no timezone) and represents UTC time.
    If timezone-aware, convert to UTC first, then strip timezone info.
    If naive, assume it's already UTC.
    """
    if dt.tzinfo is not None:
        # Convert to UTC and strip timezone
        return dt.astimezone(UTC).replace(tzinfo=None)
    else:
        # Already naive, assume it's UTC
        return dt

# conversion tools between timestamp different kinds of timestamp
import datetime
epoch = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

def datetime_to_timestamp_in_ms(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return int((dt - epoch).total_seconds() * 1000000)

def timestamp_in_ms_to_datetime(ts):
    return datetime.datetime.fromtimestamp(float(int(ts)/1000000.0), datetime.timezone.utc)
