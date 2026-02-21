# import os
# import re
# import xlsxwriter

# from django.db import transaction, IntegrityError
# from django.db.models import Q
# from django.http import HttpResponse
# from django.contrib.auth.hashers import make_password

# from submission.models import Submission
# from utils.api import APIView, validate_serializer
# from utils.shortcuts import rand_str

# from ..decorators import super_admin_required
# from ..models import AdminType, ProblemPermission, User, UserProfile
# from ..serializers import EditUserSerializer, UserAdminSerializer, GenerateUserSerializer
# from ..serializers import ImportUserSeralizer


# class UserAdminAPI(APIView):
#     @validate_serializer(ImportUserSeralizer)
#     @super_admin_required
#     def post(self, request):
#         """
#         Import User
#         """
#         data = request.data["users"]

#         user_list = []
#         for user_data in data:
#             if len(user_data) != 4 or len(user_data[0]) > 32:
#                 return self.error(f"Error occurred while processing data '{user_data}'")
#             user_list.append(User(username=user_data[0], password=make_password(user_data[1]), email=user_data[2]))

#         try:
#             with transaction.atomic():
#                 ret = User.objects.bulk_create(user_list)
#                 UserProfile.objects.bulk_create([UserProfile(user=ret[i], real_name=data[i][3]) for i in range(len(ret))])
#             return self.success()
#         except IntegrityError as e:
#             # Extract detail from exception message
#             #    duplicate key value violates unique constraint "user_username_key"
#             #    DETAIL:  Key (username)=(root11) already exists.
#             return self.error(str(e).split("\n")[1])

#     @validate_serializer(EditUserSerializer)
#     @super_admin_required
#     def put(self, request):
#         """
#         Edit user api
#         """
#         data = request.data
#         try:
#             user = User.objects.get(id=data["id"])
#         except User.DoesNotExist:
#             return self.error("User does not exist")
#         if User.objects.filter(username=data["username"].lower()).exclude(id=user.id).exists():
#             return self.error("Username already exists")
#         if User.objects.filter(email=data["email"].lower()).exclude(id=user.id).exists():
#             return self.error("Email already exists")

#         pre_username = user.username
#         user.username = data["username"].lower()
#         user.email = data["email"].lower()
#         user.admin_type = data["admin_type"]
#         user.is_disabled = data["is_disabled"]

#         if data["admin_type"] == AdminType.ADMIN:
#             user.problem_permission = data["problem_permission"]
#         elif data["admin_type"] == AdminType.SUPER_ADMIN:
#             user.problem_permission = ProblemPermission.ALL
#         else:
#             user.problem_permission = ProblemPermission.NONE

#         if data["password"]:
#             user.set_password(data["password"])

#         if data["open_api"]:
#             # Avoid reset user appkey after saving changes
#             if not user.open_api:
#                 user.open_api_appkey = rand_str()
#         else:
#             user.open_api_appkey = None
#         user.open_api = data["open_api"]

#         if data["two_factor_auth"]:
#             # Avoid reset user tfa_token after saving changes
#             if not user.two_factor_auth:
#                 user.tfa_token = rand_str()
#         else:
#             user.tfa_token = None

#         user.two_factor_auth = data["two_factor_auth"]

#         user.save()
#         if pre_username != user.username:
#             Submission.objects.filter(username=pre_username).update(username=user.username)

#         UserProfile.objects.filter(user=user).update(real_name=data["real_name"])
#         return self.success(UserAdminSerializer(user).data)

#     @super_admin_required
#     def get(self, request):
#         """
#         User list api / Get user by id
#         """
#         user_id = request.GET.get("id")
#         if user_id:
#             try:
#                 user = User.objects.get(id=user_id)
#             except User.DoesNotExist:
#                 return self.error("User does not exist")
#             return self.success(UserAdminSerializer(user).data)

#         user = User.objects.all().order_by("-create_time")

#         keyword = request.GET.get("keyword", None)
#         if keyword:
#             user = user.filter(Q(username__icontains=keyword) |
#                                Q(userprofile__real_name__icontains=keyword) |
#                                Q(email__icontains=keyword))
#         return self.success(self.paginate_data(request, user, UserAdminSerializer))

#     @super_admin_required
#     def delete(self, request):
#         id = request.GET.get("id")
#         if not id:
#             return self.error("Invalid Parameter, id is required")
#         ids = id.split(",")
#         if str(request.user.id) in ids:
#             return self.error("Current user can not be deleted")
#         User.objects.filter(id__in=ids).delete()
#         return self.success()


# class GenerateUserAPI(APIView):
#     @super_admin_required
#     def get(self, request):
#         """
#         download users excel
#         """
#         file_id = request.GET.get("file_id")
#         if not file_id:
#             return self.error("Invalid Parameter, file_id is required")
#         if not re.match(r"^[a-zA-Z0-9]+$", file_id):
#             return self.error("Illegal file_id")
#         file_path = f"/tmp/{file_id}.xlsx"
#         if not os.path.isfile(file_path):
#             return self.error("File does not exist")
#         with open(file_path, "rb") as f:
#             raw_data = f.read()
#         os.remove(file_path)
#         response = HttpResponse(raw_data)
#         response["Content-Disposition"] = "attachment; filename=users.xlsx"
#         response["Content-Type"] = "application/xlsx"
#         return response

#     @validate_serializer(GenerateUserSerializer)
#     @super_admin_required
#     def post(self, request):
#         """
#         Generate User
#         """
#         data = request.data
#         number_max_length = max(len(str(data["number_from"])), len(str(data["number_to"])))
#         if number_max_length + len(data["prefix"]) + len(data["suffix"]) > 32:
#             return self.error("Username should not more than 32 characters")
#         if data["number_from"] > data["number_to"]:
#             return self.error("Start number must be lower than end number")

#         file_id = rand_str(8)
#         filename = f"/tmp/{file_id}.xlsx"
#         workbook = xlsxwriter.Workbook(filename)
#         worksheet = workbook.add_worksheet()
#         worksheet.set_column("A:B", 20)
#         worksheet.write("A1", "Username")
#         worksheet.write("B1", "Password")
#         i = 1

#         user_list = []
#         for number in range(data["number_from"], data["number_to"] + 1):
#             raw_password = rand_str(data["password_length"])
#             user = User(username=f"{data['prefix']}{number}{data['suffix']}", password=make_password(raw_password))
#             user.raw_password = raw_password
#             user_list.append(user)

#         try:
#             with transaction.atomic():

#                 ret = User.objects.bulk_create(user_list)
#                 UserProfile.objects.bulk_create([UserProfile(user=user) for user in ret])
#                 for item in user_list:
#                     worksheet.write_string(i, 0, item.username)
#                     worksheet.write_string(i, 1, item.raw_password)
#                     i += 1
#                 workbook.close()
#                 return self.success({"file_id": file_id})
#         except IntegrityError as e:
#             # Extract detail from exception message
#             #    duplicate key value violates unique constraint "user_username_key"
#             #    DETAIL:  Key (username)=(root11) already exists.
#             return self.error(str(e).split("\n")[1])
import os
import re
import xlsxwriter

from django.db import transaction, IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.contrib.auth.hashers import make_password

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from submission.models import Submission
from utils.api import APIView, validate_serializer
from utils.shortcuts import rand_str
from utils.swagger import StandardResponseSerializer

from ..decorators import super_admin_required
from ..models import AdminType, ProblemPermission, User, UserProfile
from ..serializers import (
    EditUserSerializer,
    UserAdminSerializer,
    GenerateUserSerializer,
    ImportUserSeralizer,
)

# =========================
# Admin User Management
# =========================
class UserAdminAPI(APIView):

    @swagger_auto_schema(
        operation_id="admin_users_list",
        operation_summary="Admin: Get Users / User Detail",
        operation_description=(
            "**Super Admin only.** List all users or fetch a specific user by ID.\n\n"
            "**Without `id`:** Returns a paginated list of all users, sortable by creation date.  "
            "Supports keyword search across `username`, `real_name`, and `email`.\n\n"
            "**With `id`:** Returns full details for that single user."
        ),
        manual_parameters=[
            openapi.Parameter(
                "id", openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="User's database ID. If provided, returns only that user."
            ),
            openapi.Parameter(
                "keyword", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Free-text search across username, real name, and email."
            ),
            openapi.Parameter(
                "limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                description="Number of results per page"
            ),
            openapi.Parameter(
                "offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                description="Pagination offset"
            ),
        ],
        responses={
            200: openapi.Response(
                description="User or paginated user list",
                schema=StandardResponseSerializer,
                examples={
                    "application/json (list)": {
                        "error": None,
                        "data": {"total": 10, "results": [{"id": 1, "username": "alice", "email": "a@b.com"}]}
                    }
                }
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Admin"]
    )
    @super_admin_required
    def get(self, request):
        user_id = request.GET.get("id")
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return self.error("User does not exist")
            return self.success(UserAdminSerializer(user).data)

        users = User.objects.all().order_by("-create_time")
        keyword = request.GET.get("keyword")
        if keyword:
            users = users.filter(
                Q(username__icontains=keyword)
                | Q(userprofile__real_name__icontains=keyword)
                | Q(email__icontains=keyword)
            )

        return self.success(
            self.paginate_data(request, users, UserAdminSerializer)
        )

    @swagger_auto_schema(
        operation_id="admin_users_edit",
        operation_summary="Admin: Edit User",
        operation_description=(
            "**Super Admin only.** Update any user's account details.\n\n"
            "| Field               | Notes                                                  |\n"
            "|---------------------|--------------------------------------------------------|\n"
            "| `id`                | Required – user's DB ID                               |\n"
            "| `username`          | Max 32 chars; converted to lowercase                  |\n"
            "| `email`             | Valid email; converted to lowercase                   |\n"
            "| `real_name`         | User's full name (optional)                           |\n"
            "| `password`          | Min 6 chars; leave blank to keep existing             |\n"
            "| `admin_type`        | `Regular User`, `Admin`, or `Super Admin`             |\n"
            "| `problem_permission`| `None`, `Own`, or `All`                               |\n"
            "| `open_api`          | Enable Open API / AppKey access                       |\n"
            "| `two_factor_auth`   | Enable or disable 2FA for this user                   |\n"
            "| `is_disabled`       | Lock the account                                      |\n"
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["id", "username", "email", "admin_type", "problem_permission",
                      "open_api", "two_factor_auth", "is_disabled"],
            properties={
                "id":                 openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                "username":           openapi.Schema(type=openapi.TYPE_STRING, example="alice"),
                "email":              openapi.Schema(type=openapi.TYPE_STRING, format="email", example="alice@example.com"),
                "real_name":          openapi.Schema(type=openapi.TYPE_STRING, example="Alice Smith"),
                "password":           openapi.Schema(type=openapi.TYPE_STRING, example="",
                                                     description="Leave empty to keep current password"),
                "admin_type":         openapi.Schema(type=openapi.TYPE_STRING,
                                                     enum=["Regular User", "Admin", "Super Admin"],
                                                     example="Regular User"),
                "problem_permission": openapi.Schema(type=openapi.TYPE_STRING,
                                                     enum=["None", "Own", "All"],
                                                     example="None"),
                "open_api":           openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                "two_factor_auth":    openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                "is_disabled":        openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
            },
            example={
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "real_name": "Alice Smith",
                "password": "",
                "admin_type": "Regular User",
                "problem_permission": "None",
                "open_api": False,
                "two_factor_auth": False,
                "is_disabled": False
            }
        ),
        responses={
            200: openapi.Response(
                description="Updated user data",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": {"id": 1, "username": "alice"}}}
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Admin"]
    )
    @super_admin_required
    @validate_serializer(EditUserSerializer)
    def put(self, request):
        data = request.data

        try:
            user = User.objects.get(id=data["id"])
        except User.DoesNotExist:
            return self.error("User does not exist")

        if User.objects.filter(username=data["username"].lower()).exclude(id=user.id).exists():
            return self.error("Username already exists")

        if User.objects.filter(email=data["email"].lower()).exclude(id=user.id).exists():
            return self.error("Email already exists")

        old_username = user.username
        user.username = data["username"].lower()
        user.email = data["email"].lower()
        user.admin_type = data["admin_type"]
        user.is_disabled = data["is_disabled"]

        if data["admin_type"] == AdminType.ADMIN:
            user.problem_permission = data["problem_permission"]
        elif data["admin_type"] == AdminType.SUPER_ADMIN:
            user.problem_permission = ProblemPermission.ALL
        else:
            user.problem_permission = ProblemPermission.NONE

        if data.get("password"):
            user.set_password(data["password"])

        if data["open_api"]:
            if not user.open_api:
                user.open_api_appkey = rand_str()
        else:
            user.open_api_appkey = None

        user.open_api = data["open_api"]

        if data["two_factor_auth"]:
            if not user.two_factor_auth:
                user.tfa_token = rand_str()
        else:
            user.tfa_token = None

        user.two_factor_auth = data["two_factor_auth"]
        user.save()

        if old_username != user.username:
            Submission.objects.filter(username=old_username).update(
                username=user.username
            )

        UserProfile.objects.filter(user=user).update(
            real_name=data["real_name"]
        )

        return self.success(UserAdminSerializer(user).data)

    @swagger_auto_schema(
        operation_id="admin_users_delete",
        operation_summary="Admin: Delete Users",
        operation_description=(
            "**Super Admin only.** Delete one or more users by ID.\n\n"
            "Pass comma-separated IDs in the `id` query parameter.  "
            "The currently authenticated user **cannot** delete themselves."
        ),
        manual_parameters=[
            openapi.Parameter(
                "id", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="Comma-separated user IDs to delete. Example: `1,2,5`"
            )
        ],
        responses={
            200: openapi.Response(
                description="Users deleted",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": {}}}
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Admin"]
    )
    @super_admin_required
    def delete(self, request):
        ids = request.GET.get("id")
        if not ids:
            return self.error("Invalid parameter, id required")

        id_list = ids.split(",")
        if str(request.user.id) in id_list:
            return self.error("Current user cannot be deleted")

        User.objects.filter(id__in=id_list).delete()
        return self.success()


# =========================
# Generate / Import Users
# =========================
class GenerateUserAPI(APIView):

    @swagger_auto_schema(
        operation_id="admin_users_download_excel",
        operation_summary="Admin: Download Generated Users Excel",
        operation_description=(
            "**Super Admin only.** Download the Excel file that was generated by the "
            "**Generate Users** endpoint.\n\n"
            "Use the `file_id` returned from `POST /api/account/admin/generate_user/`.  "
            "The file is deleted from disk after download."
        ),
        manual_parameters=[
            openapi.Parameter(
                "file_id", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="Alphanumeric file ID returned by Generate Users endpoint"
            )
        ],
        responses={
            200: openapi.Response(
                description="Excel file (.xlsx) download",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Admin"]
    )
    @super_admin_required
    def get(self, request):
        file_id = request.GET.get("file_id")
        if not file_id:
            return self.error("file_id is required")

        if not re.match(r"^[a-zA-Z0-9]+$", file_id):
            return self.error("Illegal file_id")

        path = f"/tmp/{file_id}.xlsx"
        if not os.path.isfile(path):
            return self.error("File does not exist")

        with open(path, "rb") as f:
            data = f.read()
        os.remove(path)

        response = HttpResponse(data, content_type="application/xlsx")
        response["Content-Disposition"] = "attachment; filename=users.xlsx"
        return response

    @swagger_auto_schema(
        operation_id="admin_users_generate",
        operation_summary="Admin: Bulk Generate Users",
        operation_description=(
            "**Super Admin only.** Batch-create users with sequential usernames.\n\n"
            "Generated usernames follow the pattern: `{prefix}{number}{suffix}`.\n"
            "Each user gets a random password of the specified length.\n\n"
            "Returns a `file_id` pointing to a downloadable Excel file — "
            "pass it to **GET /api/account/admin/generate_user/?file_id=<id>** "
            "to download the credentials sheet.\n\n"
            "| Field             | Type   | Constraint                        |\n"
            "|-------------------|--------|-----------------------------------|\n"
            "| `prefix`          | string | Max 16 chars (can be empty)       |\n"
            "| `suffix`          | string | Max 16 chars (can be empty)       |\n"
            "| `number_from`     | int    | Start number (inclusive)          |\n"
            "| `number_to`       | int    | End number (inclusive)            |\n"
            "| `password_length` | int    | 1–16 chars, default 8             |\n\n"
            "**Example:** prefix=`batch`, number_from=`1`, number_to=`5` → "
            "creates `batch1` … `batch5`"
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["prefix", "suffix", "number_from", "number_to"],
            properties={
                "prefix": openapi.Schema(
                    type=openapi.TYPE_STRING, maxLength=16,
                    description="Username prefix (e.g. 'batch', 'user', 'team1_')",
                    example="batch"
                ),
                "suffix": openapi.Schema(
                    type=openapi.TYPE_STRING, maxLength=16,
                    description="Username suffix (e.g. '_test'). Can be empty string.",
                    example=""
                ),
                "number_from": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Starting number (inclusive)",
                    example=1
                ),
                "number_to": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Ending number (inclusive). Max username = prefix+number+suffix ≤ 32 chars.",
                    example=5
                ),
                "password_length": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    minimum=1, maximum=16,
                    description="Length of the auto-generated password (default: 8)",
                    example=8
                ),
            },
            example={
                "prefix": "batch",
                "suffix": "",
                "number_from": 1,
                "number_to": 5,
                "password_length": 8
            }
        ),
        responses={
            200: openapi.Response(
                description="Returns file_id for the downloadable Excel credential sheet",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {
                        "error": None,
                        "data": {"file_id": "a1b2c3d4"}
                    }
                }
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Admin"]
    )
    @super_admin_required
    @validate_serializer(GenerateUserSerializer)
    def post(self, request):
        data = request.data

        number_len = max(
            len(str(data["number_from"])),
            len(str(data["number_to"]))
        )

        if number_len + len(data["prefix"]) + len(data["suffix"]) > 32:
            return self.error("Username should not exceed 32 characters")

        if data["number_from"] > data["number_to"]:
            return self.error("Start number must be lower than end number")

        file_id = rand_str(8)
        path = f"/tmp/{file_id}.xlsx"
        workbook = xlsxwriter.Workbook(path)
        sheet = workbook.add_worksheet()

        sheet.write("A1", "Username")
        sheet.write("B1", "Password")

        users = []
        row = 1

        for number in range(data["number_from"], data["number_to"] + 1):
            raw_password = rand_str(data["password_length"])
            username = f"{data['prefix']}{number}{data['suffix']}"
            user = User(
                username=username,
                password=make_password(raw_password)
            )
            user.raw_password = raw_password
            users.append(user)

        try:
            with transaction.atomic():
                created = User.objects.bulk_create(users)
                UserProfile.objects.bulk_create(
                    [UserProfile(user=u) for u in created]
                )

                for u in users:
                    sheet.write(row, 0, u.username)
                    sheet.write(row, 1, u.raw_password)
                    row += 1

                workbook.close()
                return self.success({"file_id": file_id})

        except IntegrityError as e:
            return self.error(str(e).split("\n")[1])
