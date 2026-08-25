from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django_fsm import can_proceed
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from core.games.models import Episode
from core.games.models import EpisodeQuestion
from core.games.models import PrizeAttribute
from core.games.models import QueryConfig
from core.games.models import SpecialAttribute
from core.games.models import StealAttribute
from core.games.selectors import eligible_questions_for_episode
from core.games.services import select_episode_question
from core.grid.models import Cell
from core.grid.models import Grid
from core.grid.services import save_attribute_dispatch
from core.grid.services import save_challenge_dispatch
from core.qa.api.filters import QuestionFilter
from core.qa.api.serializers import QuestionSerializer

from .filters import EpisodeFilter
from .filters import ParticipantFilter
from .serializers import AttributeDispatchSerializer
from .serializers import ChallengeDispatchSerializer
from .serializers import CoordinateFormatSerializer
from .serializers import EpisodeQuestionSelectionSerializer
from .serializers import EpisodeSerializer
from .serializers import GridConfigSerializer
from .serializers import ParticipantSerializer
from .serializers import PrizeAttributeSerializer
from .serializers import QueryConfigSerializer
from .serializers import StealAttributeSerializer


class EpisodeViewSet(viewsets.ModelViewSet):
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

    @action(
        detail=True,
        methods=["get"],
        url_path="readiness",
        url_name="readiness",
    )
    def readiness(self, request, pk=None):
        episode = self.get_object()
        missing_roles = sorted(episode.missing_start_roles())
        return Response(
            {
                "grid_locked": episode.has_locked_grid(),
                "missing_roles": missing_roles,
                "can_start": episode.state == Episode.State.PENDING
                and episode.can_start(),
            },
        )

    @action(
        detail=True,
        methods=["get", "post", "delete"],
        url_path="grid",
        url_name="grid",
    )
    def grid(self, request, pk=None):
        if request.method == "GET":
            grid = get_object_or_404(Grid, episode_id=pk)
            return Response(self._serialize_grid(grid))

        with transaction.atomic():
            episode = Episode.objects.select_for_update().get(pk=pk)
            if episode.state != Episode.State.PENDING:
                return self._conflict(
                    "A grid can only change while the episode is pending.",
                )

            if request.method == "DELETE":
                grid = get_object_or_404(Grid, episode=episode)
                grid.delete()
                # A locked grid is restarted as a whole: its configuration and
                # special attributes must not survive into the next draw.
                episode.special_attributes.all().delete()
                metadata = dict(episode.metadata)
                metadata.pop("grid_config", None)
                episode.metadata = metadata
                episode.save(update_fields=["metadata", "modified"])
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
                max_attrs_per_cell=config["max_attrs_per_cell"],
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
        methods=["get"],
        url_path="selected-questions",
        url_name="selected-questions",
    )
    def selected_questions(self, request, pk=None):
        episode = self.get_object()
        questions = (
            eligible_questions_for_episode(episode)
            .filter(episode_selections__episode=episode)
            .order_by("level", "label")
            .distinct()
        )
        return Response(QuestionSerializer(questions, many=True).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="challenge-dispatch",
        url_name="challenge-dispatch",
    )
    def challenge_dispatch(self, request, pk=None):
        episode = self.get_object()
        self._ensure_not_ended(episode)
        config_serializer = GridConfigSerializer(
            data=episode.metadata.get("grid_config"),
        )
        config_serializer.is_valid(raise_exception=True)
        serializer = ChallengeDispatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            grid = save_challenge_dispatch(
                episode_id=episode.pk,
                config=config_serializer.validated_data,
                assignments=serializer.validated_data["assignments"],
            )
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict) from error
        return Response(self._serialize_grid(grid), status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="attribute-dispatch",
        url_name="attribute-dispatch",
    )
    def attribute_dispatch(self, request, pk=None):
        episode = self.get_object()
        self._ensure_not_ended(episode)
        serializer = AttributeDispatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            grid = save_attribute_dispatch(
                episode_id=episode.pk,
                assignments=serializer.validated_data["assignments"],
            )
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict) from error
        return Response(self._serialize_grid(grid))

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="participants",
        url_name="participants",
    )
    def participants(self, request, pk=None):
        episode = get_object_or_404(self.get_queryset(), pk=pk)

        if request.method == "GET":
            queryset = ParticipantFilter(
                request.query_params,
                queryset=episode.participants.select_related("user"),
            ).qs
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
        methods=["get", "post"],
        url_path="questions",
        url_name="questions",
    )
    def questions(self, request, pk=None):
        episode = self.get_object()
        eligible_questions = eligible_questions_for_episode(episode).order_by("label")

        if request.method == "POST":
            self._ensure_not_ended(episode)
            serializer = EpisodeQuestionSelectionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                selection = select_episode_question(
                    episode=episode,
                    question_id=serializer.validated_data["question_id"],
                )
            except DjangoValidationError as error:
                raise ValidationError(error.message_dict) from error
            return Response(
                {"question_id": selection.question_id},
                status=status.HTTP_201_CREATED,
            )

        selected_ids = {
            str(question_id)
            for question_id in EpisodeQuestion.objects.filter(
                episode=episode,
                question__in=eligible_questions,
            ).values_list("question_id", flat=True)
        }
        filtered_questions = QuestionFilter(
            request.query_params,
            queryset=eligible_questions,
        ).qs
        page = self.paginate_queryset(filtered_questions)
        page_questions = page if page is not None else filtered_questions
        serialized_questions = QuestionSerializer(page_questions, many=True).data
        results = [
            {**question, "is_selected": question["id"] in selected_ids}
            for question in serialized_questions
        ]
        eligible_count = eligible_questions.count()
        selected_by_level = {
            str(item["question__level"]): item["count"]
            for item in EpisodeQuestion.objects.filter(
                episode=episode,
                question__in=eligible_questions,
            )
            .values("question__level")
            .annotate(count=Count("id"))
        }

        if page is not None:
            response = self.get_paginated_response(results)
            response.data["eligible_count"] = eligible_count
            response.data["selected_count"] = len(selected_ids)
            response.data["selected_by_level"] = selected_by_level
            return response
        return Response(
            {
                "eligible_count": eligible_count,
                "selected_count": len(selected_ids),
                "selected_by_level": selected_by_level,
                "results": results,
            },
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"questions/(?P<question_id>[^/.]+)",
        url_name="question",
    )
    def question(self, request, question_id=None, pk=None):
        episode = self.get_object()
        self._ensure_not_ended(episode)
        selection = get_object_or_404(
            EpisodeQuestion,
            episode=episode,
            question_id=question_id,
        )
        selection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["get", "put", "patch", "delete"],
        url_path=r"participants/(?P<participant_id>[^/.]+)",
        url_name="participant",
    )
    def participant(self, request, participant_id=None, pk=None):
        episode = get_object_or_404(self.get_queryset(), pk=pk)
        participant = get_object_or_404(
            episode.participants.select_related("user"),
            pk=participant_id,
        )

        if request.method == "GET":
            return Response(ParticipantSerializer(participant).data)

        if request.method == "DELETE":
            if episode.state == Episode.State.PENDING:
                participant.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            participant.is_active = False
            participant.save(update_fields=["is_active", "modified"])
            return Response(status=status.HTTP_204_NO_CONTENT)

        self._ensure_not_ended(episode)
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

    @action(
        detail=True,
        methods=["get"],
        url_path="special-attributes-summary",
        url_name="special-attributes-summary",
    )
    def special_attributes_summary(self, request, pk=None):
        episode = self.get_object()
        queryset = SpecialAttribute.objects.filter(episode=episode)
        return Response(
            {
                "active_count": queryset.filter(is_active=True).count(),
                "total_count": queryset.count(),
            },
        )

    @staticmethod
    def _attribute_collection(request, episode, model_class, serializer_class):
        if request.method == "GET":
            queryset = model_class.objects.filter(episode=episode)
            return Response(serializer_class(queryset, many=True).data)

        EpisodeViewSet._ensure_not_ended(episode)
        EpisodeViewSet._ensure_attributes_editable(episode)
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        # The manager does not expose an activation control at creation time:
        # every new special attribute must therefore be immediately drawable.
        attribute = serializer.save(episode=episode, is_active=True)
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
        EpisodeViewSet._ensure_attributes_editable(episode)
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
    def _ensure_attributes_editable(episode):
        try:
            grid = episode.grid
        except Grid.DoesNotExist:
            return
        if grid.state == Grid.GridState.ATTRIBUTES_DRAWN:
            message = "Attributes are locked after their confirmed dispatch."
            raise PermissionDenied(message)

    @staticmethod
    def _serialize_grid(grid):
        return {
            "id": grid.pk,
            "rows": grid.rows,
            "columns": grid.columns,
            "empty_cell_count": grid.empty_cell_count,
            "point_distribution": grid.point_distribution,
            "max_attrs_per_cell": grid.max_attrs_per_cell,
            "state": grid.state,
            "cells": list(
                grid.cells.order_by("x", "y").values(
                    "id",
                    "name",
                    "x",
                    "y",
                    "challenge_id",
                ),
            ),
        }
