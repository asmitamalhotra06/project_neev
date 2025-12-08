from django.db import models

# Create your models here.

from django.contrib.auth.models import User
from django.utils import timezone

class PasswordResetOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=timezone.now)
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.otp}"


class Student(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    student_class = models.CharField(max_length=20)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.full_name


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=100)

    def __str__(self):
        return self.full_name
    
import uuid


