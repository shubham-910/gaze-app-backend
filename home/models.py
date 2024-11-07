from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class GadResponse(models.Model):
    question_1 = models.IntegerField()
    question_2 = models.IntegerField()
    question_3 = models.IntegerField()
    question_4 = models.IntegerField()
    question_5 = models.IntegerField()
    question_6 = models.IntegerField()
    question_7 = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    difficulty = models.CharField(max_length=50, default='Not specified')  # Add default value here
    is_filled = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(default=timezone.now)

class PredictionData(models.Model):
    category_number = models.IntegerField()
    left_count = models.IntegerField()
    right_count = models.IntegerField()
    final_prediction = models.CharField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test_date = models.DateTimeField(default=timezone.now)
