from django.db import models
from utils.models import JSONField


class SysOptions(models.Model):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Stores system-wide configuration options.

    Logic Flow:
    - Uses a Key-Value pair structure.
    - `value` is a JSONField, allowing flexible data types (strings, lists, dicts).
    - Acts as a persistent configuration store for the application.
    """
    key = models.TextField(unique=True, db_index=True)
    value = JSONField()
