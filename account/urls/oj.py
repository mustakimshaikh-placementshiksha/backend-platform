# from django.conf.urls import url

# from ..views.oj import (ApplyResetPasswordAPI, ResetPasswordAPI,
#                         UserChangePasswordAPI, UserRegisterAPI, UserChangeEmailAPI,
#                         UserLoginAPI, UserLogoutAPI, UsernameOrEmailCheck,
#                         AvatarUploadAPI, TwoFactorAuthAPI, UserProfileAPI,
#                         UserRankAPI, CheckTFARequiredAPI, SessionManagementAPI,
#                         ProfileProblemDisplayIDRefreshAPI, OpenAPIAppkeyAPI, SSOAPI)

# from utils.captcha.views import CaptchaAPIView

# urlpatterns = [
#     url(r"^login/?$", UserLoginAPI.as_view(), name="user_login_api"),
#     url(r"^logout/?$", UserLogoutAPI.as_view(), name="user_logout_api"),
#     url(r"^register/?$", UserRegisterAPI.as_view(), name="user_register_api"),
#     url(r"^change_password/?$", UserChangePasswordAPI.as_view(), name="user_change_password_api"),
#     url(r"^change_email/?$", UserChangeEmailAPI.as_view(), name="user_change_email_api"),
#     url(r"^apply_reset_password/?$", ApplyResetPasswordAPI.as_view(), name="apply_reset_password_api"),
#     url(r"^reset_password/?$", ResetPasswordAPI.as_view(), name="reset_password_api"),
#     url(r"^captcha/?$", CaptchaAPIView.as_view(), name="show_captcha"),
#     url(r"^check_username_or_email", UsernameOrEmailCheck.as_view(), name="check_username_or_email"),
#     url(r"^profile/?$", UserProfileAPI.as_view(), name="user_profile_api"),
#     url(r"^profile/fresh_display_id", ProfileProblemDisplayIDRefreshAPI.as_view(), name="display_id_fresh"),
#     url(r"^upload_avatar/?$", AvatarUploadAPI.as_view(), name="avatar_upload_api"),
#     url(r"^tfa_required/?$", CheckTFARequiredAPI.as_view(), name="tfa_required_check"),
#     url(r"^two_factor_auth/?$", TwoFactorAuthAPI.as_view(), name="two_factor_auth_api"),
#     url(r"^user_rank/?$", UserRankAPI.as_view(), name="user_rank_api"),
#     url(r"^sessions/?$", SessionManagementAPI.as_view(), name="session_management_api"),
#     url(r"^open_api_appkey/?$", OpenAPIAppkeyAPI.as_view(), name="open_api_appkey_api"),
#     url(r"^sso?$", SSOAPI.as_view(), name="sso_api")
# ]
# account/urls/oj.py
# account/urls/oj.py
from django.urls import path

from ..views.oj import (
    ApplyResetPasswordAPI,
    ResetPasswordAPI,
    UserChangePasswordAPI,
    UserRegisterAPI,
    UserChangeEmailAPI,
    UserLoginAPI,
    UserLogoutAPI,
    UsernameOrEmailCheck,
    AvatarUploadAPI,
    TwoFactorAuthAPI,
    UserProfileAPI,
    UserRankAPI,
    CheckTFARequiredAPI,
    SessionManagementAPI,
    ProfileProblemDisplayIDRefreshAPI,
    OpenAPIAppkeyAPI,
    SSOAPI,
)

from utils.captcha.views import CaptchaAPIView


urlpatterns = [
    # Auth
    path("login/", UserLoginAPI.as_view(), name="user_login_api"),
    path("logout/", UserLogoutAPI.as_view(), name="user_logout_api"),
    path("register/", UserRegisterAPI.as_view(), name="user_register_api"),

    # Account settings
    path("change_password/", UserChangePasswordAPI.as_view(), name="user_change_password_api"),
    path("change_email/", UserChangeEmailAPI.as_view(), name="user_change_email_api"),

    # Password reset
    path("apply_reset_password/", ApplyResetPasswordAPI.as_view(), name="apply_reset_password_api"),
    path("reset_password/", ResetPasswordAPI.as_view(), name="reset_password_api"),

    # Captcha
    path("captcha/", CaptchaAPIView.as_view(), name="show_captcha"),

    # Checks
    path("check_username_or_email/", UsernameOrEmailCheck.as_view(), name="check_username_or_email"),
    path("tfa_required/", CheckTFARequiredAPI.as_view(), name="tfa_required_check"),

    # Profile
    path("profile/", UserProfileAPI.as_view(), name="user_profile_api"),
    path(
        "profile/fresh_display_id/",
        ProfileProblemDisplayIDRefreshAPI.as_view(),
        name="display_id_fresh",
    ),
    path("upload_avatar/", AvatarUploadAPI.as_view(), name="avatar_upload_api"),

    # Security
    path("two_factor_auth/", TwoFactorAuthAPI.as_view(), name="two_factor_auth_api"),
    path("sessions/", SessionManagementAPI.as_view(), name="session_management_api"),

    # Rank
    path("user_rank/", UserRankAPI.as_view(), name="user_rank_api"),

    # OpenAPI / SSO
    path("open_api_appkey/", OpenAPIAppkeyAPI.as_view(), name="open_api_appkey_api"),
    path("sso/", SSOAPI.as_view(), name="sso_api"),
]
