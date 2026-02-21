import copy
import os
import zipfile
from ipaddress import ip_network

import dateutil.parser
from django.http import FileResponse

from account.decorators import check_contest_permission, ensure_created_by
from account.models import User
from submission.models import Submission, JudgeStatus
from utils.api import APIView, validate_serializer
from utils.cache import cache
from utils.constants import CacheKey
from utils.shortcuts import rand_str
from utils.tasks import delete_files
from ..models import Contest, ContestAnnouncement, ACMContestRank
from ..serializers import (ContestAnnouncementSerializer, ContestAdminSerializer,
                           CreateConetestSeriaizer, CreateContestAnnouncementSerializer,
                           EditConetestSeriaizer, EditContestAnnouncementSerializer,
                           ACMContesHelperSerializer, )



from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from utils.swagger import StandardResponseSerializer

class ContestAPI(APIView):
    @swagger_auto_schema(
        operation_id="contest_admin_create",
        operation_summary="Admin: Create Contest",
        operation_description=(
            "**Admin only.** Create a new contest.\n\n"
            "- `start_time` / `end_time`: ISO8601 datetime strings (e.g. `2026-03-01T10:00:00`).\n"
            "- `rule_type`: `ACM` or `OI`\n"
            "- `contest_type`: `Public` or `Password Protected`\n"
            "- `allowed_ip_ranges`: CIDR networks to restrict participation (empty = no restriction)"
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["title", "description", "start_time", "end_time", "rule_type", "contest_type"],
            properties={
                "title":             openapi.Schema(type=openapi.TYPE_STRING, example="Spring 2026 ACM Contest"),
                "description":       openapi.Schema(type=openapi.TYPE_STRING, example="Spring semester competitive programming contest."),
                "start_time":        openapi.Schema(type=openapi.TYPE_STRING, format="date-time", example="2026-03-01T10:00:00"),
                "end_time":          openapi.Schema(type=openapi.TYPE_STRING, format="date-time", example="2026-03-01T13:00:00"),
                "rule_type":         openapi.Schema(type=openapi.TYPE_STRING, enum=["ACM", "OI"], example="ACM"),
                "contest_type":      openapi.Schema(type=openapi.TYPE_STRING, enum=["Public", "Password Protected"], example="Public"),
                "password":          openapi.Schema(type=openapi.TYPE_STRING, example="",
                                                    description="Required only if contest_type is 'Password Protected'"),
                "real_time_rank":    openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True,
                                                    description="Show live leaderboard during contest"),
                "allowed_ip_ranges": openapi.Schema(type=openapi.TYPE_ARRAY,
                                                    items=openapi.Schema(type=openapi.TYPE_STRING),
                                                    example=[],
                                                    description="IP CIDR ranges allowed to participate, empty = unrestricted"),
            },
            example={
                "title": "Spring 2026 ACM Contest",
                "description": "Spring semester competitive programming contest.",
                "start_time": "2026-03-01T10:00:00",
                "end_time": "2026-03-01T13:00:00",
                "rule_type": "ACM",
                "contest_type": "Public",
                "password": "",
                "real_time_rank": True,
                "allowed_ip_ranges": []
            }
        ),
        responses={200: ContestAdminSerializer},
        tags=["Contest Admin"]
    )
    @validate_serializer(CreateConetestSeriaizer)
    def post(self, request):
        data = request.data
        data["start_time"] = dateutil.parser.parse(data["start_time"])
        data["end_time"] = dateutil.parser.parse(data["end_time"])
        data["created_by"] = request.user
        if data["end_time"] <= data["start_time"]:
            return self.error("Start time must occur earlier than end time")
        if data.get("password") and data["password"] == "":
            data["password"] = None
        for ip_range in data["allowed_ip_ranges"]:
            try:
                ip_network(ip_range, strict=False)
            except ValueError:
                return self.error(f"{ip_range} is not a valid cidr network")
        contest = Contest.objects.create(**data)
        return self.success(ContestAdminSerializer(contest).data)

    @swagger_auto_schema(
        operation_id="contest_admin_edit",
        operation_summary="Admin: Edit Contest",
        operation_description=(
            "**Admin only.** Update an existing contest. Include `id` to specify which contest to edit."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["id", "title", "description", "start_time", "end_time", "rule_type", "contest_type"],
            properties={
                "id":                openapi.Schema(type=openapi.TYPE_INTEGER, example=1,
                                                   description="Contest ID to edit"),
                "title":             openapi.Schema(type=openapi.TYPE_STRING, example="Spring 2026 ACM Contest (Updated)"),
                "description":       openapi.Schema(type=openapi.TYPE_STRING, example="Updated description."),
                "start_time":        openapi.Schema(type=openapi.TYPE_STRING, format="date-time", example="2026-03-01T10:00:00"),
                "end_time":          openapi.Schema(type=openapi.TYPE_STRING, format="date-time", example="2026-03-01T14:00:00"),
                "rule_type":         openapi.Schema(type=openapi.TYPE_STRING, enum=["ACM", "OI"], example="ACM"),
                "contest_type":      openapi.Schema(type=openapi.TYPE_STRING, enum=["Public", "Password Protected"], example="Public"),
                "password":          openapi.Schema(type=openapi.TYPE_STRING, example=""),
                "real_time_rank":    openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                "allowed_ip_ranges": openapi.Schema(type=openapi.TYPE_ARRAY,
                                                    items=openapi.Schema(type=openapi.TYPE_STRING), example=[]),
            },
            example={
                "id": 1,
                "title": "Spring 2026 ACM Contest (Updated)",
                "description": "Updated description.",
                "start_time": "2026-03-01T10:00:00",
                "end_time": "2026-03-01T14:00:00",
                "rule_type": "ACM",
                "contest_type": "Public",
                "password": "",
                "real_time_rank": True,
                "allowed_ip_ranges": []
            }
        ),
        responses={200: ContestAdminSerializer},
        tags=["Contest Admin"]
    )
    @validate_serializer(EditConetestSeriaizer)
    def put(self, request):
        data = request.data
        try:
            contest = Contest.objects.get(id=data.pop("id"))
            ensure_created_by(contest, request.user)
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")
        data["start_time"] = dateutil.parser.parse(data["start_time"])
        data["end_time"] = dateutil.parser.parse(data["end_time"])
        if data["end_time"] <= data["start_time"]:
            return self.error("Start time must occur earlier than end time")
        if not data["password"]:
            data["password"] = None
        for ip_range in data["allowed_ip_ranges"]:
            try:
                ip_network(ip_range, strict=False)
            except ValueError:
                return self.error(f"{ip_range} is not a valid cidr network")
        if not contest.real_time_rank and data.get("real_time_rank"):
            cache_key = f"{CacheKey.contest_rank_cache}:{contest.id}"
            cache.delete(cache_key)

        for k, v in data.items():
            setattr(contest, k, v)
        contest.save()
        return self.success(ContestAdminSerializer(contest).data)

    @swagger_auto_schema(
        operation_summary="Get Contest List",
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Contest ID"),
            openapi.Parameter("keyword", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Keyword"),
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Limit"),
            openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Offset"),
        ],
        responses={200: ContestAdminSerializer(many=True)},
        tags=["Contest Admin"]
    )
    def get(self, request):
        contest_id = request.GET.get("id")
        if contest_id:
            try:
                contest = Contest.objects.get(id=contest_id)
                ensure_created_by(contest, request.user)
                return self.success(ContestAdminSerializer(contest).data)
            except Contest.DoesNotExist:
                return self.error("Contest does not exist")

        contests = Contest.objects.all().order_by("-create_time")
        if request.user.is_admin():
            contests = contests.filter(created_by=request.user)

        keyword = request.GET.get("keyword")
        if keyword:
            contests = contests.filter(title__contains=keyword)
        return self.success(self.paginate_data(request, contests, ContestAdminSerializer))


class ContestAnnouncementAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Create Contest Announcement",
        request_body=CreateContestAnnouncementSerializer,
        responses={200: ContestAnnouncementSerializer},
        tags=["Contest Admin"]
    )
    @validate_serializer(CreateContestAnnouncementSerializer)
    def post(self, request):
        """
        Create one contest_announcement.
        """
        data = request.data
        try:
            contest = Contest.objects.get(id=data.pop("contest_id"))
            ensure_created_by(contest, request.user)
            data["contest"] = contest
            data["created_by"] = request.user
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")
        announcement = ContestAnnouncement.objects.create(**data)
        return self.success(ContestAnnouncementSerializer(announcement).data)

    @swagger_auto_schema(
        operation_summary="Edit Contest Announcement",
        request_body=EditContestAnnouncementSerializer,
        responses={200: openapi.Response("Succeeded", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["Contest Admin"]
    )
    @validate_serializer(EditContestAnnouncementSerializer)
    def put(self, request):
        """
        update contest_announcement
        """
        data = request.data
        try:
            contest_announcement = ContestAnnouncement.objects.get(id=data.pop("id"))
            ensure_created_by(contest_announcement, request.user)
        except ContestAnnouncement.DoesNotExist:
            return self.error("Contest announcement does not exist")
        for k, v in data.items():
            setattr(contest_announcement, k, v)
        contest_announcement.save()
        return self.success()

    @swagger_auto_schema(
        operation_summary="Delete Contest Announcement",
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Announcement ID")
        ],
        responses={200: StandardResponseSerializer},
        tags=["Contest Admin"]
    )
    def delete(self, request):
        """
        Delete one contest_announcement.
        """
        contest_announcement_id = request.GET.get("id")
        if contest_announcement_id:
            if request.user.is_admin():
                ContestAnnouncement.objects.filter(id=contest_announcement_id,
                                                   contest__created_by=request.user).delete()
            else:
                ContestAnnouncement.objects.filter(id=contest_announcement_id).delete()
        return self.success()

    @swagger_auto_schema(
        operation_summary="Get Contest Announcement List",
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Announcement ID"),
            openapi.Parameter("contest_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Contest ID"),
            openapi.Parameter("keyword", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Keyword"),
        ],
        responses={200: ContestAnnouncementSerializer(many=True)},
        tags=["Contest Admin"]
    )
    def get(self, request):
        """
        Get one contest_announcement or contest_announcement list.
        """
        contest_announcement_id = request.GET.get("id")
        if contest_announcement_id:
            try:
                contest_announcement = ContestAnnouncement.objects.get(id=contest_announcement_id)
                ensure_created_by(contest_announcement, request.user)
                return self.success(ContestAnnouncementSerializer(contest_announcement).data)
            except ContestAnnouncement.DoesNotExist:
                return self.error("Contest announcement does not exist")

        contest_id = request.GET.get("contest_id")
        if not contest_id:
            return self.error("Parameter error")
        contest_announcements = ContestAnnouncement.objects.filter(contest_id=contest_id)
        if request.user.is_admin():
            contest_announcements = contest_announcements.filter(created_by=request.user)
        keyword = request.GET.get("keyword")
        if keyword:
            contest_announcements = contest_announcements.filter(title__contains=keyword)
        return self.success(ContestAnnouncementSerializer(contest_announcements, many=True).data)


class ACMContestHelper(APIView):
    @swagger_auto_schema(
        operation_summary="Get ACM Contest Ranks",
        manual_parameters=[
            openapi.Parameter("contest_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Contest ID"),
        ],
        responses={200: openapi.Response("Ranks", schema=openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)))},
        tags=["Contest Admin"]
    )
    @check_contest_permission(check_type="ranks")
    def get(self, request):
        ranks = ACMContestRank.objects.filter(contest=self.contest, accepted_number__gt=0) \
            .values("id", "user__username", "user__userprofile__real_name", "submission_info")
        results = []
        for rank in ranks:
            for problem_id, info in rank["submission_info"].items():
                if info["is_ac"]:
                    results.append({
                        "id": rank["id"],
                        "username": rank["user__username"],
                        "real_name": rank["user__userprofile__real_name"],
                        "problem_id": problem_id,
                        "ac_info": info,
                        "checked": info.get("checked", False)
                    })
        results.sort(key=lambda x: -x["ac_info"]["ac_time"])
        return self.success(results)

    @swagger_auto_schema(
        operation_summary="Update ACM Contest Rank Status",
        request_body=ACMContesHelperSerializer,
        responses={200: openapi.Response("Succeeded", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["Contest Admin"]
    )
    @check_contest_permission(check_type="ranks")
    @validate_serializer(ACMContesHelperSerializer)
    def put(self, request):
        data = request.data
        try:
            rank = ACMContestRank.objects.get(pk=data["rank_id"])
        except ACMContestRank.DoesNotExist:
            return self.error("Rank id does not exist")
        problem_rank_status = rank.submission_info.get(data["problem_id"])
        if not problem_rank_status:
            return self.error("Problem id does not exist")
        problem_rank_status["checked"] = data["checked"]
        rank.save(update_fields=("submission_info",))
        return self.success()


class DownloadContestSubmissions(APIView):
    def _dump_submissions(self, contest, exclude_admin=True):
        problem_ids = contest.problem_set.all().values_list("id", "_id")
        id2display_id = {k[0]: k[1] for k in problem_ids}
        ac_map = {k[0]: False for k in problem_ids}
        submissions = Submission.objects.filter(contest=contest, result=JudgeStatus.ACCEPTED).order_by("-create_time")
        user_ids = submissions.values_list("user_id", flat=True)
        users = User.objects.filter(id__in=user_ids)
        path = f"/tmp/{rand_str()}.zip"
        with zipfile.ZipFile(path, "w") as zip_file:
            for user in users:
                if user.is_admin_role() and exclude_admin:
                    continue
                user_ac_map = copy.deepcopy(ac_map)
                user_submissions = submissions.filter(user_id=user.id)
                for submission in user_submissions:
                    problem_id = submission.problem_id
                    if user_ac_map[problem_id]:
                        continue
                    file_name = f"{user.username}_{id2display_id[submission.problem_id]}.txt"
                    compression = zipfile.ZIP_DEFLATED
                    zip_file.writestr(zinfo_or_arcname=f"{file_name}",
                                      data=submission.code,
                                      compress_type=compression)
                    user_ac_map[problem_id] = True
        return path

    @swagger_auto_schema(
        operation_summary="Download Contest Submissions",
        manual_parameters=[
            openapi.Parameter("contest_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="Contest ID"),
            openapi.Parameter("exclude_admin", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Exclude Admin (1=Yes)"),
        ],
        responses={200: openapi.Response("File Download", schema=openapi.Schema(type=openapi.TYPE_FILE))},
        tags=["Contest Admin"]
    )
    def get(self, request):
        contest_id = request.GET.get("contest_id")
        if not contest_id:
            return self.error("Parameter error")
        try:
            contest = Contest.objects.get(id=contest_id)
            ensure_created_by(contest, request.user)
        except Contest.DoesNotExist:
            return self.error("Contest does not exist")

        exclude_admin = request.GET.get("exclude_admin") == "1"
        zip_path = self._dump_submissions(contest, exclude_admin)
        delete_files.send_with_options(args=(zip_path,), delay=300_000)
        resp = FileResponse(open(zip_path, "rb"))
        resp["Content-Type"] = "application/zip"
        resp["Content-Disposition"] = f"attachment;filename={os.path.basename(zip_path)}"
        return resp
