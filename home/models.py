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
    total_score = models.IntegerField(default=0)  # New field for score


class PredictionData(models.Model):
    category_number = models.IntegerField()
    left_count = models.IntegerField()
    right_count = models.IntegerField()
    final_prediction = models.CharField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test_date = models.DateTimeField(default=timezone.now)
    # result_data = models.CharField(max_length=500, default='Not specified') 


class CategoryData(models.Model):
    category_number = models.IntegerField()
    category_name = models.CharField()
    is_positive = models.IntegerField()
    image_metadata = models.CharField()
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    image_description = models.CharField()


class LLMResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    response_llm = models.TextField()
    techniques = models.TextField()
    next_steps = models.TextField()
    prediction_test = models.ForeignKey(
        'PredictionData', on_delete=models.CASCADE, related_name="llm_responses"
    )
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for when the record was created

    def __str__(self):
        return f"LLM Response for User {self.user.id} and Prediction {self.prediction_test.id}"