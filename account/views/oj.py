# import os
# from datetime import timedelta
# from importlib import import_module

# import qrcode
# from django.conf import settings
# from django.contrib import auth
# from django.template.loader import render_to_string
# from django.utils.decorators import method_decorator
# from django.utils.timezone import now
# from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
# from otpauth import OtpAuth

# from problem.models import Problem
# from utils.constants import ContestRuleType
# from options.options import SysOptions
# from utils.api import APIView, validate_serializer, CSRFExemptAPIView
# from utils.captcha import Captcha
# from utils.shortcuts import rand_str, img2base64, datetime2str
# from ..decorators import login_required
# from ..models import User, UserProfile, AdminType
# from ..serializers import (ApplyResetPasswordSerializer, ResetPasswordSerializer,
#                            UserChangePasswordSerializer, UserLoginSerializer,
#                            UserRegisterSerializer, UsernameOrEmailCheckSerializer,
#                            RankInfoSerializer, UserChangeEmailSerializer, SSOSerializer)
# from ..serializers import (TwoFactorAuthCodeSerializer, UserProfileSerializer,
#                            EditUserProfileSerializer, ImageUploadForm)
# from ..tasks import send_email_async


# class UserProfileAPI(APIView):
#     @method_decorator(ensure_csrf_cookie)
#     def get(self, request, **kwargs):
#         """
#         判断是否登录， 若登录返回用户信息
#         """
#         user = request.user
#         if not user.is_authenticated:
#             return self.success()
#         show_real_name = False
#         username = request.GET.get("username")
#         try:
#             if username:
#                 user = User.objects.get(username=username, is_disabled=False)
#             else:
#                 user = request.user
#                 # api返回的是自己的信息，可以返real_name
#                 show_real_name = True
#         except User.DoesNotExist:
#             return self.error("User does not exist")
#         return self.success(UserProfileSerializer(user.userprofile, show_real_name=show_real_name).data)

#     @validate_serializer(EditUserProfileSerializer)
#     @login_required
#     def put(self, request):
#         data = request.data
#         user_profile = request.user.userprofile
#         for k, v in data.items():
#             setattr(user_profile, k, v)
#         user_profile.save()
#         return self.success(UserProfileSerializer(user_profile, show_real_name=True).data)


# class AvatarUploadAPI(APIView):
#     request_parsers = ()

#     @login_required
#     def post(self, request):
#         form = ImageUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             avatar = form.cleaned_data["image"]
#         else:
#             return self.error("Invalid file content")
#         if avatar.size > 2 * 1024 * 1024:
#             return self.error("Picture is too large")
#         suffix = os.path.splitext(avatar.name)[-1].lower()
#         if suffix not in [".gif", ".jpg", ".jpeg", ".bmp", ".png"]:
#             return self.error("Unsupported file format")

#         name = rand_str(10) + suffix
#         with open(os.path.join(settings.AVATAR_UPLOAD_DIR, name), "wb") as img:
#             for chunk in avatar:
#                 img.write(chunk)
#         user_profile = request.user.userprofile

#         user_profile.avatar = f"{settings.AVATAR_URI_PREFIX}/{name}"
#         user_profile.save()
#         return self.success("Succeeded")


# class TwoFactorAuthAPI(APIView):
#     @login_required
#     def get(self, request):
#         """
#         Get QR code
#         """
#         user = request.user
#         if user.two_factor_auth:
#             return self.error("2FA is already turned on")
#         token = rand_str()
#         user.tfa_token = token
#         user.save()

#         label = f"{SysOptions.website_name_shortcut}:{user.username}"
#         image = qrcode.make(OtpAuth(token).to_uri("totp", label, SysOptions.website_name.replace(" ", "")))
#         return self.success(img2base64(image))

#     @login_required
#     @validate_serializer(TwoFactorAuthCodeSerializer)
#     def post(self, request):
#         """
#         Open 2FA
#         """
#         code = request.data["code"]
#         user = request.user
#         if OtpAuth(user.tfa_token).valid_totp(code):
#             user.two_factor_auth = True
#             user.save()
#             return self.success("Succeeded")
#         else:
#             return self.error("Invalid code")

#     @login_required
#     @validate_serializer(TwoFactorAuthCodeSerializer)
#     def put(self, request):
#         code = request.data["code"]
#         user = request.user
#         if not user.two_factor_auth:
#             return self.error("2FA is already turned off")
#         if OtpAuth(user.tfa_token).valid_totp(code):
#             user.two_factor_auth = False
#             user.save()
#             return self.success("Succeeded")
#         else:
#             return self.error("Invalid code")


# class CheckTFARequiredAPI(APIView):
#     @validate_serializer(UsernameOrEmailCheckSerializer)
#     def post(self, request):
#         """
#         Check TFA is required
#         """
#         data = request.data
#         result = False
#         if data.get("username"):
#             try:
#                 user = User.objects.get(username=data["username"])
#                 result = user.two_factor_auth
#             except User.DoesNotExist:
#                 pass
#         return self.success({"result": result})


# class UserLoginAPI(APIView):
#     @validate_serializer(UserLoginSerializer)
#     def post(self, request):
#         """
#         User login api
#         """
#         data = request.data
#         user = auth.authenticate(username=data["username"], password=data["password"])
#         # None is returned if username or password is wrong
#         if user:
#             if user.is_disabled:
#                 return self.error("Your account has been disabled")
#             if not user.two_factor_auth:
#                 auth.login(request, user)
#                 return self.success("Succeeded")

#             # `tfa_code` not in post data
#             if user.two_factor_auth and "tfa_code" not in data:
#                 return self.error("tfa_required")

#             if OtpAuth(user.tfa_token).valid_totp(data["tfa_code"]):
#                 auth.login(request, user)
#                 return self.success("Succeeded")
#             else:
#                 return self.error("Invalid two factor verification code")
#         else:
#             return self.error("Invalid username or password")


# class UserLogoutAPI(APIView):
#     def get(self, request):
#         auth.logout(request)
#         return self.success()


# class UsernameOrEmailCheck(APIView):
#     @validate_serializer(UsernameOrEmailCheckSerializer)
#     def post(self, request):
#         """
#         check username or email is duplicate
#         """
#         data = request.data
#         # True means already exist.
#         result = {
#             "username": False,
#             "email": False
#         }
#         if data.get("username"):
#             result["username"] = User.objects.filter(username=data["username"].lower()).exists()
#         if data.get("email"):
#             result["email"] = User.objects.filter(email=data["email"].lower()).exists()
#         return self.success(result)


# class UserRegisterAPI(APIView):
#     @validate_serializer(UserRegisterSerializer)
#     def post(self, request):
#         """
#         User register api
#         """
#         if not SysOptions.allow_register:
#             return self.error("Register function has been disabled by admin")

#         data = request.data
#         data["username"] = data["username"].lower()
#         data["email"] = data["email"].lower()
#         captcha = Captcha(request)
#         if not captcha.check(data["captcha"]):
#             return self.error("Invalid captcha")
#         if User.objects.filter(username=data["username"]).exists():
#             return self.error("Username already exists")
#         if User.objects.filter(email=data["email"]).exists():
#             return self.error("Email already exists")
#         user = User.objects.create(username=data["username"], email=data["email"])
#         user.set_password(data["password"])
#         user.save()
#         UserProfile.objects.create(user=user)
#         return self.success("Succeeded")


# class UserChangeEmailAPI(APIView):
#     @validate_serializer(UserChangeEmailSerializer)
#     @login_required
#     def post(self, request):
#         data = request.data
#         user = auth.authenticate(username=request.user.username, password=data["password"])
#         if user:
#             if user.two_factor_auth:
#                 if "tfa_code" not in data:
#                     return self.error("tfa_required")
#                 if not OtpAuth(user.tfa_token).valid_totp(data["tfa_code"]):
#                     return self.error("Invalid two factor verification code")
#             data["new_email"] = data["new_email"].lower()
#             if User.objects.filter(email=data["new_email"]).exists():
#                 return self.error("The email is owned by other account")
#             user.email = data["new_email"]
#             user.save()
#             return self.success("Succeeded")
#         else:
#             return self.error("Wrong password")


# class UserChangePasswordAPI(APIView):
#     @validate_serializer(UserChangePasswordSerializer)
#     @login_required
#     def post(self, request):
#         """
#         User change password api
#         """
#         data = request.data
#         username = request.user.username
#         user = auth.authenticate(username=username, password=data["old_password"])
#         if user:
#             if user.two_factor_auth:
#                 if "tfa_code" not in data:
#                     return self.error("tfa_required")
#                 if not OtpAuth(user.tfa_token).valid_totp(data["tfa_code"]):
#                     return self.error("Invalid two factor verification code")
#             user.set_password(data["new_password"])
#             user.save()
#             return self.success("Succeeded")
#         else:
#             return self.error("Invalid old password")


# class ApplyResetPasswordAPI(APIView):
#     @validate_serializer(ApplyResetPasswordSerializer)
#     def post(self, request):
#         if request.user.is_authenticated:
#             return self.error("You have already logged in, are you kidding me? ")
#         data = request.data
#         captcha = Captcha(request)
#         if not captcha.check(data["captcha"]):
#             return self.error("Invalid captcha")
#         try:
#             user = User.objects.get(email__iexact=data["email"])
#         except User.DoesNotExist:
#             return self.error("User does not exist")
#         if user.reset_password_token_expire_time and 0 < int(
#                 (user.reset_password_token_expire_time - now()).total_seconds()) < 20 * 60:
#             return self.error("You can only reset password once per 20 minutes")
#         user.reset_password_token = rand_str()
#         user.reset_password_token_expire_time = now() + timedelta(minutes=20)
#         user.save()
#         render_data = {
#             "username": user.username,
#             "website_name": SysOptions.website_name,
#             "link": f"{SysOptions.website_base_url}/reset-password/{user.reset_password_token}"
#         }
#         email_html = render_to_string("reset_password_email.html", render_data)
#         send_email_async.send(from_name=SysOptions.website_name_shortcut,
#                               to_email=user.email,
#                               to_name=user.username,
#                               subject="Reset your password",
#                               content=email_html)
#         return self.success("Succeeded")


# class ResetPasswordAPI(APIView):
#     @validate_serializer(ResetPasswordSerializer)
#     def post(self, request):
#         data = request.data
#         captcha = Captcha(request)
#         if not captcha.check(data["captcha"]):
#             return self.error("Invalid captcha")
#         try:
#             user = User.objects.get(reset_password_token=data["token"])
#         except User.DoesNotExist:
#             return self.error("Token does not exist")
#         if user.reset_password_token_expire_time < now():
#             return self.error("Token has expired")
#         user.reset_password_token = None
#         user.two_factor_auth = False
#         user.set_password(data["password"])
#         user.save()
#         return self.success("Succeeded")


# class SessionManagementAPI(APIView):
#     @login_required
#     def get(self, request):
#         engine = import_module(settings.SESSION_ENGINE)
#         session_store = engine.SessionStore
#         current_session = request.session.session_key
#         session_keys = request.user.session_keys
#         result = []
#         modified = False
#         for key in session_keys[:]:
#             session = session_store(key)
#             # session does not exist or is expiry
#             if not session._session:
#                 session_keys.remove(key)
#                 modified = True
#                 continue

#             s = {}
#             if current_session == key:
#                 s["current_session"] = True
#             s["ip"] = session["ip"]
#             s["user_agent"] = session["user_agent"]
#             s["last_activity"] = datetime2str(session["last_activity"])
#             s["session_key"] = key
#             result.append(s)
#         if modified:
#             request.user.save()
#         return self.success(result)

#     @login_required
#     def delete(self, request):
#         session_key = request.GET.get("session_key")
#         if not session_key:
#             return self.error("Parameter Error")
#         request.session.delete(session_key)
#         if session_key in request.user.session_keys:
#             request.user.session_keys.remove(session_key)
#             request.user.save()
#             return self.success("Succeeded")
#         else:
#             return self.error("Invalid session_key")


# class UserRankAPI(APIView):
#     def get(self, request):
#         rule_type = request.GET.get("rule")
#         if rule_type not in ContestRuleType.choices():
#             rule_type = ContestRuleType.ACM
#         profiles = UserProfile.objects.filter(user__admin_type=AdminType.REGULAR_USER, user__is_disabled=False) \
#             .select_related("user")
#         if rule_type == ContestRuleType.ACM:
#             profiles = profiles.filter(submission_number__gt=0).order_by("-accepted_number", "submission_number")
#         else:
#             profiles = profiles.filter(total_score__gt=0).order_by("-total_score")
#         return self.success(self.paginate_data(request, profiles, RankInfoSerializer))


# class ProfileProblemDisplayIDRefreshAPI(APIView):
#     @login_required
#     def get(self, request):
#         profile = request.user.userprofile
#         acm_problems = profile.acm_problems_status.get("problems", {})
#         oi_problems = profile.oi_problems_status.get("problems", {})
#         ids = list(acm_problems.keys()) + list(oi_problems.keys())
#         if not ids:
#             return self.success()
#         display_ids = Problem.objects.filter(id__in=ids, visible=True).values_list("_id", flat=True)
#         id_map = dict(zip(ids, display_ids))
#         for k, v in acm_problems.items():
#             v["_id"] = id_map[k]
#         for k, v in oi_problems.items():
#             v["_id"] = id_map[k]
#         profile.save(update_fields=["acm_problems_status", "oi_problems_status"])
#         return self.success()


# class OpenAPIAppkeyAPI(APIView):
#     @login_required
#     def post(self, request):
#         user = request.user
#         if not user.open_api:
#             return self.error("OpenAPI function is truned off for you")
#         api_appkey = rand_str()
#         user.open_api_appkey = api_appkey
#         user.save()
#         return self.success({"appkey": api_appkey})


# class SSOAPI(CSRFExemptAPIView):
#     @login_required
#     def get(self, request):
#         token = rand_str()
#         request.user.auth_token = token
#         request.user.save()
#         return self.success({"token": token})

#     @method_decorator(csrf_exempt)
#     @validate_serializer(SSOSerializer)
#     def post(self, request):
#         try:
#             user = User.objects.get(auth_token=request.data["token"])
#         except User.DoesNotExist:
#             return self.error("User does not exist")
#         return self.success({"username": user.username, "avatar": user.userprofile.avatar, "admin_type": user.admin_type})
import os
from datetime import timedelta
from importlib import import_module

import qrcode
from django.conf import settings
from django.contrib import auth
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from otpauth import TOTP, HOTP


from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser

from problem.models import Problem
from utils.constants import ContestRuleType
from options.options import SysOptions
from utils.api import APIView, validate_serializer, CSRFExemptAPIView
from utils.captcha import Captcha
from utils.shortcuts import rand_str, img2base64, datetime2str
from utils.swagger import StandardResponseSerializer

from ..decorators import login_required
from ..models import User, UserProfile, AdminType
from ..serializers import (
    ApplyResetPasswordSerializer, ResetPasswordSerializer,
    UserChangePasswordSerializer, UserLoginSerializer,
    UserRegisterSerializer, UsernameOrEmailCheckSerializer,
    RankInfoSerializer, UserChangeEmailSerializer, SSOSerializer,
    TwoFactorAuthCodeSerializer, UserProfileSerializer,
    EditUserProfileSerializer, ImageUploadForm
)
from ..tasks import send_email_async


# =====================================================
# User Profile
# =====================================================
class UserProfileAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles retrieval of user profile information.

    Logic Flow:
    - If the user is not authenticated, returns successfully with no data (or partial data depending on context).
    - If a specific `username` is provided in query parameters, it retrieves that user's profile.
    - If no `username` is provided, it retrieves the current authenticated user's profile.
    - `show_real_name` is set to True only if the user is viewing their own profile.
    - Returns serialized user profile data.
    """
    @swagger_auto_schema(
        operation_id="account_profile_get",
        operation_summary="Get User Profile",
        operation_description=(
            "Returns profile data for a user.\n\n"
            "- If `username` query param is provided → returns **that user's** public profile.\n"
            "- If omitted → returns the **current logged-in user's** full profile (including real name).\n"
            "- Returns an empty `data: {}` if called while not authenticated (for checking login state)."
        ),
        manual_parameters=[
            openapi.Parameter(
                "username", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Username to look up. Omit to get your own profile."
            )
        ],
        responses={
            200: openapi.Response(
                description="User profile or empty object",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {
                        "error": None,
                        "data": {
                            "id": 1, "user": {"username": "alice"},
                            "avatar": "/public/avatar/abc.png",
                            "blog": "https://alice.dev",
                            "school": "MIT", "major": "CS",
                            "accepted_number": 42, "submission_number": 100
                        }
                    }
                }
            )
        },
        security=[{"SessionAuth": []}, {"ApiKeyAuth": []}],
        tags=["Account"]
    )
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        if not request.user.is_authenticated:
            return self.success()

        show_real_name = False
        username = request.GET.get("username")

        try:
            if username:
                user = User.objects.get(username=username, is_disabled=False)
            else:
                user = request.user
                show_real_name = True
        except User.DoesNotExist:
            return self.error("User does not exist")

        return self.success(
            UserProfileSerializer(user.userprofile, show_real_name=show_real_name).data
        )

    @swagger_auto_schema(
        operation_id="account_profile_update",
        operation_summary="Update User Profile",
        operation_description=(
            "Update the current user's profile fields.\n\n"
            "All fields are **optional** — only send what you want to change.\n\n"
            "| Field        | Type   | Description                          |\n"
            "|--------------|--------|--------------------------------------|\n"
            "| `real_name`  | string | Full legal name (hidden from others) |\n"
            "| `avatar`     | string | Avatar URL path                      |\n"
            "| `blog`       | URL    | Personal blog or website             |\n"
            "| `mood`       | string | Short status / mood text             |\n"
            "| `github`     | URL    | GitHub profile URL                   |\n"
            "| `school`     | string | School / university name             |\n"
            "| `major`      | string | Field of study                       |\n"
            "| `language`   | string | Preferred programming language       |\n"
        ),
        request_body=EditUserProfileSerializer,
        responses={
            200: openapi.Response(
                description="Updated profile data",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": {"real_name": "Alice", "school": "MIT"}}}
            )
        },
        security=[{"SessionAuth": []}, {"ApiKeyAuth": []}],
        tags=["Account"]
    )
    @login_required
    @validate_serializer(EditUserProfileSerializer)
    def put(self, request):
        """
        Updates the user profile with provided data.
        
        Logic Flow:
        - Iterates through the request data items.
        - Updates the corresponding fields in the `UserProfile` model.
        - Saves the profile and returns the updated serialized data.
        """
        profile = request.user.userprofile
        for k, v in request.data.items():
            setattr(profile, k, v)
        profile.save()
        return self.success(
            UserProfileSerializer(profile, show_real_name=True).data
        )


# =====================================================
# Avatar Upload
# =====================================================
class AvatarUploadAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles user avatar uploads.

    Logic Flow:
    - Validates the uploaded image file (size, format).
    - Checks if the file size exceeds 2MB.
    - Checks if the file extension is supported (.gif, .jpg, .jpeg, .bmp, .png).
    - Generates a random name for the file to prevent collisions.
    - Saves the file to the configured upload directory.
    - Updates the user's profile with the new avatar URL.
    """
    parser_classes = [MultiPartParser, FormParser]
    request_parsers = ()

    @swagger_auto_schema(
        operation_id="account_avatar_upload",
        operation_summary="Upload Avatar",
        operation_description=(
            "Upload a profile avatar image.\n\n"
            "**Constraints:**\n"
            "- Max file size: **2 MB**\n"
            "- Allowed formats: `.gif`, `.jpg`, `.jpeg`, `.bmp`, `.png`\n\n"
            "On success, the user's `avatar` field is updated automatically."
        ),
        manual_parameters=[
            openapi.Parameter(
                "image", openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Avatar image file (gif/jpg/jpeg/bmp/png, max 2 MB)"
            )
        ],
        consumes=["multipart/form-data"],
        responses={
            200: openapi.Response(
                description="Success",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Account"]
    )
    @login_required
    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.error("Invalid file")

        avatar = form.cleaned_data["image"]
        if avatar.size > 2 * 1024 * 1024:
            return self.error("Picture is too large")

        suffix = os.path.splitext(avatar.name)[-1].lower()
        if suffix not in [".gif", ".jpg", ".jpeg", ".bmp", ".png"]:
            return self.error("Unsupported file format")

        name = rand_str(10) + suffix
        with open(os.path.join(settings.AVATAR_UPLOAD_DIR, name), "wb") as f:
            for chunk in avatar:
                f.write(chunk)

        profile = request.user.userprofile
        profile.avatar = f"{settings.AVATAR_URI_PREFIX}/{name}"
        profile.save()
        return self.success("Succeeded")

# =====================================================
# Check if Two-Factor Authentication is Required
# =====================================================
# =====================================================
# Check if Two-Factor Authentication is Required
# =====================================================
class CheckTFARequiredAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Checks if Two-Factor Authentication (TFA/2FA) is enabled for a specific user.

    Logic Flow:
    - Receives a username.
    - Checks if the user exists in the database.
    - Returns the `two_factor_auth` status of the user.
    - Used by the frontend to determine if the 2FA input field should be shown during login.
    """
    @swagger_auto_schema(
        operation_id="security_tfa_check",
        operation_summary="Check if 2FA is Required",
        operation_description=(
            "Check whether Two-Factor Authentication (2FA) is enabled for a given username.\n\n"
            "**Usage:** Call this before showing the login form.  "
            "If `result` is `true`, display the 2FA code input field.\n\n"
            "No authentication required."
        ),
        request_body=UsernameOrEmailCheckSerializer,
        responses={
            200: openapi.Response(
                description="2FA required flag",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {"error": None, "data": {"result": True}}
                }
            )
        },
        security=[],
        tags=["Security"]
    )
    @validate_serializer(UsernameOrEmailCheckSerializer)
    def post(self, request):
        result = False
        username = request.data.get("username")

        if username:
            try:
                user = User.objects.get(username=username)
                result = user.two_factor_auth
            except User.DoesNotExist:
                pass

        return self.success({"result": result})
# =====================================================
# Refresh Problem Display IDs in User Profile
# =====================================================
# =====================================================
# Refresh Problem Display IDs in User Profile
# =====================================================
class ProfileProblemDisplayIDRefreshAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Refreshes the display IDs of problems in the user's profile.

    Logic Flow:
    - Retrieves the user's solved problem lists from `acm_problems_status` and `oi_problems_status`.
    - Queries the database to get the latest display IDs (`_id`) for these problems.
    - Updates the profile data with the new display IDs.
    - Ensures that the user's profile accurately reflects the current problem IDs, which might have changed.
    """
    @swagger_auto_schema(
        operation_id="account_profile_refresh_problem_ids",
        operation_summary="Refresh Problem Display IDs in Profile",
        operation_description=(
            "Syncs the display IDs (`_id` field) of problems in the user's solved-problem status cache.\n\n"
            "Call this if problem display IDs have been changed by an admin and the user's\n"
            "profile still shows the old IDs.  Typically called transparently by the frontend."
        ),
        responses={
            200: openapi.Response(
                description="IDs refreshed",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": {}}}
            )
        },
        security=[{"SessionAuth": []}, {"ApiKeyAuth": []}],
        tags=["Account"]
    )
    @login_required
    def get(self, request):
        profile = request.user.userprofile

        acm_problems = profile.acm_problems_status.get("problems", {})
        oi_problems = profile.oi_problems_status.get("problems", {})

        ids = list(acm_problems.keys()) + list(oi_problems.keys())
        if not ids:
            return self.success()

        display_ids = Problem.objects.filter(
            id__in=ids,
            visible=True
        ).values_list("_id", flat=True)

        id_map = dict(zip(ids, display_ids))

        for k, v in acm_problems.items():
            if k in id_map:
                v["_id"] = id_map[k]

        for k, v in oi_problems.items():
            if k in id_map:
                v["_id"] = id_map[k]

        profile.save(update_fields=[
            "acm_problems_status",
            "oi_problems_status"
        ])

        return self.success()


# =====================================================
# Two Factor Authentication
# =====================================================
# =====================================================
# Two Factor Authentication
# =====================================================
class TwoFactorAuthAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Manages Two-Factor Authentication (2FA) settings.

    Logic Flow:
    - GET: Generates and returns a QR code for setting up 2FA if not already enabled.
    - POST: Verifies the provided 2FA code and enables 2FA for the user.
    - PUT: Verifies the provided 2FA code and disables 2FA for the user.
    """
    @swagger_auto_schema(
        operation_id="security_tfa_qr",
        operation_summary="Get 2FA QR Code",
        operation_description=(
            "Returns a **base64-encoded PNG QR code** for setting up TOTP two-factor authentication.\n\n"
            "1. Call this endpoint → receive QR code image.\n"
            "2. Scan with an authenticator app (Google Authenticator, Authy…).\n"
            "3. POST the 6-digit code to **Enable 2FA** (`POST /api/account/two_factor_auth/`).\n\n"
            "Returns an error if 2FA is already enabled."
        ),
        responses={
            200: openapi.Response(
                description="Base64-encoded QR code PNG",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "data:image/png;base64,iVBOR..."}}
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Security"]
    )
    @login_required
    def get(self, request):
        """
        Get QR code for 2FA setup.
        """
        user = request.user
        if user.two_factor_auth:
            return self.error("2FA already enabled")

        user.tfa_token = rand_str()
        user.save()

        label = f"{SysOptions.website_name_shortcut}:{user.username}"
        image = qrcode.make(
            TOTP(user.tfa_token).to_uri(
                label, SysOptions.website_name.replace(" ", "")
            )
        )
        return self.success(img2base64(image))

    @swagger_auto_schema(
        operation_id="security_tfa_enable",
        operation_summary="Enable 2FA",
        operation_description=(
            "Verify the 6-digit TOTP code from your authenticator app to **enable** 2FA.\n\n"
            "You must call **Get 2FA QR Code** first to obtain the QR code and store the token."
        ),
        request_body=TwoFactorAuthCodeSerializer,
        responses={
            200: openapi.Response(
                description="2FA enabled successfully",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            ),
            400: openapi.Response(description="Invalid code")
        },
        security=[{"SessionAuth": []}],
        tags=["Security"]
    )
    @login_required
    @validate_serializer(TwoFactorAuthCodeSerializer)
    def post(self, request):
        """
        Enable 2FA with verification code.
        """
        if TOTP(request.user.tfa_token).verify(request.data["code"]):
            request.user.two_factor_auth = True
            request.user.save()
            return self.success("Succeeded")
        return self.error("Invalid code")

    @swagger_auto_schema(
        operation_id="security_tfa_disable",
        operation_summary="Disable 2FA",
        operation_description=(
            "Verify the current TOTP code to **disable** 2FA on your account.\n\n"
            "⚠️ After disabling 2FA, your account is protected by password only."
        ),
        request_body=TwoFactorAuthCodeSerializer,
        responses={
            200: openapi.Response(
                description="2FA disabled",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            ),
            400: openapi.Response(description="Invalid code or 2FA already off")
        },
        security=[{"SessionAuth": []}],
        tags=["Security"]
    )
    @login_required
    @validate_serializer(TwoFactorAuthCodeSerializer)
    def put(self, request):
        """
        Disable 2FA with verification code.
        """
        if OtpAuth(request.user.tfa_token).valid_totp(request.data["code"]):
            request.user.two_factor_auth = False
            request.user.save()
            return self.success("Succeeded")
        return self.error("Invalid code")


# =====================================================
# Login / Logout
# =====================================================
# =====================================================
# Login / Logout
# =====================================================
class UserLoginAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles user authentication and login.

    Logic Flow:
    - Validates username and password.
    - Checks if the account is disabled.
    - If 2FA is not enabled, logs the user in immediately.
    - If 2FA is enabled, checks if `tfa_code` is provided and valid.
    - Establishes a session upon successful login.
    """
    @swagger_auto_schema(
        operation_id="account_login",
        operation_summary="User Login",
        operation_description=(
            "Authenticate a user and establish a session.\n\n"
            "**Flow:**\n"
            "1. POST `username` + `password` (add `tfa_code` if 2FA is enabled).\n"
            "2. On success the `sessionid` cookie is set automatically.\n"
            "3. All subsequent requests in this browser tab will be authenticated.\n\n"
            "**Common errors:**\n"
            "- `tfa_required` → re-submit with `tfa_code` field\n"
            "- `Invalid username or password` → wrong credentials"
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "password"],
            properties={
                "username": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Your username",
                    example="admin"
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Your password",
                    example="admin123"
                ),
                "tfa_code": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="6-digit TOTP code (only if 2FA is enabled)",
                    example=""
                ),
            },
            example={
                "username": "admin",
                "password": "admin123"
            }
        ),
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {"error": None, "data": "Succeeded"}
                }
            )
        },
        security=[],
        tags=["Account"]
    )
    @validate_serializer(UserLoginSerializer)
    def post(self, request):
        data = request.data
        user = auth.authenticate(username=data["username"], password=data["password"])

        if not user:
            return self.error("Invalid username or password")
        if user.is_disabled:
            return self.error("Your account has been disabled")

        if not user.two_factor_auth:
            auth.login(request, user)
            return self.success("Succeeded")

        if "tfa_code" not in data:
            return self.error("tfa_required")

        if OtpAuth(user.tfa_token).valid_totp(data["tfa_code"]):
            auth.login(request, user)
            return self.success("Succeeded")

        return self.error("Invalid two factor verification code")


class UserLogoutAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles user logout.

    Logic Flow:
    - Clears the user's session data.
    - Logs the user out.
    """
    @swagger_auto_schema(
        operation_id="account_logout",
        operation_summary="User Logout",
        operation_description="Invalidate the current session and log the user out.",
        responses={
            200: openapi.Response(
                description="Logged out",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": {}}}
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Account"]
    )
    def get(self, request):
        auth.logout(request)
        return self.success()


# =====================================================
# Registration & Checks
# =====================================================
class UsernameOrEmailCheck(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Checks if a username or email is already taken.

    Logic Flow:
    - Accepts a username and/or email.
    - Queries the database to check for existence.
    - Returns boolean flags for both username and email indicating if they are already in use.
    - Primarily used for real-time validation forms.
    """
    @swagger_auto_schema(
        operation_id="account_check_username_email",
        operation_summary="Check Username / Email Availability",
        operation_description=(
            "Check if a username or email address is already taken.\n\n"
            "Pass **either** or **both** fields. Returns `true` if already taken, `false` if available.\n\n"
            "Used for real-time validation during registration."
        ),
        request_body=UsernameOrEmailCheckSerializer,
        responses={
            200: openapi.Response(
                description="Availability flags",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {
                        "error": None,
                        "data": {"username": False, "email": True}
                    }
                }
            )
        },
        security=[],
        tags=["Account"]
    )
    @validate_serializer(UsernameOrEmailCheckSerializer)
    def post(self, request):
        data = request.data
        return self.success({
            "username": User.objects.filter(username=data.get("username", "").lower()).exists()
            if data.get("username") else False,
            "email": User.objects.filter(email=data.get("email", "").lower()).exists()
            if data.get("email") else False,
        })


class UserRegisterAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles new user registration.

    Logic Flow:
    - Checks if registration is enabled via system options.
    - Validates the captcha.
    - Checks if the username or email already exists.
    - Creates a new `User` instance with the provided credentials.
    - Creates an associated `UserProfile`.
    """
    @swagger_auto_schema(
        operation_id="account_register",
        operation_summary="Register New User",
        operation_description=(
            "Register a new user account.\n\n"
            "- Username: max 32 characters\n"
            "- Password: min 6 characters\n"
            "- `captcha`: obtain from `GET /api/conf/captcha/`\n\n"
            "Registration can be disabled globally by the admin."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "password", "email", "captcha"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, example="newuser1"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, example="Password123"),
                "email":    openapi.Schema(type=openapi.TYPE_STRING, format="email", example="newuser1@example.com"),
                "captcha":  openapi.Schema(type=openapi.TYPE_STRING,
                                           description="CAPTCHA token from GET /api/conf/captcha/",
                                           example="CAPTCHA_TOKEN_HERE"),
            },
            example={
                "username": "newuser1",
                "password": "Password123",
                "email": "newuser1@example.com",
                "captcha": "CAPTCHA_TOKEN_HERE"
            }
        ),
        responses={
            200: openapi.Response(
                description="Registered successfully",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            )
        },
        security=[],
        tags=["Account"]
    )
    @validate_serializer(UserRegisterSerializer)
    def post(self, request):
        if not SysOptions.allow_register:
            return self.error("Register disabled")

        data = request.data
        captcha = Captcha(request)
        if not captcha.check(data["captcha"]):
            return self.error("Invalid captcha")

        data["username"] = data["username"].lower()
        data["email"] = data["email"].lower()

        if User.objects.filter(username=data["username"]).exists():
            return self.error("Username already exists")
        if User.objects.filter(email=data["email"]).exists():
            return self.error("Email already exists")

        user = User.objects.create(username=data["username"], email=data["email"])
        user.set_password(data["password"])
        user.save()
        UserProfile.objects.create(user=user)
        return self.success("Succeeded")


# =====================================================
# Password / Email Change
# =====================================================
class UserChangePasswordAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Allows users to change their password.

    Logic Flow:
    - Authenticates the user with their old password.
    - If valid, updates the password with the new one.
    - Does NOT require 2FA here, assuming the session or old password is sufficient (though some implementations might add it).
    """
    @swagger_auto_schema(
        operation_id="account_change_password",
        operation_summary="Change Password",
        operation_description=(
            "Change the current user's password.\n\n"
            "Requires the **old password** for verification. "
            "Add `tfa_code` if 2FA is enabled."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["old_password", "new_password"],
            properties={
                "old_password": openapi.Schema(type=openapi.TYPE_STRING, example="admin123"),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING, example="NewPassword456"),
                "tfa_code":     openapi.Schema(type=openapi.TYPE_STRING,
                                               description="TOTP code if 2FA is enabled",
                                               example=""),
            },
            example={"old_password": "admin123", "new_password": "NewPassword456"}
        ),
        responses={
            200: openapi.Response(
                description="Password changed",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Account"]
    )
    @login_required
    @validate_serializer(UserChangePasswordSerializer)
    def post(self, request):
        user = auth.authenticate(
            username=request.user.username,
            password=request.data["old_password"]
        )
        if not user:
            return self.error("Invalid old password")

        user.set_password(request.data["new_password"])
        user.save()
        return self.success("Succeeded")


class UserChangeEmailAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Allows users to change their email address.

    Logic Flow:
    - Requires password verification to authorize the change.
    - Updates the email address in the `User` model.
    """
    @swagger_auto_schema(
        operation_id="account_change_email",
        operation_summary="Change Email Address",
        operation_description=(
            "Change the current user's email address.\n\n"
            "Requires the account **password** for verification. Add `tfa_code` if 2FA is enabled."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["password", "new_email"],
            properties={
                "password":  openapi.Schema(type=openapi.TYPE_STRING, example="admin123"),
                "new_email": openapi.Schema(type=openapi.TYPE_STRING, format="email", example="newemail@example.com"),
                "tfa_code":  openapi.Schema(type=openapi.TYPE_STRING, example=""),
            },
            example={"password": "admin123", "new_email": "newemail@example.com"}
        ),
        responses={
            200: openapi.Response(
                description="Email changed",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Account"]
    )
    @login_required
    @validate_serializer(UserChangeEmailSerializer)
    def post(self, request):
        user = auth.authenticate(
            username=request.user.username,
            password=request.data["password"]
        )
        if not user:
            return self.error("Wrong password")

        user.email = request.data["new_email"].lower()
        user.save()
        return self.success("Succeeded")


# =====================================================
# Reset Password
# =====================================================
# =====================================================
# Reset Password
# =====================================================
class ApplyResetPasswordAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Initiates the password reset process.

    Logic Flow:
    - Checks if the user is already logged in (password reset is for lost passwords).
    - Validates captcha.
    - Checks if the email exists in the system.
    - Limits reset requests to one every 20 minutes to prevent spam.
    - Generates a reset token and sets an expiration time.
    - Sends an email with the reset link to the user.
    """
    @swagger_auto_schema(
        operation_id="account_apply_reset_password",
        operation_summary="Request Password Reset Link",
        operation_description=(
            "Sends a password reset email. Rate-limited to once per 20 minutes.\n\n"
            "Must NOT be logged in. The email contains a one-time reset link (expires in 20 min)."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "captcha"],
            properties={
                "email":   openapi.Schema(type=openapi.TYPE_STRING, format="email", example="user@example.com"),
                "captcha": openapi.Schema(type=openapi.TYPE_STRING, example="CAPTCHA_TOKEN_HERE"),
            },
            example={"email": "user@example.com", "captcha": "CAPTCHA_TOKEN_HERE"}
        ),
        responses={
            200: openapi.Response(
                description="Reset email sent",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            )
        },
        security=[],
        tags=["Account"]
    )
    @validate_serializer(ApplyResetPasswordSerializer)
    def post(self, request):
        if request.user.is_authenticated:
            return self.error("You have already logged in, are you kidding me?")
        
        data = request.data
        captcha = Captcha(request)
        if not captcha.check(data["captcha"]):
            return self.error("Invalid captcha")

        try:
            user = User.objects.get(email__iexact=data["email"])
        except User.DoesNotExist:
            return self.error("User does not exist")

        if user.reset_password_token_expire_time and 0 < int(
                (user.reset_password_token_expire_time - now()).total_seconds()) < 20 * 60:
            return self.error("You can only reset password once per 20 minutes")

        user.reset_password_token = rand_str()
        user.reset_password_token_expire_time = now() + timedelta(minutes=20)
        user.save()

        render_data = {
            "username": user.username,
            "website_name": SysOptions.website_name,
            "link": f"{SysOptions.website_base_url}/reset-password/{user.reset_password_token}"
        }
        email_html = render_to_string("reset_password_email.html", render_data)
        send_email_async.send(from_name=SysOptions.website_name_shortcut,
                              to_email=user.email,
                              to_name=user.username,
                              subject="Reset your password",
                              content=email_html)
        return self.success("Succeeded")


class ResetPasswordAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Completes the password reset process.

    Logic Flow:
    - Validates the captcha.
    - Verifies the reset token matches a user and has not expired.
    - Updates the user's password.
    - Clears the reset token.
    - Disables 2FA as a security measure (can be re-enabled by user).
    """
    @swagger_auto_schema(
        operation_id="account_reset_password",
        operation_summary="Complete Password Reset",
        operation_description=(
            "Set a new password using the reset token from your email.\n\n"
            "⚠️ This also disables 2FA. Re-enable it after login."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["token", "password", "captcha"],
            properties={
                "token":    openapi.Schema(type=openapi.TYPE_STRING,
                                           description="Reset token from the password-reset email",
                                           example="RESET_TOKEN_FROM_EMAIL"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, example="NewPassword123"),
                "captcha":  openapi.Schema(type=openapi.TYPE_STRING, example="CAPTCHA_TOKEN_HERE"),
            },
            example={
                "token": "RESET_TOKEN_FROM_EMAIL",
                "password": "NewPassword123",
                "captcha": "CAPTCHA_TOKEN_HERE"
            }
        ),
        responses={
            200: openapi.Response(
                description="Password reset successful",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            )
        },
        security=[],
        tags=["Account"]
    )
    @validate_serializer(ResetPasswordSerializer)
    def post(self, request):
        data = request.data
        captcha = Captcha(request)
        if not captcha.check(data["captcha"]):
            return self.error("Invalid captcha")

        try:
            user = User.objects.get(reset_password_token=data["token"])
        except User.DoesNotExist:
            return self.error("Token does not exist")

        if user.reset_password_token_expire_time < now():
            return self.error("Token has expired")

        user.reset_password_token = None
        user.two_factor_auth = False
        user.set_password(data["password"])
        user.save()
        return self.success("Succeeded")


# =====================================================
# Sessions / Rank / OpenAPI / SSO
# =====================================================
# =====================================================
# Sessions / Rank / OpenAPI / SSO
# =====================================================
class SessionManagementAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Manages active user sessions.

    Logic Flow:
    - GET: list all active sessions for the current user, showing IP, user agent, and last activity.
    - DELETE: kill a specific session (force logout on that device).
    - Automatically cleans up expired sessions from the user's session list.
    """
    @swagger_auto_schema(
        operation_id="security_sessions_list",
        operation_summary="List Active Sessions",
        operation_description=(
            "Returns a list of all active sessions for the current user.\n\n"
            "Each entry includes: IP address, user-agent string, last activity time, and session key.  "
            "The current session is flagged with `current_session: true`."
        ),
        responses={
            200: openapi.Response(
                description="Active sessions",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {
                        "error": None,
                        "data": [
                            {
                                "current_session": True,
                                "ip": "203.0.113.5",
                                "user_agent": "Mozilla/5.0 ...",
                                "last_activity": "2026-02-21T01:00:00Z",
                                "session_key": "abc123"
                            }
                        ]
                    }
                }
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Security"]
    )
    @login_required
    def get(self, request):
        engine = import_module(settings.SESSION_ENGINE)
        session_store = engine.SessionStore
        current_session = request.session.session_key
        session_keys = request.user.session_keys
        result = []
        modified = False
        for key in session_keys[:]:
            session = session_store(key)
            # session does not exist or is expiry
            if not session._session:
                session_keys.remove(key)
                modified = True
                continue

            s = {}
            if current_session == key:
                s["current_session"] = True
            s["ip"] = session["ip"]
            s["user_agent"] = session["user_agent"]
            s["last_activity"] = datetime2str(session["last_activity"])
            s["session_key"] = key
            result.append(s)
        if modified:
            request.user.save()
        return self.success(result)

    @swagger_auto_schema(
        operation_id="security_sessions_kill",
        operation_summary="Kill (Terminate) a Session",
        operation_description=(
            "Force-logout a specific session identified by `session_key`.  "
            "Use this to sign out another device.\n\n"
            "Obtain the `session_key` from the **List Active Sessions** endpoint."
        ),
        manual_parameters=[
            openapi.Parameter(
                "session_key", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="Session key to terminate (from List Sessions)"
            )
        ],
        responses={
            200: openapi.Response(
                description="Session terminated",
                schema=StandardResponseSerializer,
                examples={"application/json": {"error": None, "data": "Succeeded"}}
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Security"]
    )
    @login_required
    def delete(self, request):
        session_key = request.GET.get("session_key")
        if not session_key:
            return self.error("Parameter Error")
        request.session.delete(session_key)
        if session_key in request.user.session_keys:
            request.user.session_keys.remove(session_key)
            request.user.save()
            return self.success("Succeeded")
        else:
            return self.error("Invalid session_key")


class UserRankAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Retrieves the user leaderboard/rankings.

    Logic Flow:
    - Supports different ranking rules (ACM vs OI).
    - Filters out admin users and disabled accounts.
    - ACM Rule: Ranks by number of accepted problems (descending) and then submission count (ascending).
    - OI Rule: Ranks by total score (descending).
    - Supports pagination.
    """
    @swagger_auto_schema(
        operation_id="rank_user_list",
        operation_summary="Global User Leaderboard",
        operation_description=(
            "Returns a paginated user leaderboard.\n\n"
            "**Rule types:**\n"
            "- `ACM` (default) – ranked by accepted problems (desc), then submission count (asc)\n"
            "- `OI` – ranked by total score (desc)\n\n"
            "Only `REGULAR_USER` accounts that have at least one submission are shown.  "
            "Admin accounts and disabled accounts are excluded."
        ),
        manual_parameters=[
            openapi.Parameter(
                "rule", openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Ranking rule: `ACM` (default) or `OI`"
            ),
            openapi.Parameter("limit",  openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                              description="Results per page"),
            openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                              description="Starting offset"),
        ],
        responses={
            200: openapi.Response(
                description="Paginated leaderboard",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {
                        "error": None,
                        "data": {
                            "total": 500,
                            "results": [
                                {"user": {"username": "alice"}, "accepted_number": 42, "submission_number": 60}
                            ]
                        }
                    }
                }
            )
        },
        security=[],
        tags=["Rank"]
    )
    def get(self, request):
        rule_type = request.GET.get("rule", ContestRuleType.ACM)
        profiles = UserProfile.objects.filter(
            user__admin_type=AdminType.REGULAR_USER,
            user__is_disabled=False
        ).select_related("user")

        if rule_type == ContestRuleType.ACM:
            profiles = profiles.filter(submission_number__gt=0).order_by(
                "-accepted_number", "submission_number"
            )
        else:
            profiles = profiles.filter(total_score__gt=0).order_by("-total_score")

        return self.success(
            self.paginate_data(request, profiles, RankInfoSerializer)
        )


class OpenAPIAppkeyAPI(APIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Resets the Open API app key for the user.

    Logic Flow:
    - Checks if the Open API feature is enabled for the user.
    - Generates a new random app key.
    - Saves the new key to the user profile and returns it.
    """
    @swagger_auto_schema(
        operation_id="security_appkey_reset",
        operation_summary="Reset / Get Open API App Key",
        operation_description=(
            "Generate a **new** API app key for your account.\n\n"
            "⚠️ The previous app key is **invalidated immediately**.\n\n"
            "**Prerequisites:**\n"
            "- Your account must have Open API enabled (set by Super Admin).\n\n"
            "**Use the returned `appkey` in subsequent requests:**  "
            "Add the `APPKEY` HTTP header:"
            "```\nAPPKEY: <your-appkey>\n```"
        ),
        responses={
            200: openapi.Response(
                description="New app key generated",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {
                        "error": None,
                        "data": {"appkey": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"}
                    }
                }
            )
        },
        security=[{"SessionAuth": []}],
        tags=["Security"]
    )
    @login_required
    def post(self, request):
        if not request.user.open_api:
            return self.error("OpenAPI disabled")

        request.user.open_api_appkey = rand_str()
        request.user.save()
        return self.success({"appkey": request.user.open_api_appkey})


class SSOAPI(CSRFExemptAPIView):
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Handles Single Sign-On (SSO) operations.

    Logic Flow:
    - GET: Generates a temporary SSO token for the current user to use in external applications.
    - POST: Validates an SSO token from an external application and returns the user's information (username, avatar, admin type).
    """
    @swagger_auto_schema(
        operation_id="sso_token_generate",
        operation_summary="Generate SSO Token",
        operation_description=(
            "Generate a one-time SSO token for the current user.\n\n"
            "The token is stored in the user record and can be exchanged by an\n"
            "external service via **SSO Login** (`POST /api/account/sso/`).\n\n"
            "Each call overwrites the previous token."
        ),
        responses={
            200: openapi.Response(
                description="SSO token",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {"error": None, "data": {"token": "random32chartoken"}}
                }
            )
        },
        security=[{"SessionAuth": []}],
        tags=["SSO"]
    )
    @login_required
    def get(self, request):
        token = rand_str()
        request.user.auth_token = token
        request.user.save()
        return self.success({"token": token})

    @swagger_auto_schema(
        operation_id="sso_token_login",
        operation_summary="SSO Token Exchange",
        operation_description=(
            "Exchange an SSO token for user information (for external services).\n\n"
            "An external system obtains the token from the user (via **Generate SSO Token**) and calls\n"
            "this endpoint to verify the token and retrieve the user's profile.\n\n"
            "Returns `username`, `avatar`, and `admin_type`."
        ),
        request_body=SSOSerializer,
        responses={
            200: openapi.Response(
                description="User info from token",
                schema=StandardResponseSerializer,
                examples={
                    "application/json": {
                        "error": None,
                        "data": {
                            "username": "alice",
                            "avatar": "/public/avatar/abc.png",
                            "admin_type": "Regular User"
                        }
                    }
                }
            )
        },
        security=[],
        tags=["SSO"]
    )
    @method_decorator(csrf_exempt)
    @validate_serializer(SSOSerializer)
    def post(self, request):
        try:
            user = User.objects.get(auth_token=request.data["token"])
        except User.DoesNotExist:
            return self.error("User does not exist")

        return self.success({
            "username": user.username,
            "avatar": user.userprofile.avatar,
            "admin_type": user.admin_type
        })
