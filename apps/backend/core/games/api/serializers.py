from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from core.games.models import Episode
from core.games.models import Participant
from core.games.models import PrizeAttribute
from core.games.models import QueryConfig
from core.games.models import StealAttribute
from core.helpers.functional import generate_username

User = get_user_model()
UNIQUE_USERNAME_ERROR = "Could not generate a unique username."


class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = ["id", "title", "time_slot", "metadata", "is_active"]
        read_only_fields = ["id"]


class ParticipantSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name")
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Participant
        fields = ["id", "username", "name", "role", "is_active", "tags"]
        read_only_fields = ["id", "username"]

    def create(self, validated_data):
        name = validated_data.pop("user")["name"]
        user = self._create_user(name)
        return Participant.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        if "name" in user_data:
            instance.user.name = user_data["name"]
            instance.user.save(update_fields=["name"])

        return super().update(instance, validated_data)

    @staticmethod
    def _create_user(name: str):
        for _ in range(10):
            try:
                return User.objects.create_user(
                    username=generate_username(6),
                    name=name,
                )
            except IntegrityError:
                continue

        raise serializers.ValidationError(UNIQUE_USERNAME_ERROR)


class QueryConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryConfig
        fields = ["id", "join", "mode", "tags", "level"]
        read_only_fields = ["id"]


class StealAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StealAttribute
        fields = ["id", "is_active"]
        read_only_fields = ["id"]


class PrizeAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrizeAttribute
        fields = ["id", "is_active", "name", "description", "image"]
        read_only_fields = ["id"]
