"""HTTP Cloud Function, entry point 'ingest'. Takes the same synthetic
event JSON the AWS-side generator can emit (see log-generator/generate.py)
and writes it as a structured Cloud Logging entry. Deliberately minimal,
this exists to back a real GCP deployment, not to duplicate the AWS
detection logic on a second cloud.
"""

import json

import functions_framework
import google.cloud.logging

_client = google.cloud.logging.Client()
_logger = _client.logger("synthetic-events")


@functions_framework.http
def ingest(request):
    if request.method != "POST":
        return ("method not allowed, POST a JSON event body", 405)

    try:
        payload = request.get_json(silent=False)
    except Exception:
        return ("invalid JSON body", 400)

    if not isinstance(payload, dict) or "event_type" not in payload:
        return ("expected a JSON object with an event_type field", 400)

    _logger.log_struct(payload, severity="INFO")
    return (json.dumps({"status": "logged"}), 200, {"Content-Type": "application/json"})
