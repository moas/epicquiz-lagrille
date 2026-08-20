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
CELL_NAME_MAX_LENGTH = 5


class CoordinateFormatSerializer(serializers.Serializer):
    x = serializers.CharField()
    y = serializers.CharField()

    @staticmethod
    def labels(value):
        return [label.strip() for label in value.split(",")]


class GridConfigSerializer(serializers.Serializer):
    version = serializers.IntegerField(default=1, min_value=1)
    rows = serializers.IntegerField(min_value=1, max_value=99)
    columns = serializers.IntegerField(min_value=1, max_value=99)
    empty_cell_count = serializers.IntegerField(min_value=0)
    point_distribution = serializers.DictField(
        child=serializers.IntegerField(min_value=0),
    )
    coordinate_format = CoordinateFormatSerializer()

    def validate(self, attrs):
        cell_count = attrs["rows"] * attrs["columns"]
        if attrs["empty_cell_count"] >= cell_count:
            raise serializers.ValidationError(
                {"empty_cell_count": "It must leave at least one playable cell."},
            )

        point_cell_count = sum(attrs["point_distribution"].values())
        if point_cell_count != cell_count - attrs["empty_cell_count"]:
            raise serializers.ValidationError(
                {"point_distribution": "It must cover every playable cell."},
            )

        coordinate_format = attrs["coordinate_format"]
        for axis, expected_size in (
            ("x", attrs["rows"]),
            ("y", attrs["columns"]),
        ):
            labels = CoordinateFormatSerializer.labels(coordinate_format[axis])
            if len(labels) != expected_size:
                raise serializers.ValidationError(
                    {
                        "coordinate_format": {
                            axis: f"It must contain exactly {expected_size} labels.",
                        },
                    },
                )
            if len(labels) != len(set(labels)):
                raise serializers.ValidationError(
                    {"coordinate_format": {axis: "Labels must be unique."}},
                )
            if any(not label for label in labels):
                raise serializers.ValidationError(
                    {"coordinate_format": {axis: "Labels cannot be empty."}},
                )
            if any(len(label) >= CELL_NAME_MAX_LENGTH for label in labels):
                raise serializers.ValidationError(
                    {
                        "coordinate_format": {
                            axis: (
                                f"Each label must be shorter than "
                                f"{CELL_NAME_MAX_LENGTH} characters."
                            ),
                        },
                    },
                )

        x_labels = CoordinateFormatSerializer.labels(coordinate_format["x"])
        y_labels = CoordinateFormatSerializer.labels(coordinate_format["y"])

        longest_name_size = max(
            len(x_label) + len(y_label)
            for x_label in x_labels
            for y_label in y_labels
        )
        if longest_name_size > CELL_NAME_MAX_LENGTH:
            raise serializers.ValidationError(
                {
                    "coordinate_format": (
                        f"Combined coordinate labels must not exceed "
                        f"{CELL_NAME_MAX_LENGTH} characters."
                    ),
                },
            )

        cell_names = {
            f"{x_label}{y_label}"
            for x_label in x_labels
            for y_label in y_labels
        }
        if len(cell_names) != cell_count:
            raise serializers.ValidationError(
                {
                    "coordinate_format": (
                        "Coordinate labels must produce a unique name for each cell."
                    ),
                },
            )

        return attrs


class EpisodeMetadataSerializer(serializers.Serializer):
    grid_config = GridConfigSerializer(required=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"metadata": "Expected an object."})

        unknown_keys = set(data) - {"grid_config"}
        if unknown_keys:
            unsupported_keys = ", ".join(sorted(unknown_keys))
            raise serializers.ValidationError(
                {"metadata": f"Unsupported keys: {unsupported_keys}."},
            )

        return super().to_internal_value(data)


class EpisodeSerializer(serializers.ModelSerializer):
    metadata = EpisodeMetadataSerializer(required=False)

    class Meta:
        model = Episode
        fields = ["id", "title", "time_slot", "metadata", "is_active", "state"]
        read_only_fields = ["id", "state"]

    def validate(self, attrs):
        if self.instance and "metadata" in attrs and self.instance.has_grid():
            previous_config = self.instance.metadata.get("grid_config")
            next_config = attrs["metadata"].get("grid_config")
            if previous_config != next_config:
                raise serializers.ValidationError(
                    {"metadata": "grid_config cannot change after grid creation."},
                )

        return attrs


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
