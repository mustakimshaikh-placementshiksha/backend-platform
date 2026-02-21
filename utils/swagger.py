"""
utils/swagger.py

Shared Swagger/OpenAPI helpers for the OnlineJudge project.
Import these into any view file to standardize response shapes.
"""
from rest_framework import serializers
from drf_yasg import openapi


# ─── Standard wrapper every endpoint returns ────────────────────────────────

class StandardResponseSerializer(serializers.Serializer):
    """
    Every API endpoint in OnlineJudge wraps its response in:
      {
        "error": null | "ErrorMessage",
        "data":  <payload>
      }
    Use this as the `responses={200: StandardResponseSerializer}` shorthand.
    """
    error = serializers.CharField(
        allow_null=True,
        help_text="null on success, error message string on failure"
    )
    data = serializers.JSONField(
        help_text="Actual response payload, structure varies per endpoint"
    )


# ─── Pre-built pagination wrapper ────────────────────────────────────────────

class PaginatedResponseSerializer(serializers.Serializer):
    """
    Paginated list response shape:
      {
        "error": null,
        "data": {
          "total": 42,
          "results": [ ... ]
        }
      }
    """
    error = serializers.CharField(allow_null=True)
    data  = serializers.DictField(
        child=serializers.JSONField(),
        help_text='{"total": int, "results": [...]}'
    )


# ─── Re-usable openapi.Parameter shortcuts ───────────────────────────────────

def query_int(name, description, required=False):
    return openapi.Parameter(name, openapi.IN_QUERY,
                             type=openapi.TYPE_INTEGER,
                             required=required,
                             description=description)

def query_str(name, description, required=False):
    return openapi.Parameter(name, openapi.IN_QUERY,
                             type=openapi.TYPE_STRING,
                             required=required,
                             description=description)

def query_bool(name, description, required=False):
    return openapi.Parameter(name, openapi.IN_QUERY,
                             type=openapi.TYPE_BOOLEAN,
                             required=required,
                             description=description)

# ─── Common pagination parameters ────────────────────────────────────────────

PAGINATION_PARAMS = [
    query_int("limit",  "Number of results per page (required for list endpoints)"),
    query_int("offset", "Starting offset for pagination"),
]

# ─── Common security definitions (mirror settings.py SWAGGER_SETTINGS) ───────

SESSION_AUTH  = [{"SessionAuth": []}]
APPKEY_AUTH   = [{"ApiKeyAuth": []}]
DUAL_AUTH     = [{"SessionAuth": []}, {"ApiKeyAuth": []}]
NO_AUTH       = []
