import hashlib
import json
import os
import re
import shutil
import smtplib
import time
from datetime import datetime

import pytz
import requests
from django.conf import settings
from django.utils import timezone
from requests.exceptions import RequestException

from account.decorators import super_admin_required
from account.models import User
from contest.models import Contest
from judge.dispatcher import process_pending_task
from options.options import SysOptions
from problem.models import Problem
from submission.models import Submission
from utils.api import APIView, CSRFExemptAPIView, validate_serializer
from utils.shortcuts import send_email, get_env
from utils.xss_filter import XSSHtml
from .models import JudgeServer
from .serializers import (CreateEditWebsiteConfigSerializer,
                          CreateSMTPConfigSerializer, EditSMTPConfigSerializer,
                          JudgeServerHeartbeatSerializer,
                          JudgeServerSerializer, TestSMTPConfigSerializer, EditJudgeServerSerializer)



from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from utils.swagger import StandardResponseSerializer

class SMTPAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Get SMTP Config",
        responses={200: openapi.Response("SMTP Config", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["System Config"]
    )
    @super_admin_required
    def get(self, request):
        smtp = SysOptions.smtp_config
        if not smtp:
            return self.success(None)
        smtp.pop("password")
        return self.success(smtp)

    @swagger_auto_schema(
        operation_summary="Create SMTP Config",
        request_body=CreateSMTPConfigSerializer,
        responses={200: StandardResponseSerializer},
        tags=["System Config"]
    )
    @super_admin_required
    @validate_serializer(CreateSMTPConfigSerializer)
    def post(self, request):
        SysOptions.smtp_config = request.data
        return self.success()

    @swagger_auto_schema(
        operation_summary="Edit SMTP Config",
        request_body=EditSMTPConfigSerializer,
        responses={200: StandardResponseSerializer},
        tags=["System Config"]
    )
    @super_admin_required
    @validate_serializer(EditSMTPConfigSerializer)
    def put(self, request):
        smtp = SysOptions.smtp_config
        data = request.data
        for item in ["server", "port", "email", "tls"]:
            smtp[item] = data[item]
        if "password" in data:
            smtp["password"] = data["password"]
        SysOptions.smtp_config = smtp
        return self.success()


class SMTPTestAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Test SMTP Config",
        request_body=TestSMTPConfigSerializer,
        responses={200: StandardResponseSerializer},
        tags=["System Config"]
    )
    @super_admin_required
    @validate_serializer(TestSMTPConfigSerializer)
    def post(self, request):
        if not SysOptions.smtp_config:
            return self.error("Please setup SMTP config at first")
        try:
            send_email(smtp_config=SysOptions.smtp_config,
                       from_name=SysOptions.website_name_shortcut,
                       to_name=request.user.username,
                       to_email=request.data["email"],
                       subject="You have successfully configured SMTP",
                       content="You have successfully configured SMTP")
        except smtplib.SMTPResponseException as e:
            # guess error message encoding
            msg = b"Failed to send email"
            try:
                msg = e.smtp_error
                # qq mail
                msg = msg.decode("gbk")
            except Exception:
                msg = msg.decode("utf-8", "ignore")
            return self.error(msg)
        except Exception as e:
            msg = str(e)
            return self.error(msg)
        return self.success()


class WebsiteConfigAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Get Website Config",
        responses={200: openapi.Response("Website Config", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["System Config"]
    )
    def get(self, request):
        ret = {key: getattr(SysOptions, key) for key in
               ["website_base_url", "website_name", "website_name_shortcut",
                "website_footer", "allow_register", "submission_list_show_all"]}
        return self.success(ret)

    @swagger_auto_schema(
        operation_summary="Edit Website Config",
        request_body=CreateEditWebsiteConfigSerializer,
        responses={200: StandardResponseSerializer},
        tags=["System Config"]
    )
    @super_admin_required
    @validate_serializer(CreateEditWebsiteConfigSerializer)
    def post(self, request):
        for k, v in request.data.items():
            if k == "website_footer":
                with XSSHtml() as parser:
                    v = parser.clean(v)
            setattr(SysOptions, k, v)
        return self.success()


class JudgeServerAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Get Judge Server List",
        responses={200: openapi.Response("Judge Servers", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["System Config"]
    )
    @super_admin_required
    def get(self, request):
        servers = JudgeServer.objects.all().order_by("-last_heartbeat")
        return self.success({"token": SysOptions.judge_server_token,
                             "servers": JudgeServerSerializer(servers, many=True).data})

    @swagger_auto_schema(
        operation_summary="Delete Judge Server",
        manual_parameters=[
            openapi.Parameter("hostname", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Hostname")
        ],
        responses={200: StandardResponseSerializer},
        tags=["System Config"]
    )
    @super_admin_required
    def delete(self, request):
        hostname = request.GET.get("hostname")
        if hostname:
            JudgeServer.objects.filter(hostname=hostname).delete()
        return self.success()

    @swagger_auto_schema(
        operation_summary="Edit Judge Server",
        request_body=EditJudgeServerSerializer,
        responses={200: StandardResponseSerializer},
        tags=["System Config"]
    )
    @validate_serializer(EditJudgeServerSerializer)
    @super_admin_required
    def put(self, request):
        is_disabled = request.data.get("is_disabled", False)
        JudgeServer.objects.filter(id=request.data["id"]).update(is_disabled=is_disabled)
        if not is_disabled:
            process_pending_task()
        return self.success()


class JudgeServerHeartbeatAPI(CSRFExemptAPIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles heartbeat signals from judge servers.

    Logic Flow:
    - Validates the judge server token.
    - Updates or creates a `JudgeServer` record with current metrics (CPU, memory, etc.).
    - Triggers `process_pending_task` to ensure new servers immediately pick up pending tasks.
    """
    @swagger_auto_schema(
        operation_summary="Judge Server Heartbeat",
        request_body=JudgeServerHeartbeatSerializer,
        responses={200: StandardResponseSerializer},
        tags=["System Config"]
    )
    @validate_serializer(JudgeServerHeartbeatSerializer)
    def post(self, request):
        data = request.data
        client_token = request.META.get("HTTP_X_JUDGE_SERVER_TOKEN")
        if hashlib.sha256(SysOptions.judge_server_token.encode("utf-8")).hexdigest() != client_token:
            return self.error("Invalid token")

        try:
            server = JudgeServer.objects.get(hostname=data["hostname"])
            server.judger_version = data["judger_version"]
            server.cpu_core = data["cpu_core"]
            server.memory_usage = data["memory"]
            server.cpu_usage = data["cpu"]
            server.service_url = data["service_url"]
            server.ip = request.ip
            server.last_heartbeat = timezone.now()
            server.save(update_fields=["judger_version", "cpu_core", "memory_usage", "service_url", "ip", "last_heartbeat"])
        except JudgeServer.DoesNotExist:
            JudgeServer.objects.create(hostname=data["hostname"],
                                       judger_version=data["judger_version"],
                                       cpu_core=data["cpu_core"],
                                       memory_usage=data["memory"],
                                       cpu_usage=data["cpu"],
                                       ip=request.META["REMOTE_ADDR"],
                                       service_url=data["service_url"],
                                       last_heartbeat=timezone.now(),
                                       )
        # Process pending tasks when a server comes online/heartbeats to avoid tasks getting stuck
        process_pending_task()

        return self.success()


class LanguagesAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Get Languages",
        responses={200: openapi.Response("Languages", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["System Config"]
    )
    def get(self, request):
        return self.success({"languages": SysOptions.languages, "spj_languages": SysOptions.spj_languages})


class TestCasePruneAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Get Orphan Test Cases",
        responses={200: openapi.Response("Orphan Test Cases", schema=openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)))},
        tags=["System Config"]
    )
    @super_admin_required
    def get(self, request):
        """
        return orphan test_case list
        """
        ret_data = []
        dir_to_be_removed = self.get_orphan_ids()

        # return an iterator
        for d in os.scandir(settings.TEST_CASE_DIR):
            if d.name in dir_to_be_removed:
                ret_data.append({"id": d.name, "create_time": d.stat().st_mtime})
        return self.success(ret_data)

    @swagger_auto_schema(
        operation_summary="Delete Orphan Test Cases",
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Test Case ID")
        ],
        responses={200: StandardResponseSerializer},
        tags=["System Config"]
    )
    @super_admin_required
    def delete(self, request):
        test_case_id = request.GET.get("id")
        if test_case_id:
            self.delete_one(test_case_id)
            return self.success()
        for id in self.get_orphan_ids():
            self.delete_one(id)
        return self.success()

    @staticmethod
    def get_orphan_ids():
        db_ids = Problem.objects.all().values_list("test_case_id", flat=True)
        disk_ids = os.listdir(settings.TEST_CASE_DIR)
        test_case_re = re.compile(r"^[a-zA-Z0-9]{32}$")
        disk_ids = filter(lambda f: test_case_re.match(f), disk_ids)
        return list(set(disk_ids) - set(db_ids))

    @staticmethod
    def delete_one(id):
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, id)
        if os.path.isdir(test_case_dir):
            shutil.rmtree(test_case_dir, ignore_errors=True)


class ReleaseNotesAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Get Release Notes",
        responses={200: openapi.Response("Release Notes", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["System Config"]
    )
    def get(self, request):
        try:
            resp = requests.get("https://raw.githubusercontent.com/QingdaoU/OnlineJudge/master/docs/data.json?_=" + str(time.time()),
                                timeout=3)
            releases = resp.json()
        except (RequestException, ValueError):
            return self.success()
        with open("docs/data.json", "r") as f:
            local_version = json.load(f)["update"][0]["version"]
        releases["local_version"] = local_version
        return self.success(releases)


class DashboardInfoAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Get Dashboard Info",
        responses={200: openapi.Response("Dashboard Info", schema=openapi.Schema(type=openapi.TYPE_OBJECT))},
        tags=["System Config"]
    )
    def get(self, request):
        today = datetime.today()
        today_submission_count = Submission.objects.filter(
            create_time__gte=datetime(today.year, today.month, today.day, 0, 0, tzinfo=pytz.UTC)).count()
        recent_contest_count = Contest.objects.exclude(end_time__lt=timezone.now()).count()
        judge_server_count = len(list(filter(lambda x: x.status == "normal", JudgeServer.objects.all())))
        return self.success({
            "user_count": User.objects.count(),
            "recent_contest_count": recent_contest_count,
            "today_submission_count": today_submission_count,
            "judge_server_count": judge_server_count,
            "env": {
                "FORCE_HTTPS": get_env("FORCE_HTTPS", default=False),
                "STATIC_CDN_HOST": get_env("STATIC_CDN_HOST", default="")
            }
        })
