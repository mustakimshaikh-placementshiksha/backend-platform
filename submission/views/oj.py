import ipaddress

from account.decorators import login_required, check_contest_permission
from contest.models import ContestStatus, ContestRuleType
from judge.tasks import judge_task
from options.options import SysOptions
# from judge.dispatcher import JudgeDispatcher
from problem.models import Problem, ProblemRuleType
from utils.api import APIView, validate_serializer
from utils.cache import cache
from utils.captcha import Captcha
from utils.throttling import TokenBucket
from ..models import Submission
from ..serializers import (CreateSubmissionSerializer, SubmissionModelSerializer,
                           ShareSubmissionSerializer)
from ..serializers import SubmissionSafeModelSerializer, SubmissionListSerializer



from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from utils.swagger import StandardResponseSerializer

class SubmissionAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles individual submission operations.

    Logic Flow:
    - Throttling: Limits submission frequency for users (except for API key usage).
    """
    def throttling(self, request):
        # Open API requests are not throttled
        auth_method = getattr(request, "auth_method", "")
        if auth_method == "api_key":
            return
        user_bucket = TokenBucket(key=str(request.user.id),
                                  redis_conn=cache, **SysOptions.throttling["user"])
        can_consume, wait = user_bucket.consume()
        if not can_consume:
            return "Please wait %d seconds" % (int(wait))

    @check_contest_permission(check_type="problems")
    def check_contest_permission(self, request):
        contest = self.contest
        if contest.status == ContestStatus.CONTEST_ENDED:
            return self.error("The contest have ended")
        if not request.user.is_contest_admin(contest):
            user_ip = ipaddress.ip_address(request.session.get("ip"))
            if contest.allowed_ip_ranges:
                if not any(user_ip in ipaddress.ip_network(cidr, strict=False) for cidr in contest.allowed_ip_ranges):
                    return self.error("Your IP is not allowed in this contest")

    @swagger_auto_schema(
        operation_id="submission_create",
        operation_summary="Submit Problem Solution",
        operation_description=(
            "Submit code for judging.\n\n"
            "**Flow:**\n"
            "1. Get available languages from `GET /api/conf/languages/`\n"
            "2. Get the `problem_id` (DB integer PK) from the problem detail endpoint\n"
            "3. Submit here with correct language code\n\n"
            "**Throttling:** Regular users can submit once per 30 seconds. API Key users are exempt.\n\n"
            "**Returns:** `submission_id` — use with `GET /api/submission/` to poll for the judge result."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["problem_id", "language", "code"],
            properties={
                "problem_id":  openapi.Schema(type=openapi.TYPE_INTEGER,
                                              description="Problem's database PK (integer, not display ID)",
                                              example=1),
                "language":    openapi.Schema(type=openapi.TYPE_STRING,
                                              description="Language code from GET /api/conf/languages/",
                                              example="C++"),
                "code":        openapi.Schema(type=openapi.TYPE_STRING,
                                              description="Your solution source code",
                                              example="#include<bits/stdc++.h>\nusing namespace std;\nint main(){\n    int a, b;\n    cin >> a >> b;\n    cout << a + b << endl;\n    return 0;\n}"),
                "contest_id":  openapi.Schema(type=openapi.TYPE_INTEGER,
                                              description="Contest ID (only if submitting to a contest)",
                                              example=None),
                "captcha":     openapi.Schema(type=openapi.TYPE_STRING,
                                              description="CAPTCHA token (if required by system settings)",
                                              example=""),
            },
            example={
                "problem_id": 1,
                "language": "C++",
                "code": "#include<bits/stdc++.h>\nusing namespace std;\nint main(){\n    int a, b;\n    cin >> a >> b;\n    cout << a + b << endl;\n    return 0;\n}"
            }
        ),
        responses={
            200: openapi.Response(
                description="Submission created",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {"error": None, "data": {"submission_id": "abc123def456"}}
                }
            )
        },
        tags=["Submission"]
    )
    @validate_serializer(CreateSubmissionSerializer)
    @login_required
    def post(self, request):
        """
        Creates a new submission.

        Logic Flow:
        - Validates contest permissions if part of a contest.
        - Checks if the user is allowed to access problem details.
        - Validates captcha if required.
        - Checks throttling limits.
        - Validates problem existence and allowed languages.
        - Creates the `Submission` record.
        - Triggers the asynchronous judging task: `judge_task.send`.
        """
        data = request.data
        hide_id = False
        if data.get("contest_id"):
            error = self.check_contest_permission(request)
            if error:
                return error
            contest = self.contest
            if not contest.problem_details_permission(request.user):
                hide_id = True

        if data.get("captcha"):
            if not Captcha(request).check(data["captcha"]):
                return self.error("Invalid captcha")
        error = self.throttling(request)
        if error:
            return self.error(error)

        try:
            problem = Problem.objects.get(id=data["problem_id"], contest_id=data.get("contest_id"), visible=True)
        except Problem.DoesNotExist:
            return self.error("Problem not exist")
        if data["language"] not in problem.languages:
            return self.error(f"{data['language']} is not allowed in the problem")
        submission = Submission.objects.create(user_id=request.user.id,
                                               username=request.user.username,
                                               language=data["language"],
                                               code=data["code"],
                                               problem_id=problem.id,
                                               ip=request.session["ip"],
                                               contest_id=data.get("contest_id"))
        # Asynchronous task for judging
        # JudgeDispatcher(submission.id, problem.id).judge()
        judge_task.send(submission.id, problem.id)
        if hide_id:
            return self.success()
        else:
            return self.success({"submission_id": submission.id})

    @swagger_auto_schema(
        operation_summary="Get Submission Detail",
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Submission ID"),
        ],
        responses={200: SubmissionModelSerializer},
        tags=["Submission"]
    )
    @login_required
    def get(self, request):
        """
        Retrieves submission details.
        
        Logic Flow:
        - Checks permissions (user must own it, or be an admin, or permission to view all).
        - For OI problems or admins, full submission details are returned.
        - For other users on non-OI problems, safe details are returned (potentially hiding sensitive info).
        - Includes a flag `can_unshare` indicating if the user can stop sharing the submission.
        """
        submission_id = request.GET.get("id")
        if not submission_id:
            return self.error("Parameter id doesn't exist")
        try:
            submission = Submission.objects.select_related("problem").get(id=submission_id)
        except Submission.DoesNotExist:
            return self.error("Submission doesn't exist")
        if not submission.check_user_permission(request.user):
            return self.error("No permission for this submission")

        if submission.problem.rule_type == ProblemRuleType.OI or request.user.is_admin_role():
            submission_data = SubmissionModelSerializer(submission).data
        else:
            submission_data = SubmissionSafeModelSerializer(submission).data
        # Check if user has permission to unshare the submission
        submission_data["can_unshare"] = submission.check_user_permission(request.user, check_share=False)
        return self.success(submission_data)

    @swagger_auto_schema(
        operation_summary="Share Submission",
        request_body=ShareSubmissionSerializer,
        responses={200: openapi.Response("Succeeded", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["Submission"]
    )
    @validate_serializer(ShareSubmissionSerializer)
    @login_required
    def put(self, request):
        """
        Updates the shared status of a submission.

        Logic Flow:
        - Verifies that the user owns the submission or has permission.
        - Prevents sharing if the contest is currently underway (to avoid cheating).
        - Updates the `shared` boolean field.
        """
        try:
            submission = Submission.objects.select_related("problem").get(id=request.data["id"])
        except Submission.DoesNotExist:
            return self.error("Submission doesn't exist")
        if not submission.check_user_permission(request.user, check_share=False):
            return self.error("No permission to share the submission")
        if submission.contest and submission.contest.status == ContestStatus.CONTEST_UNDERWAY:
            return self.error("Can not share submission now")
        submission.shared = request.data["shared"]
        submission.save(update_fields=["shared"])
        return self.success()


class SubmissionListAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Get Submission List",
        manual_parameters=[
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Limit"),
            openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Offset"),
            openapi.Parameter("problem_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Problem ID"),
            openapi.Parameter("myself", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Myself (1=Yes)"),
            openapi.Parameter("result", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Result"),
            openapi.Parameter("username", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Username"),
        ],
        responses={200: SubmissionListSerializer(many=True)},
        tags=["Submission"]
    )
    def get(self, request):
        if not request.GET.get("limit"):
            return self.error("Limit is needed")
        if request.GET.get("contest_id"):
            return self.error("Parameter error")

        submissions = Submission.objects.filter(contest_id__isnull=True).select_related("problem__created_by")
        problem_id = request.GET.get("problem_id")
        myself = request.GET.get("myself")
        result = request.GET.get("result")
        username = request.GET.get("username")
        if problem_id:
            try:
                problem = Problem.objects.get(_id=problem_id, contest_id__isnull=True, visible=True)
            except Problem.DoesNotExist:
                return self.error("Problem doesn't exist")
            submissions = submissions.filter(problem=problem)
        if (myself and myself == "1") or not SysOptions.submission_list_show_all:
            submissions = submissions.filter(user_id=request.user.id)
        elif username:
            submissions = submissions.filter(username__icontains=username)
        if result:
            submissions = submissions.filter(result=result)
        data = self.paginate_data(request, submissions)
        data["results"] = SubmissionListSerializer(data["results"], many=True, user=request.user).data
        return self.success(data)


class ContestSubmissionListAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves a list of submissions within a specific contest.

    Logic Flow:
    - Filters submissions by contest ID.
    - Applies filters for problem ID, user (myself vs others), and result status.
    - Enforces contest rules:
        - If the contest hasn't started, no submissions are shown (or handled elsewhere).
        - If `ACM` rules apply and the rank board is sealed (`real_time_rank` is False), normal users can only see their own submissions to prevent leaking info during the final freeze.
        - Admins can always see all submissions.
    """
    @swagger_auto_schema(
        operation_summary="Get Contest Submission List",
        manual_parameters=[
            openapi.Parameter("contest_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Contest ID"),
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Limit"),
            openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Offset"),
            openapi.Parameter("problem_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Problem ID"),
            openapi.Parameter("myself", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Myself (1=Yes)"),
            openapi.Parameter("result", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Result"),
            openapi.Parameter("username", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Username"),
        ],
        responses={200: SubmissionListSerializer(many=True)},
        tags=["Contest"]
    )
    @check_contest_permission(check_type="submissions")
    def get(self, request):
        if not request.GET.get("limit"):
            return self.error("Limit is needed")

        contest = self.contest
        submissions = Submission.objects.filter(contest_id=contest.id).select_related("problem__created_by")
        problem_id = request.GET.get("problem_id")
        myself = request.GET.get("myself")
        result = request.GET.get("result")
        username = request.GET.get("username")
        if problem_id:
            try:
                problem = Problem.objects.get(_id=problem_id, contest_id=contest.id, visible=True)
            except Problem.DoesNotExist:
                return self.error("Problem doesn't exist")
            submissions = submissions.filter(problem=problem)

        if myself and myself == "1":
            submissions = submissions.filter(user_id=request.user.id)
        elif username:
            submissions = submissions.filter(username__icontains=username)
        if result:
            submissions = submissions.filter(result=result)

        # Filter submissions made before the contest started
        if contest.status != ContestStatus.CONTEST_NOT_START:
            submissions = submissions.filter(create_time__gte=contest.start_time)

        # During rank freeze, regular users can only see their own submissions
        if contest.rule_type == ContestRuleType.ACM:
            if not contest.real_time_rank and not request.user.is_contest_admin(contest):
                submissions = submissions.filter(user_id=request.user.id)

        data = self.paginate_data(request, submissions)
        data["results"] = SubmissionListSerializer(data["results"], many=True, user=request.user).data
        return self.success(data)


class SubmissionExistsAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Check Submission Exists",
        manual_parameters=[
            openapi.Parameter("problem_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Problem ID"),
        ],
        responses={200: openapi.Response("Exists", schema=openapi.Schema(type=openapi.TYPE_BOOLEAN))},
        tags=["Submission"]
    )
    def get(self, request):
        if not request.GET.get("problem_id"):
            return self.error("Parameter error, problem_id is required")
        return self.success(request.user.is_authenticated and
                            Submission.objects.filter(problem_id=request.GET["problem_id"],
                                                      user_id=request.user.id).exists())
