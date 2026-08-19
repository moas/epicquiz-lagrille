from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.games.models import Participant

User = get_user_model()
INVALID_CREDENTIALS = "Invalid credentials."


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        required=False,
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        try:
            user = User.objects.get(username=attrs["username"])
        except User.DoesNotExist:
            raise serializers.ValidationError(INVALID_CREDENTIALS) from None

        if not user.is_active:
            raise serializers.ValidationError(INVALID_CREDENTIALS)

        if "password" in attrs:
            if not user.is_staff or not user.check_password(attrs["password"]):
                raise serializers.ValidationError(INVALID_CREDENTIALS)
        elif not Participant.objects.filter(user=user).exists():
            raise serializers.ValidationError(INVALID_CREDENTIALS)

        attrs["user"] = user
        return attrs
