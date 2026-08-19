from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from core.games.models import Episode
from core.games.models import PrizeAttribute
from core.games.models import QueryConfig
from core.games.models import StealAttribute

from .serializers import EpisodeSerializer
from .serializers import ParticipantSerializer
from .serializers import PrizeAttributeSerializer
from .serializers import QueryConfigSerializer
from .serializers import StealAttributeSerializer


class EpisodeViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Episode.objects.all()
    serializer_class = EpisodeSerializer
    permission_classes = [IsAdminUser]

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
