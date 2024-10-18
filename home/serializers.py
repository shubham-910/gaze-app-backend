from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new user.
    """
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('name', 'email', 'password', 'password2')

    def validate(self, data):
        """
        Check that the two passwords match.
        """
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords must match.")
        return data

    def create(self, validated_data):
        """
        Create a new user after ensuring the passwords match.
        """
        validated_data.pop('password2')  # Remove password2 field
        user = User.objects.create_user(**validated_data)  # Create user with the validated data
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """
        Validate the user credentials.
        """
        email = data.get('email')
        password = data.get('password')

        # Authenticate using the custom user model and email
        user = authenticate(request=self.context.get('request'), username=email, password=password)

        if user is None:
            raise serializers.ValidationError(_('Invalid credentials or inactive user.'))

        # Check if the user is active
        if not user.is_active:
            raise serializers.ValidationError(_('User account is deactivated.'))

        return user
