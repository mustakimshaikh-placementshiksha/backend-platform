from django.db import models
from utils.models import JSONField

from account.models import User
from contest.models import Contest
from utils.models import RichTextField
from utils.constants import Choices


class ProblemTag(models.Model):
    name = models.TextField()

    class Meta:
        db_table = "problem_tag"


class ProblemRuleType(Choices):
    ACM = "ACM"
    OI = "OI"


class ProblemDifficulty(object):
    High = "High"
    Mid = "Mid"
    Low = "Low"


class ProblemIOMode(Choices):
    standard = "Standard IO"
    file = "File IO"


def _default_io_mode():
    return {"io_mode": ProblemIOMode.standard, "input": "input.txt", "output": "output.txt"}


class Problem(models.Model):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Represents a programming problem.

    Logic Flow:
    - Stores problem statement, input/output descriptions, samples, and test cases.
    - `_id` is the display ID used in URLs.
    - `io_mode` defines input/output types (standard or file).
    - `spj` flags indicate Special Judge usage.
    - `rule_type` distinguishes between ACM and OI modes.
    - `statistic_info` caches acceptance/submission counts.
    """
    # display ID (custom alphanumeric ID for URLs)
    _id = models.TextField(db_index=True)
    contest = models.ForeignKey(Contest, null=True, on_delete=models.CASCADE)
    # determines validity for contest problems
    is_public = models.BooleanField(default=False)
    title = models.TextField()
    # HTML content for description
    description = RichTextField()
    input_description = RichTextField()
    output_description = RichTextField()
    # Example format: [{input: "test", output: "123"}, {input: "test123", output: "456"}]
    samples = JSONField()
    test_case_id = models.TextField()
    # Format: [{"input_name": "1.in", "output_name": "1.out", "score": 0}]
    test_case_score = JSONField()
    hint = RichTextField(null=True)
    languages = JSONField()
    template = JSONField()
    create_time = models.DateTimeField(auto_now_add=True)
    # Last update timestamp (manually updated)
    last_update_time = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    # Time limit in milliseconds
    time_limit = models.IntegerField()
    # Memory limit in Megabytes
    memory_limit = models.IntegerField()
    # Input/Output mode configuration
    io_mode = JSONField(default=_default_io_mode)
    # Special Judge configuration
    spj = models.BooleanField(default=False)
    spj_language = models.TextField(null=True)
    spj_code = models.TextField(null=True)
    spj_version = models.TextField(null=True)
    spj_compile_ok = models.BooleanField(default=False)
    rule_type = models.TextField()
    visible = models.BooleanField(default=True)
    difficulty = models.TextField()
    tags = models.ManyToManyField(ProblemTag)
    source = models.TextField(null=True)
    # Total score for OI mode
    total_score = models.IntegerField(default=0)
    submission_number = models.BigIntegerField(default=0)
    accepted_number = models.BigIntegerField(default=0)
    # Statistics cache: {JudgeStatus.ACCEPTED: 3, JudgeStaus.WRONG_ANSWER: 11}
    statistic_info = JSONField(default=dict)
    share_submission = models.BooleanField(default=False)

    class Meta:
        db_table = "problem"
        unique_together = (("_id", "contest"),)
        ordering = ("create_time",)

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save(update_fields=["submission_number"])

    def add_ac_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save(update_fields=["accepted_number"])
