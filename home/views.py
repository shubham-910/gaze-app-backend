from django.shortcuts import HttpResponse, redirect
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from django.contrib.auth  import authenticate,  login, logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
import json
from .models import GadResponse, PredictionData, CategoryData
from django.utils import timezone
from django.http import JsonResponse
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from pathlib import Path
import random

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
                send_mail(
                subject="Account Registration Successful - GazeTrack",
                message=f"""
                        Dear {myuser.username or 'User'},
                        
                        Welcome to the GazeTrack. Your account has been successfully created with us.

                        We are happy to have you on our website. Enjoy our aaplication.

                        Best regards,
                        The GazeTrack Team
                    """,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[myuser.email],
                fail_silently=False,
                )
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
                subject="Password Reset Request - GazeTrack",
                message=f"""
                        Dear {user.username or 'User'},
                        
                        We received a request to reset the password for your account on GazeTrack. If you initiated this request, please click the link below to reset your password:

                        {reset_url}

                        If you did not request a password reset, please ignore this email.

                        For your security, this link will expire in 24 hours.

                        Thank you for using GazeTrack!

                        Best regards,
                        The GazeTrack Team
                    """,
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
                print("email:")
                print(user.email)
            except User.DoesNotExist:
                return HttpResponse({"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

            # Verify the token
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                return HttpResponse({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

            # Set the new password
            user.set_password(new_password)
            send_mail(
                subject="Password Reset successful - GazeTrack",
                message=f"""
                    Dear {user.username or 'User'},
                    
                    Your password for the account associated with {user.email} on GazeTrack has been successfully updated.
                    
                    Please use your new credentials to log in to your account.

                    Thank you for using GazeTrack!

                    Best regards,
                    The GazeTrack Team
                """,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
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
def getGadResponse(request, user_id):
    if request.method == "GET":
        try:
            # Get the latest GAD response for the user
            gad_response = GadResponse.objects.filter(user_id=user_id, is_filled=True).latest('submitted_at')
            return JsonResponse({
                "question_1": gad_response.question_1,
                "question_2": gad_response.question_2,
                "question_3": gad_response.question_3,
                "question_4": gad_response.question_4,
                "question_5": gad_response.question_5,
                "question_6": gad_response.question_6,
                "question_7": gad_response.question_7,
                "difficulty": gad_response.difficulty,
            })
        except GadResponse.DoesNotExist:
            return JsonResponse({"error": "No GAD response found for the user."}, status=404)
    return JsonResponse({"error": "Only GET method is allowed"}, status=405)

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
            print(f"Model Accuracy: {accuracy * 100:.2f}%")

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
            response['id'] = insertData.id

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

# @csrf_exempt
# def updatePrediction(request, prediction_id):
#     if request.method == 'PATCH':
#         try:
#             data = json.loads(request.body)
#             result_data = data.get('result_data')

#             if not result_data:
#                 return JsonResponse({"error": "result_data is required"}, status=400)

#             # Update the specific record
#             prediction = PredictionData.objects.get(id=prediction_id)
#             prediction.result_data = result_data
#             prediction.save()

#             return JsonResponse({"status": "success", "message": "Result data updated successfully."})
#         except PredictionData.DoesNotExist:
#             return JsonResponse({"error": "Prediction not found"}, status=404)
#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=400)

#     return JsonResponse({"error": "Only PATCH method is allowed"}, status=405)


@csrf_exempt
def addCategory(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Parse JSON data from the request body

            # Check if the input is a list or a single object
            if isinstance(data, list):  # Multiple entries
                created_records = []
                created_records = []
                for item in data:
                    # Extract fields from each item
                    category_number = item.get("category_number")
                    category_name = item.get("category_name")
                    is_positive = item.get("is_positive")
                    image_metadata = item.get("image_metadata")
                    image_description = item.get("image_description")

                    # Validate fields
                    if not all([category_number, category_name, is_positive, image_metadata, image_description]):
                        return JsonResponse({"error": "All fields are required for each entry."}, status=400)

                    # Create a new record
                    category = CategoryData.objects.create(
                        category_number=category_number,
                        category_name=category_name,
                        is_positive=is_positive,
                        image_metadata=image_metadata,
                        image_description=image_description,
                    )
                    created_records.append({
                        "id": category.id,
                        "category_number": category.category_number,
                        "category_name": category.category_name,
                        "is_positive": category.is_positive,
                        "image_metadata": category.image_metadata,
                        "image_description": category.image_description,
                    })

                # Return response for all created records
                return JsonResponse({"created_records": created_records}, status=201)

            elif isinstance(data, dict):  # Single entry
                # Extract fields
                category_number = data.get("category_number")
                category_name = data.get("category_name")
                is_positive = data.get("is_positive")
                image_metadata = data.get("image_metadata")
                image_description = data.get("image_description")

                # Validate fields
                if not all([category_number, category_name, is_positive, image_metadata, image_description]):
                    return JsonResponse({"error": "All fields are required."}, status=400)

                # Create a new record
                category = CategoryData.objects.create(
                    category_number=category_number,
                    category_name=category_name,
                    is_positive=is_positive,
                    image_metadata=image_metadata,
                    image_description=image_description,
                )

                # Return success response for single record
                return JsonResponse(
                    {
                        "id": category.id,
                        "category_number": category.category_number,
                        "category_name": category.category_name,
                        "is_positive": category.is_positive,
                        "image_metadata": category.image_metadata,
                        "image_description": category.image_description,
                    },
                    status=201,
                )

            else:
                return JsonResponse({"error": "Invalid data format. Provide a JSON object or array."}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
    else:
        return JsonResponse({"error": "Only POST method is allowed."}, status=405)


@csrf_exempt
def getCategoryPhotos(request):
    if request.method == "GET":
        try:
            # Get category_number from query parameters
            category_number = request.GET.get('category_number')

            # Check if category_number is provided
            if not category_number:
                return JsonResponse({"error": "Missing parameter."}, status=400)

            # Fetch all positive and negative photos for the category
            positive_photos = CategoryData.objects.filter(category_number=category_number, is_positive=1)
            negative_photos = CategoryData.objects.filter(category_number=category_number, is_positive=0)

            # If no data found, return an appropriate message
            if not positive_photos.exists() or not negative_photos.exists():
                return JsonResponse({"message": "Not enough data to generate pairs."}, status=404)

            # Randomly select 3 pairs (1 positive + 1 negative per pair)
            pairs = []
            for _ in range(3):
                if positive_photos.exists() and negative_photos.exists():
                    positive = random.choice(positive_photos)
                    negative = random.choice(negative_photos)

                    # Add pair to the result
                    pairs.append({
                        "negative_image": {
                            "id": negative.id,
                            "image_metadata": negative.image_metadata,
                            "image_description": negative.image_description,
                        },
                        "positive_image": {
                            "id": positive.id,
                            "image_metadata": positive.image_metadata,
                            "image_description": positive.image_description,
                        },
                    })

                    # Remove selected items to avoid repetition
                    positive_photos = positive_photos.exclude(id=positive.id)
                    negative_photos = negative_photos.exclude(id=negative.id)

            # Return the pairs
            return JsonResponse({"pairs": pairs}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Only GET method is allowed."}, status=405)