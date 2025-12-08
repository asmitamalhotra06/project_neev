from django.urls import path
from .views import student_register, teacher_register, login_user, forgot_request_otp, forgot_verify_otp, forgot_reset_password, student_profile,  teacher_profile

urlpatterns = [
    path("register/student/", student_register),
    path("register/teacher/", teacher_register),
    path("login/", login_user),
    path("forgot/request_otp/", forgot_request_otp),
    path("forgot/verify_otp/", forgot_verify_otp),
    path("forgot/reset_password/", forgot_reset_password),
    path("student/profile/", student_profile),
    path("teacher/profile/", teacher_profile),
]
