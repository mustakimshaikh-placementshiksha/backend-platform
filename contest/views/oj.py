import io

import xlsxwriter
from django.http import HttpResponse
from django.utils.timezone import now
from django.core.cache import cache

from problem.models import Problem
from utils.api import APIView, validate_serializer
from utils.constants import CacheKey, CONTEST_PASSWORD_SESSION_KEY
from utils.shortcuts import datetime2str, check_is_id
from account.models import AdminType
from account.decorators import login_required, check_contest_permission, check_contest_password

from utils.constants import ContestRuleType, ContestStatus
from ..models import ContestAnnouncement, Contest, OIContestRank, ACMContestRank
from ..serializers import ContestAnnouncementSerializer
from ..serializers import ContestSerializer, ContestPasswordVerifySerializer
from ..serializers import OIContestRankSerializer, ACMContestRankSerializer



from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class ContestAnnouncementListAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves announcements for a specific contest.

    Logic Flow:
    - Lists announcements associated with the given contest ID.
    - Supports pagination via `max_id`.
    - Only returns visible announcements.
    """
    @swagger_auto_schema(
        operation_summary="Get Contest Announcement List",
        manual_parameters=[
            openapi.Parameter("contest_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Contest ID"),
            openapi.Parameter("max_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Max ID"),
        ],
        responses={200: ContestAnnouncementSerializer(many=True)},
        tags=["Contest"]
    )
    @check_contest_permission(check_type="announcements")
    def get(self, request):
        contest_id = request.GET.get("contest_id")
        if not contest_id:
            return self.error("Invalid parameter, contest_id is required")
        data = ContestAnnouncement.objects.select_related("created_by").filter(contest_id=contest_id, visible=True)
        max_id = request.GET.get("max_id")
        if max_id:
            data = data.filter(id__gt=max_id)
        return self.success(ContestAnnouncementSerializer(data, many=True).data)


class ContestAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves detailed information for a specific contest.

    Logic Flow:
    - Fetches contest by ID.
    - Returns serialized contest data along with the current server time (`now`).
    """
    @swagger_auto_schema(
        operation_summary="Get Contest Detail",
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Contest ID"),
        ],
        responses={200: ContestSerializer},
        tags=["Contest"]
    )
    def get(self, request):
        id = request.GET.get("id")
        if not id or not check_is_id(id):
            return self.error("Invalid parameter, id is required")
        try:
            contest = Contest.objects.get(id=id, visible=True)
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")
        data = ContestSerializer(contest).data
        data["now"] = datetime2str(now())
        return self.success(data)


class ContestListAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves a list of all visible contests.

    Logic Flow:
    - Filters contests by rule type (ACM/OI), status (Not Started, Ended, Underway), and keyword search.
    - Status filtering depends on current server time compared to contest start/end times.
    - Returns paginated list of contests.
    """
    @swagger_auto_schema(
        operation_summary="Get Contest List",
        manual_parameters=[
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Limit"),
            openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Offset"),
            openapi.Parameter("keyword", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Keyword"),
            openapi.Parameter("rule_type", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Rule Type"),
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Status"),
        ],
        responses={200: ContestSerializer(many=True)},
        tags=["Contest"]
    )
    def get(self, request):
        contests = Contest.objects.select_related("created_by").filter(visible=True)
        keyword = request.GET.get("keyword")
        rule_type = request.GET.get("rule_type")
        status = request.GET.get("status")
        if keyword:
            contests = contests.filter(title__contains=keyword)
        if rule_type:
            contests = contests.filter(rule_type=rule_type)
        if status:
            cur = now()
            if status == ContestStatus.CONTEST_NOT_START:
                contests = contests.filter(start_time__gt=cur)
            elif status == ContestStatus.CONTEST_ENDED:
                contests = contests.filter(end_time__lt=cur)
            else:
                contests = contests.filter(start_time__lte=cur, end_time__gte=cur)
        return self.success(self.paginate_data(request, contests, ContestSerializer))


class ContestPasswordVerifyAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Verifies the password for password-protected contests.

    Logic Flow:
    - Checks if the contest matches the provided ID and has a password set.
    - Validates the provided password.
    - If valid, stores the password in the user's session to grant access.
    """
    @swagger_auto_schema(
        operation_summary="Verify Contest Password",
        request_body=ContestPasswordVerifySerializer,
        responses={200: openapi.Response("Succeeded", schema=openapi.Schema(type=openapi.TYPE_BOOLEAN))},
        tags=["Contest"]
    )
    @validate_serializer(ContestPasswordVerifySerializer)
    @login_required
    def post(self, request):
        data = request.data
        try:
            contest = Contest.objects.get(id=data["contest_id"], visible=True, password__isnull=False)
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")
        if not check_contest_password(data["password"], contest.password):
            return self.error("Wrong password or password expired")

        # password verify OK.
        if CONTEST_PASSWORD_SESSION_KEY not in request.session:
            request.session[CONTEST_PASSWORD_SESSION_KEY] = {}
        request.session[CONTEST_PASSWORD_SESSION_KEY][contest.id] = data["password"]
        # https://docs.djangoproject.com/en/dev/topics/http/sessions/#when-sessions-are-saved
        request.session.modified = True
        return self.success(True)


class ContestAccessAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Checks if the user has access to a password-protected contest.

    Logic Flow:
    - Verifies checks if the contest ID in the user's session has a valid password stored.
    - Used by the frontend to determine if it should prompt for a password.
    """
    @swagger_auto_schema(
        operation_summary="Check Contest Access",
        manual_parameters=[
            openapi.Parameter("contest_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Contest ID"),
        ],
        responses={200: openapi.Response("Access Status", schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={"access": openapi.Schema(type=openapi.TYPE_BOOLEAN)}))},
        tags=["Contest"]
    )
    @login_required
    def get(self, request):
        contest_id = request.GET.get("contest_id")
        if not contest_id:
            return self.error()
        try:
            contest = Contest.objects.get(id=contest_id, visible=True, password__isnull=False)
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")
        session_pass = request.session.get(CONTEST_PASSWORD_SESSION_KEY, {}).get(contest.id)
        return self.success({"access": check_contest_password(session_pass, contest.password)})


class ContestRankAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves and downloads the contest leaderboard/rankings.

    Logic Flow:
    - `get_rank`: Fetches rank data from either `ACMContestRank` or `OIContestRank` based on contest type.
    - `get`:
        - Caches rank data to reduce database load.
        - Supports admin forced refresh (`force_refresh`).
        - Supports CSV download (`download_csv`) for exporting results.
            - Builds an Excel file in-memory using `xlsxwriter`.
        - Returns paginated rank data if not downloading.
    """
    def get_rank(self):
        if self.contest.rule_type == ContestRuleType.ACM:
            return ACMContestRank.objects.filter(contest=self.contest,
                                                 user__admin_type=AdminType.REGULAR_USER,
                                                 user__is_disabled=False).\
                select_related("user").order_by("-accepted_number", "total_time")
        else:
            return OIContestRank.objects.filter(contest=self.contest,
                                                user__admin_type=AdminType.REGULAR_USER,
                                                user__is_disabled=False). \
                select_related("user").order_by("-total_score")

    def column_string(self, n):
        string = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string

    @swagger_auto_schema(
        operation_summary="Get Contest Ranks",
        manual_parameters=[
            openapi.Parameter("contest_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Contest ID"),
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Limit"),
            openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Offset"),
            openapi.Parameter("force_refresh", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Force Refresh (1=Yes)"),
            openapi.Parameter("download_csv", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Download CSV"),
        ],
        responses={200: openapi.Response("Contest Ranks", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},  # Keeping it simple for now due to dynamic structure
        tags=["Contest"]
    )
    @check_contest_permission(check_type="ranks")
    def get(self, request):
        download_csv = request.GET.get("download_csv")
        force_refresh = request.GET.get("force_refresh")
        is_contest_admin = request.user.is_authenticated and request.user.is_contest_admin(self.contest)
        if self.contest.rule_type == ContestRuleType.OI:
            serializer = OIContestRankSerializer
        else:
            serializer = ACMContestRankSerializer

        if force_refresh == "1" and is_contest_admin:
            qs = self.get_rank()
        else:
            cache_key = f"{CacheKey.contest_rank_cache}:{self.contest.id}"
            qs = cache.get(cache_key)
            if not qs:
                qs = self.get_rank()
                cache.set(cache_key, qs)

        if download_csv:
            data = serializer(qs, many=True, is_contest_admin=is_contest_admin).data
            contest_problems = Problem.objects.filter(contest=self.contest, visible=True).order_by("_id")
            problem_ids = [item.id for item in contest_problems]

            f = io.BytesIO()
            workbook = xlsxwriter.Workbook(f)
            worksheet = workbook.add_worksheet()
            worksheet.write("A1", "User ID")
            worksheet.write("B1", "Username")
            worksheet.write("C1", "Real Name")
            if self.contest.rule_type == ContestRuleType.OI:
                worksheet.write("D1", "Total Score")
                for item in range(contest_problems.count()):
                    worksheet.write(self.column_string(5 + item) + "1", f"{contest_problems[item].title}")
                for index, item in enumerate(data):
                    worksheet.write_string(index + 1, 0, str(item["user"]["id"]))
                    worksheet.write_string(index + 1, 1, item["user"]["username"])
                    worksheet.write_string(index + 1, 2, item["user"]["real_name"] or "")
                    worksheet.write_string(index + 1, 3, str(item["total_score"]))
                    for k, v in item["submission_info"].items():
                        worksheet.write_string(index + 1, 4 + problem_ids.index(int(k)), str(v))
            else:
                worksheet.write("D1", "AC")
                worksheet.write("E1", "Total Submission")
                worksheet.write("F1", "Total Time")
                for item in range(contest_problems.count()):
                    worksheet.write(self.column_string(7 + item) + "1", f"{contest_problems[item].title}")

                for index, item in enumerate(data):
                    worksheet.write_string(index + 1, 0, str(item["user"]["id"]))
                    worksheet.write_string(index + 1, 1, item["user"]["username"])
                    worksheet.write_string(index + 1, 2, item["user"]["real_name"] or "")
                    worksheet.write_string(index + 1, 3, str(item["accepted_number"]))
                    worksheet.write_string(index + 1, 4, str(item["submission_number"]))
                    worksheet.write_string(index + 1, 5, str(item["total_time"]))
                    for k, v in item["submission_info"].items():
                        worksheet.write_string(index + 1, 6 + problem_ids.index(int(k)), str(v["is_ac"]))

            workbook.close()
            f.seek(0)
            response = HttpResponse(f.read())
            response["Content-Disposition"] = f"attachment; filename=content-{self.contest.id}-rank.xlsx"
            response["Content-Type"] = "application/xlsx"
            return response

        page_qs = self.paginate_data(request, qs)
        page_qs["results"] = serializer(page_qs["results"], many=True, is_contest_admin=is_contest_admin).data
        return self.success(page_qs)
