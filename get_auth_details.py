import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")
django.setup()

from account.models import User
from utils.shortcuts import rand_str

def init_user():
    username = "root"
    password = "rootroot"
    email = "root@onlinejudge.local"

    from account.models import AdminType, UserProfile
    try:
        user = User.objects.get(username=username)
        print(f"[+] User '{username}' already exists.")
    except User.DoesNotExist:
        user = User.objects.create(username=username, email=email, admin_type=AdminType.SUPER_ADMIN)
        UserProfile.objects.create(user=user, real_name="Super Admin")
        print(f"[+] User '{username}' created.")

    # Reset password to ensure we know it
    user.set_password(password)
    print(f"[+] Password set to '{password}'.")

    # Ensure OpenAPI is enabled
    user.open_api = True
    
    # Generate APPKEY if missing
    if not user.open_api_appkey:
        user.open_api_appkey = rand_str()
        print("[+] Generated new APPKEY.")
    else:
        print("[+] Existing APPKEY found.")
    
    user.save()

    print("\n" + "="*40)
    print("SWAGGER AUTHENTICATION DETAILS")
    print("="*40)
    print(f"Username : {username}")
    print(f"Password : {password}")
    print(f"APPKEY   : {user.open_api_appkey}")
    print("-" * 40)
    print("INSTRUCTIONS:")
    print("1. 'SessionAuth': Login at http://127.0.0.1:8000/api/account/login/ (or /admin/).")
    print("   Once logged in, SessionAuth works automatically!")
    print("2. 'ApiKeyAuth': Copy the APPKEY above and paste it into the Swagger authorize box.")
    print("="*40 + "\n")

if __name__ == "__main__":
    init_user()
