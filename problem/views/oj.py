import random
from django.db.models import Q, Count
from utils.api import APIView
from account.decorators import check_contest_permission
from ..models import ProblemTag, Problem, ProblemRuleType
from ..serializers import ProblemSerializer, TagSerializer, ProblemSafeSerializer
from contest.models import ContestRuleType



from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class ProblemTagAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves a list of problem tags.

    Logic Flow:
    - Filters tags by keyword if provided.
    - Only returns tags that are associated with at least one problem.
    """
    @swagger_auto_schema(
        operation_summary="Get Problem Tags",
        manual_parameters=[
            openapi.Parameter("keyword", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Keyword"),
        ],
        responses={200: TagSerializer(many=True)},
        tags=["Problem"]
    )
    def get(self, request):
        qs = ProblemTag.objects
        keyword = request.GET.get("keyword")
        if keyword:
            qs = ProblemTag.objects.filter(name__icontains=keyword)
        tags = qs.annotate(problem_count=Count("problem")).filter(problem_count__gt=0)
        return self.success(TagSerializer(tags, many=True).data)


class PickOneAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Selects a random problem for the user to solve.

    Logic Flow:
    - Filters for visible problems that are not part of a contest.
    - Returns a random problem ID.
    """
    @swagger_auto_schema(
        operation_summary="Pick One Problem",
        responses={200: openapi.Response("Problem ID", schema=openapi.Schema(type=openapi.TYPE_STRING))},
        tags=["Problem"]
    )
    def get(self, request):
        problems = Problem.objects.filter(contest_id__isnull=True, visible=True)
        count = problems.count()
        if count == 0:
            return self.error("No problem to pick")
        return self.success(problems[random.randint(0, count - 1)]._id)


class ProblemAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles retrieving problem lists and details.

    Logic Flow:
    - `_add_problem_status`: Helper to inject the user's solve status (Accepted, Wrong Answer, etc.) into the problem data.
    - GET (List):
        - Filters by tags, search keywords, difficulty.
        - Only shows visible problems not part of a contest.
        - Supports pagination.
    - GET (Detail):
        - Retrieves a single problem by its display ID (`_id`).
        - Injects user status if authenticated.
    """
    @staticmethod
    def _add_problem_status(request, queryset_values):
        if request.user.is_authenticated:
            profile = request.user.userprofile
            acm_problems_status = profile.acm_problems_status.get("problems", {})
            oi_problems_status = profile.oi_problems_status.get("problems", {})
            # paginate data
            results = queryset_values.get("results")
            if results is not None:
                problems = results
            else:
                problems = [queryset_values, ]
            for problem in problems:
                if problem["rule_type"] == ProblemRuleType.ACM:
                    problem["my_status"] = acm_problems_status.get(str(problem["id"]), {}).get("status")
                else:
                    problem["my_status"] = oi_problems_status.get(str(problem["id"]), {}).get("status")

    @swagger_auto_schema(
        operation_summary="Get Problem List / Detail",
        manual_parameters=[
            openapi.Parameter("problem_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Problem ID (Display ID)"),
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Limit"),
            openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Offset"),
            openapi.Parameter("tag", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Tag Name"),
            openapi.Parameter("keyword", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Keyword"),
            openapi.Parameter("difficulty", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Difficulty"),
        ],
        responses={200: ProblemSerializer(many=True)},
        tags=["Problem"]
    )
    def get(self, request):
        # Problem Detail Page
        problem_id = request.GET.get("problem_id")
        if problem_id:
            try:
                problem = Problem.objects.select_related("created_by") \
                    .get(_id=problem_id, contest_id__isnull=True, visible=True)
                problem_data = ProblemSerializer(problem).data
                self._add_problem_status(request, problem_data)
                return self.success(problem_data)
            except Problem.DoesNotExist:
                return self.error("Problem does not exist")

        limit = request.GET.get("limit")
        if not limit:
            return self.error("Limit is needed")

        problems = Problem.objects.select_related("created_by").filter(contest_id__isnull=True, visible=True)
        # Filter by Tag
        tag_text = request.GET.get("tag")
        if tag_text:
            problems = problems.filter(tags__name=tag_text)

        # Search functionality
        keyword = request.GET.get("keyword", "").strip()
        if keyword:
            problems = problems.filter(Q(title__icontains=keyword) | Q(_id__icontains=keyword))

        # Difficulty filtering
        difficulty = request.GET.get("difficulty")
        if difficulty:
            problems = problems.filter(difficulty=difficulty)
        # Add solved status for authenticated users
        data = self.paginate_data(request, problems, ProblemSerializer)
        self._add_problem_status(request, data)
        return self.success(data)


class ContestProblemAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles retrieving problems within a specific contest.

    Logic Flow:
    - `_add_problem_status`: Similar to `ProblemAPI`, but uses contest-specific status storage.
    - GET:
        - Checks contest permissions (e.g., if user is participant/admin).
        - List: Returns all visible problems for the contest.
        - Detail: Returns a specific problem's details.
        - If the user has permission (e.g., admin or contest ended), returns full problem data.
        - Otherwise (e.g., contest running), returns "Safe" serializer data (might hide hidden test cases or sensitive info).
    """
    def _add_problem_status(self, request, queryset_values):
        if request.user.is_authenticated:
            profile = request.user.userprofile
            if self.contest.rule_type == ContestRuleType.ACM:
                problems_status = profile.acm_problems_status.get("contest_problems", {})
            else:
                problems_status = profile.oi_problems_status.get("contest_problems", {})
            for problem in queryset_values:
                problem["my_status"] = problems_status.get(str(problem["id"]), {}).get("status")

    @swagger_auto_schema(
        operation_summary="Get Contest Problem List / Detail",
        manual_parameters=[
            openapi.Parameter("contest_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Contest ID"),
            openapi.Parameter("problem_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Problem ID"),
        ],
        responses={200: ProblemSerializer(many=True)},
        tags=["Contest"]
    )
    @check_contest_permission(check_type="problems")
    def get(self, request):
        problem_id = request.GET.get("problem_id")
        if problem_id:
            try:
                problem = Problem.objects.select_related("created_by").get(_id=problem_id,
                                                                           contest=self.contest,
                                                                           visible=True)
            except Problem.DoesNotExist:
                return self.error("Problem does not exist.")
            if self.contest.problem_details_permission(request.user):
                problem_data = ProblemSerializer(problem).data
                self._add_problem_status(request, [problem_data, ])
            else:
                problem_data = ProblemSafeSerializer(problem).data
            return self.success(problem_data)

        contest_problems = Problem.objects.select_related("created_by").filter(contest=self.contest, visible=True)
        if self.contest.problem_details_permission(request.user):
            data = ProblemSerializer(contest_problems, many=True).data
            self._add_problem_status(request, data)
        else:
            data = ProblemSafeSerializer(contest_problems, many=True).data
        return self.success(data)
