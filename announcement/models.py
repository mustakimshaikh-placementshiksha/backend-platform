from django.db import models

from account.models import User
from utils.models import RichTextField


class Announcement(models.Model):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Represents a system-wide announcement.

    Logic Flow:
    - Stores the title and rich-text content of the announcement.
    - Used for broadcasting information to all users (e.g., maintenance, updates).
    """
    title = models.TextField()
    # HTML content for the announcement
    content = RichTextField()
    create_time = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    last_update_time = models.DateTimeField(auto_now=True)
    visible = models.BooleanField(default=True)

    class Meta:
        db_table = "announcement"
        ordering = ("-create_time",)
