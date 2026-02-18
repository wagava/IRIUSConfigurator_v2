from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from iriusconfig.constants import ModelConstants

from .models import cnfAttribute, cnfController

User = get_user_model()


class RowAddedEditedModelMixin(models.Model):
    """
    Абстрактная модель. Добвляет дату и
    время создания записи в created_at,
    а также поля n_controller, d_last_edit,
    c_user_edit
    """

    RELATED_NAME = "+"

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Добавлено",
    )

    n_controller = models.ForeignKey(
        cnfController,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Контроллер",
        related_name=RELATED_NAME,
    )
    d_last_edit = models.DateTimeField(
        max_length=256, verbose_name="Дата и время обновления", default=timezone.now
    )
    c_user_edit = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Редактор",
        related_name=RELATED_NAME,
    )

    class Meta:
        """Конструктор."""

        abstract = True


class ValueModelMixin(models.Model):
    """Миксин-класс для добавления полей
    в таблицы cnf___Value."""

    RELATED_NAME = "+"

    n_attribute = models.ForeignKey(
        cnfAttribute,
        on_delete=models.CASCADE,
        verbose_name="Attribute ID",
        null=True,
        related_name=RELATED_NAME,
    )
    f_value = models.FloatField(
        verbose_name="Значение",
    )
    c_note = models.CharField(
        verbose_name="Заметка",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
        null=True,
        blank=True,
    )

    class Meta:
        """Конструктор."""

        abstract = True
