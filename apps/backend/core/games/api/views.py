from django.db import transaction
from django.shortcuts import get_object_or_404
from django_fsm import can_proceed
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from core.games.models import Episode
from core.games.models import PrizeAttribute
from core.games.models import QueryConfig
from core.games.models import StealAttribute
from core.grid.models import Cell
from core.grid.models import Grid

from .filters import EpisodeFilter
from .serializers import CoordinateFormatSerializer
from .serializers import EpisodeSerializer
from .serializers import GridConfigSerializer
from .serializers import ParticipantSerializer
from .serializers import PrizeAttributeSerializer
from .serializers import QueryConfigSerializer
from .serializers import StealAttributeSerializer


class EpisodeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Episode.objects.all()
    serializer_class = EpisodeSerializer
    permission_classes = [IsAdminUser]
    filterset_class = EpisodeFilter

    def perform_update(self, serializer):
        self._ensure_not_ended(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_not_ended(instance)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="start", url_name="start")
    def start_episode(self, request, pk=None):
        with transaction.atomic():
            episode = Episode.objects.select_for_update().get(pk=pk)
            if not can_proceed(episode.start):
                return self._conflict("This episode cannot start yet.")
            episode.start()
            episode.save(update_fields=["state", "modified"])

        return Response(EpisodeSerializer(episode).data)

    @action(detail=True, methods=["post"], url_path="end", url_name="end")
    def end_episode(self, request, pk=None):
        with transaction.atomic():
            episode = Episode.objects.select_for_update().get(pk=pk)
            if not can_proceed(episode.end):
                return self._conflict("This episode cannot end yet.")
            episode.end()
            episode.save(update_fields=["state", "modified"])

        return Response(EpisodeSerializer(episode).data)

    @action(detail=True, methods=["post", "delete"], url_path="grid", url_name="grid")
    def grid(self, request, pk=None):
        with transaction.atomic():
            episode = Episode.objects.select_for_update().get(pk=pk)
            if episode.state != Episode.State.PENDING:
                return self._conflict(
                    "A grid can only change while the episode is pending.",
                )

            if request.method == "DELETE":
                grid = get_object_or_404(Grid, episode=episode)
                grid.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            if Grid.objects.filter(episode=episode).exists():
                return self._conflict("This episode already has a grid.")

            serializer = GridConfigSerializer(data=episode.metadata.get("grid_config"))
            serializer.is_valid(raise_exception=True)
            config = serializer.validated_data
            x_labels = CoordinateFormatSerializer.labels(
                config["coordinate_format"]["x"],
            )
            y_labels = CoordinateFormatSerializer.labels(
                config["coordinate_format"]["y"],
            )
            grid = Grid.objects.create(
                episode=episode,
                rows=config["rows"],
                columns=config["columns"],
                empty_cell_count=config["empty_cell_count"],
                point_distribution=config["point_distribution"],
            )
            Cell.objects.bulk_create(
                [
                    Cell(
                        grid=grid,
                        x=x,
                        y=y,
                        name=f"{x_labels[x]}{y_labels[y]}",
                    )
                    for x in range(config["rows"])
                    for y in range(config["columns"])
                ],
            )

        return Response(self._serialize_grid(grid), status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="participants",
        url_name="participants",
    )
    def participants(self, request, pk=None):
        episode = self.get_object()

        if request.method == "GET":
            queryset = episode.participants.select_related("user")
            serializer = ParticipantSerializer(queryset, many=True)
            return Response(serializer.data)

        self._ensure_not_ended(episode)
        serializer = ParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(episode=episode)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["get", "put", "patch", "delete"],
        url_path=r"participants/(?P<participant_id>[^/.]+)",
        url_name="participant",
    )
    def participant(self, request, participant_id=None, pk=None):
        episode = self.get_object()
        participant = get_object_or_404(
            episode.participants.select_related("user"),
            pk=participant_id,
        )

        if request.method == "GET":
            return Response(ParticipantSerializer(participant).data)

        self._ensure_not_ended(episode)
        if request.method == "DELETE":
            participant.is_active = False
            participant.save(update_fields=["is_active", "modified"])
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = ParticipantSerializer(
            participant,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="query-configs",
        url_name="query-configs",
    )
    def query_configs(self, request, pk=None):
        episode = self.get_object()

        if request.method == "GET":
            serializer = QueryConfigSerializer(episode.queries_config.all(), many=True)
            return Response(serializer.data)

        self._ensure_not_ended(episode)
        serializer = QueryConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query_config = serializer.save(episode=episode)
        return Response(
            QueryConfigSerializer(query_config).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get", "put", "patch", "delete"],
        url_path=r"query-configs/(?P<query_config_id>[^/.]+)",
        url_name="query-config",
    )
    def query_config(self, request, query_config_id=None, pk=None):
        episode = self.get_object()
        query_config = get_object_or_404(
            QueryConfig.objects.filter(episode=episode),
            pk=query_config_id,
        )

        if request.method == "GET":
            return Response(QueryConfigSerializer(query_config).data)

        self._ensure_not_ended(episode)
        if request.method == "DELETE":
            query_config.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = QueryConfigSerializer(
            query_config,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="steal-attributes",
        url_name="steal-attributes",
    )
    def steal_attributes(self, request, pk=None):
        return self._attribute_collection(
            request,
            self.get_object(),
            StealAttribute,
            StealAttributeSerializer,
        )

    @action(
        detail=True,
        methods=["get", "put", "patch", "delete"],
        url_path=r"steal-attributes/(?P<attribute_id>[^/.]+)",
        url_name="steal-attribute",
    )
    def steal_attribute(self, request, attribute_id=None, pk=None):
        return self._attribute_detail(
            request,
            self.get_object(),
            attribute_id,
            StealAttribute,
            StealAttributeSerializer,
        )

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="prize-attributes",
        url_name="prize-attributes",
    )
    def prize_attributes(self, request, pk=None):
        return self._attribute_collection(
            request,
            self.get_object(),
            PrizeAttribute,
            PrizeAttributeSerializer,
        )

    @action(
        detail=True,
        methods=["get", "put", "patch", "delete"],
        url_path=r"prize-attributes/(?P<attribute_id>[^/.]+)",
        url_name="prize-attribute",
    )
    def prize_attribute(self, request, attribute_id=None, pk=None):
        return self._attribute_detail(
            request,
            self.get_object(),
            attribute_id,
            PrizeAttribute,
            PrizeAttributeSerializer,
        )

    @staticmethod
    def _attribute_collection(request, episode, model_class, serializer_class):
        if request.method == "GET":
            queryset = model_class.objects.filter(episode=episode)
            return Response(serializer_class(queryset, many=True).data)

        EpisodeViewSet._ensure_not_ended(episode)
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        attribute = serializer.save(episode=episode)
        return Response(
            serializer_class(attribute).data,
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _attribute_detail(
        request,
        episode,
        attribute_id,
        model_class,
        serializer_class,
    ):
        attribute = get_object_or_404(model_class, episode=episode, pk=attribute_id)

        if request.method == "GET":
            return Response(serializer_class(attribute).data)

        EpisodeViewSet._ensure_not_ended(episode)
        if request.method == "DELETE":
            attribute.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = serializer_class(
            attribute,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @staticmethod
    def _conflict(detail: str):
        return Response({"detail": detail}, status=status.HTTP_409_CONFLICT)

    @staticmethod
    def _ensure_not_ended(episode):
        if episode.state == Episode.State.END:
            message = "An ended episode is immutable."
            raise PermissionDenied(message)

    @staticmethod
    def _serialize_grid(grid):
        return {
            "id": grid.pk,
            "rows": grid.rows,
            "columns": grid.columns,
            "empty_cell_count": grid.empty_cell_count,
            "point_distribution": grid.point_distribution,
        }
