from django.db import models
from django.utils import timezone


class JudgeServer(models.Model):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Represents a judging server node.

    Logic Flow:
    - Stores server metrics (CPU, memory, version, etc.).
    - `last_heartbeat`: Used to determine if the server is alive.
    - `service_url`: URL where the judge server API is accessible.
    - `is_disabled`: Administrative toggle to disable the server.
    """
    hostname = models.TextField()
    ip = models.TextField(null=True)
    judger_version = models.TextField()
    cpu_core = models.IntegerField()
    memory_usage = models.FloatField()
    cpu_usage = models.FloatField()
    last_heartbeat = models.DateTimeField()
    create_time = models.DateTimeField(auto_now_add=True)
    task_number = models.IntegerField(default=0)
    service_url = models.TextField(null=True)
    is_disabled = models.BooleanField(default=False)

    @property
    def status(self):
        # Add a 1-second delay tolerance to adapt to network fluctuations
        if (timezone.now() - self.last_heartbeat).total_seconds() > 6:
            return "abnormal"
        return "normal"

    class Meta:
        db_table = "judge_server"
