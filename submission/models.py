from django.db import models

from utils.constants import ContestStatus
from utils.models import JSONField
from problem.models import Problem
from contest.models import Contest

from utils.shortcuts import rand_str


class JudgeStatus:
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Enumeration of various matching statuses for a submission.
    """
    COMPILE_ERROR = -2
    WRONG_ANSWER = -1
    ACCEPTED = 0
    CPU_TIME_LIMIT_EXCEEDED = 1
    REAL_TIME_LIMIT_EXCEEDED = 2
    MEMORY_LIMIT_EXCEEDED = 3
    RUNTIME_ERROR = 4
    SYSTEM_ERROR = 5
    PENDING = 6
    JUDGING = 7
    PARTIALLY_ACCEPTED = 8


class Submission(models.Model):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Represents a code submission for a problem.

    Logic Flow:
    - Stores the submitted code, language, and associated user/problem/contest.
    - Tracks the judging result (status, time, memory) returned by the JudgeServer.
    - `info` stores detailed judgment results per test case.
    - `statistic_info` stores summary statistics like total time and memory usage.
    - `shared` flag allows users to make their submission code public.
    """
    id = models.TextField(default=rand_str, primary_key=True, db_index=True)
    contest = models.ForeignKey(Contest, null=True, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    user_id = models.IntegerField(db_index=True)
    username = models.TextField()
    code = models.TextField()
    result = models.IntegerField(db_index=True, default=JudgeStatus.PENDING)
    # Detailed judgment info returned from JudgeServer (per test case)
    info = JSONField(default=dict)
    language = models.TextField()
    shared = models.BooleanField(default=False)
    # Stores the time and memory usage for the submission to display in lists
    # Format: {time_cost: "", memory_cost: "", err_info: "", score: 0}
    statistic_info = JSONField(default=dict)
    ip = models.TextField(null=True)

    def check_user_permission(self, user, check_share=True):
        if self.user_id == user.id or user.is_super_admin() or user.can_mgmt_all_problem() or self.problem.created_by_id == user.id:
            return True

        if check_share:
            if self.contest and self.contest.status != ContestStatus.CONTEST_ENDED:
                return False
            if self.problem.share_submission or self.shared:
                return True
        return False

    class Meta:
        db_table = "submission"
        ordering = ("-create_time",)

    def __str__(self):
        return self.id
