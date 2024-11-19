from django.shortcuts import HttpResponse, redirect
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from django.contrib.auth  import authenticate,  login, logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
import json
from .models import GadResponse, PredictionData
from django.utils import timezone
from django.http import JsonResponse
from django.core.serializers import serialize
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from pathlib import Path

@csrf_exempt
def handleRegister(request):
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)

            username = data.get('name')
            email = data.get('email')
            password = data.get('password')
            retypePassword = data.get('retypePassword')

            # Check if both passwords match
            if password == retypePassword:
                # Create the user
                myuser = User.objects.create_user(username=username, email=email, password=password)
                myuser.is_staff = False  # Mark the user as non-staff (regular user)
                myuser.save()
                return HttpResponse("User Created Successfully", status=201)
            else:
                return HttpResponse("Passwords do not match", status=400)

        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON format", status=400)

    return HttpResponse("Invalid request method", status=405)

@csrf_exempt
def handleLogin(request):
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            # Use the custom backend to authenticate with email and password
            user = authenticate(email=email, password=password)

            if user is not None:
                token, created = Token.objects.get_or_create(user=user)
                
                # Check if there is any entry in GadResponse for this user
                is_filled = 1 if GadResponse.objects.filter(user=user).exists() else 0
                
                # Prepare the response data with token, user_id, name, and is_filled flag
                response_data = {
                    'token': token.key,
                    'user_id': user.id,
                    'name': user.username,  # or user.name if your User model uses `name` field
                    'is_filled': is_filled  # Send the is_filled flag
                }

                return HttpResponse(json.dumps(response_data), content_type="application/json", status=200)

            else:
                return HttpResponse("Invalid Credentials", status=401)

        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON format", status=400)

    else:
        return HttpResponse("404 - Not found", status=404)



@csrf_exempt
def handleLogout(request):
    if request.method == "POST":
        # Get token from headers
        authHeader = request.headers.get('Authorization')

        if authHeader:
            # Extract token key from 'Token <token_key>' format
            tokenKey = authHeader.split(' ')[1]

            try:
                # Find the token in the database and delete it
                token = Token.objects.get(key=tokenKey)
                token.delete()
                logout(request)
                return HttpResponse("Logged out successfully", status=200)

            except Token.DoesNotExist:
                return HttpResponse("Invalid token", status=400)
        else:
            return HttpResponse("No token provided", status=400)

    return HttpResponse("Method not allowed", status=405)


@csrf_exempt
def sendResetLink(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            email = data.get('email')

            # Check if a user with the provided email exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return HttpResponse({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate a password reset token for the user
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)

            # Construct the reset URL (frontend URL)
            reset_url = f"{settings.FRONTEND_URL}reset-password/{user.id}/{token}"

            # Send the reset link via email
            send_mail(
                subject="Password Reset Request from GazeTrack",
                message=f"Click the link below to reset your password:  \n{reset_url}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

            return HttpResponse({"message": "Password reset link sent successfully."}, status=status.HTTP_200_OK)
    except json.JSONDecodeError:
        return HttpResponse({"error": "Invalid JSON format."}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def resetPassword(request, user_id, token):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            new_password = data.get('new_password')
            retype_password = data.get('retype_password')

            if new_password != retype_password:
                return HttpResponse({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return HttpResponse({"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

            # Verify the token
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                return HttpResponse({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

            # Set the new password
            user.set_password(new_password)
            user.save()
            return HttpResponse({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
    except json.JSONDecodeError:
        return HttpResponse({"error": "Invalid JSON format."}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt  
def gadForm(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        response = GadResponse.objects.create(
            user_id= data.get('user_id'),  # Ensure user is correctly set
            question_1=data.get('question_1'),
            question_2=data.get('question_2'),
            question_3=data.get('question_3'),
            question_4=data.get('question_4'),
            question_5=data.get('question_5'),
            question_6=data.get('question_6'),
            question_7=data.get('question_7'),
            difficulty=data.get('difficulty'),
            is_filled = data.get('is_filled'),
            submitted_at=timezone.now()
        )
        response.save()
        return HttpResponse({'message': 'Form submitted successfully!'}, status=201)
    return HttpResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def getUserProfile(request):
    if request.method == "GET":
        # Extract userId from query parameters
        userId = request.GET.get('userId')
        
        # Check if userId is provided
        if not userId:
            return JsonResponse({'error': 'userId is required'}, status=400)

        try:
            # Retrieve user by ID
            user = User.objects.get(id=userId)
            userData = {
                'username': user.username,
                'email': user.email,
                'status': user.is_active,
                'datejoined': user.date_joined.strftime('%Y-%m-%d'),
            }
            return JsonResponse(userData, status=200)

        except User.DoesNotExist:
            return JsonResponse({"error": "User with this ID does not exist."}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@csrf_exempt
def updateUserProfile(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            userId = data.get('userId')
            username = data.get('username')
            email = data.get('email')
            
            # Ensure that required fields are provided
            if not userId or not username or not email:
                return JsonResponse({'error': 'userId, username, and email are required.'}, status=400)

            # Retrieve the user by ID
            user = User.objects.get(id=userId)
            user.username = username
            user.email = email
            user.save()

            # Return a success response
            return JsonResponse({'message': 'Profile updated successfully'}, status=200)

        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

gazeFile =  Path(__file__).resolve().parent / 'public' / 'GazeCoordinates.csv'
df = pd.read_csv(gazeFile)
x_coords = df['x']
labels = np.where(x_coords < 960, 0, 1)  # 0 = left, 1 = right

# Prepare the data for model training
X = x_coords.values.reshape(-1, 1)
y = labels
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the model
model = LogisticRegression()
model.fit(X_train, y_train)

@csrf_exempt
def predictView(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            xValue = data['x']

            predictions = model.predict(X_test)
            accuracy = accuracy_score(y_test, predictions)
            # print(f"Model Accuracy: {accuracy * 100:.2f}%")

            x_values = np.array(xValue).reshape(-1, 1)
            side = model.predict(x_values)

            # Count left and right occurrences
            left_count = (side == 0).sum()
            right_count = (side == 1).sum()

            # Determine final majority
            majority_side = "Left" if left_count>right_count else "Right"

            # "predictions": ["Left" if pred == 0 else "Right" for pred in side],
            
            response = {
                "left_count": int(left_count),
                "right_count": int(right_count),
                "final_prediction": majority_side,
                "test_date": timezone.now()
            }

            insertData = PredictionData.objects.create(
            user_id= data.get('user_id'),  # Ensure user is correctly set
            category_number=data.get('category_number'),
            left_count=response['left_count'],
            right_count=response['right_count'],
            final_prediction=response['final_prediction'],
            test_date = response['test_date'],
            )
            insertData.save()

            return JsonResponse(response)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Only POST method is allowed"}, status=405)


@csrf_exempt
def getUserGazeData(request):
    if request.method == 'GET':
        userId = request.GET.get('userId')
        
        if not userId:
            return JsonResponse({'error': 'user id is required'}, status=400)

        try:
            userGraphData = PredictionData.objects.filter(user_id=userId)
            data_list = list(userGraphData.values())
            return JsonResponse(data_list, safe=False)

        except json.JSONDecodeError:
            return JsonResponse({"status":"error","message":"Invalid format type."})
    
    return JsonResponse({"error": "Only GET method is allowed"}, status=405)
