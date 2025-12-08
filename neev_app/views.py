from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from .models import Student, Teacher, PasswordResetOTP
import json
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
import random
from django.core.mail import send_mail
from django.utils import timezone
import random, string
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.decorators import method_decorator



OTP_STORE = {}   # store email→otp temporary

def gen_otp(length=6):
    return ''.join(random.choices('0123456789', k=length))

@csrf_exempt
def student_register(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    data = json.loads(request.body)

    name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    student_class = data.get("student_class")
    phone = data.get("phone")

    if Student.objects.filter(email=email).exists():
        return JsonResponse({"message": "Email already exists"}, status=400)

    Student.objects.create(
        full_name=name,
        email=email,
        password=make_password(password),
        student_class=student_class,
        phone=phone,
    )

    return JsonResponse({"message": "Student registered successfully"}, status=200)

@csrf_exempt
def teacher_register(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    data = json.loads(request.body.decode("utf-8"))

    full_name = data.get("full_name")
    email = data.get("email")
    phone = data.get("phone")
    subject = data.get("subject")

    if Teacher.objects.filter(email=email).exists():
        return JsonResponse({"message": "Email already exists"}, status=400)


    import random, string
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    # Django User create
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=full_name
    )

    Teacher.objects.create(
        user=user,
        full_name=full_name,
        email=email,
        phone=phone,
        subject=subject,
    )

    # Send password on email
    from django.core.mail import send_mail

    send_mail(
        subject="Your NEEV Teacher Account Password",
        message=f"Hello {full_name}, your login password is: {password}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )

    return JsonResponse({"success": True, "message": "Teacher registered successfully!"})


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Student, Teacher
import json


@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    data = json.loads(request.body)
    email = data.get("email")
    password = data.get("password")

    # ---------- TEACHER LOGIN ----------
    user = authenticate(username=email, password=password)

    if user:  
        refresh = RefreshToken.for_user(user)

        try:
            teacher = Teacher.objects.get(email=email)
            refresh["email"] = teacher.email
            refresh["full_name"] = teacher.full_name
            refresh["role"] = "teacher"
        except Teacher.DoesNotExist:
            refresh["email"] = user.email
            refresh["role"] = "teacher"

        return JsonResponse({
            "success": True,
            "role": "teacher",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=200)

    # ---------- STUDENT LOGIN ----------
    try:
        student = Student.objects.get(email=email)

        if check_password(password, student.password):

            refresh = RefreshToken()
            refresh["email"] = student.email
            refresh["full_name"] = student.full_name
            refresh["role"] = "student"

            return JsonResponse({
                "success": True,
                "role": "student",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }, status=200)

    except Student.DoesNotExist:
        pass

    return JsonResponse({"success": False, "message": "Invalid credentials"}, status=400)


@csrf_exempt
def forgot_request_otp(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method"}, status=400)

    data = json.loads(request.body)
    email = data.get("email")
    if not email:
        return JsonResponse({"success": False, "message": "Email required"}, status=400)

    exists = Student.objects.filter(email=email).exists() or Teacher.objects.filter(email=email).exists() or User.objects.filter(email=email).exists()
    if not exists:
        return JsonResponse({"success": False, "message": "No account with this email"}, status=404)

    otp = gen_otp()
    PasswordResetOTP.objects.create(email=email, otp=otp)

    # send email
    try:
        send_mail(
            subject="NEEV Password Reset OTP",
            message=f"Your OTP for password reset is: {otp}. It is valid for 10 minutes.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Email send failed: {str(e)}"}, status=500)

    return JsonResponse({"success": True, "message": "OTP sent to email."}, status=200)


@csrf_exempt
def forgot_verify_otp(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method"}, status=400)

    data = json.loads(request.body)
    email = data.get("email")
    otp = data.get("otp")
    if not email or not otp:
        return JsonResponse({"success": False, "message": "Email and OTP required"}, status=400)

    # latest unused OTP for email
    try:
        pr = PasswordResetOTP.objects.filter(email=email, otp=otp, used=False).order_by('-created_at')[0]
    except IndexError:
        return JsonResponse({"success": False, "message": "Invalid OTP"}, status=400)

    # check expiry (10 minutes)
    if (timezone.now() - pr.created_at).total_seconds() > 10*60:
        return JsonResponse({"success": False, "message": "OTP expired"}, status=400)

    # mark used (but we won't change password here)
    pr.used = True
    pr.save()

    return JsonResponse({"success": True, "message": "OTP verified"}, status=200)


@csrf_exempt
def forgot_reset_password(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method"}, status=400)

    data = json.loads(request.body)
    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")
    if not email or not otp or not new_password:
        return JsonResponse({"success": False, "message": "Email, OTP and new_password required"}, status=400)

    # find used OTP recently (we marked used on verify) OR allow reset if OTP matches and within time
    try:
        pr = PasswordResetOTP.objects.filter(email=email, otp=otp).order_by('-created_at')[0]
    except IndexError:
        return JsonResponse({"success": False, "message": "Invalid OTP"}, status=400)

    if (timezone.now() - pr.created_at).total_seconds() > 10*60:
        return JsonResponse({"success": False, "message": "OTP expired"}, status=400)

    # Reset for Student
    try:
        student = Student.objects.get(email=email)
        student.password = make_password(new_password)
        student.save()
        return JsonResponse({"success": True, "message": "Password updated for student"}, status=200)
    except Student.DoesNotExist:
        pass

    # Reset for Teacher -> update auth User
    try:
        teacher = Teacher.objects.get(email=email)
        user = teacher.user
        user.set_password(new_password)
        user.save()
        return JsonResponse({"success": True, "message": "Password updated for teacher"}, status=200)
    except Teacher.DoesNotExist:
        pass

    # Reset for plain Django User (fallback)
    try:
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        return JsonResponse({"success": True, "message": "Password updated"}, status=200)
    except User.DoesNotExist:
        pass

    return JsonResponse({"success": False, "message": "Account not found"}, status=404)



@csrf_exempt
def student_profile(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=400)

    # JWT decode
    auth = JWTAuthentication()
    try:
        user_auth = auth.get_validated_token(request.headers.get("Authorization").split(" ")[1])
    except:
        return JsonResponse({"error": "Invalid token"}, status=401)

    email = user_auth.get("email")

    try:
        student = Student.objects.get(email=email)
    except Student.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)

    return JsonResponse({
        "full_name": student.full_name,
        "student_class": student.student_class,
        "email": student.email,
        "phone": student.phone,
    }, status=200)

@csrf_exempt
def teacher_profile(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=400)

    auth = JWTAuthentication()
    try:
        user_auth = auth.get_validated_token(request.headers.get("Authorization").split(" ")[1])
    except:
        return JsonResponse({"error": "Invalid token"}, status=401)

    email = user_auth.get("email") if "email" in user_auth else None

    if not email:
        # Teacher ka token default JWT hota hai, usme "email" claim nahi hota
        # Isliye user object fetch karte hain
        user = auth.get_user(user_auth)
        email = user.email

    try:
        teacher = Teacher.objects.get(email=email)
    except Teacher.DoesNotExist:
        return JsonResponse({"error": "Teacher not found"}, status=404)

    return JsonResponse({
        "full_name": teacher.full_name,
        "email": teacher.email,
        "phone": teacher.phone,
        "subject": teacher.subject,
    }, status=200)
