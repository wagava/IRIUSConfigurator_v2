from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from general.mixins import RowAddedEditedModelMixin, ValueModelMixin
from general.models import cnfAttribute, cnfController

from iriusconfig.constants import ModelConstants

User = get_user_model()


class cnfModule(RowAddedEditedModelMixin):
    """Модель для модулей контроллера."""

    RELATED_NAME = "module"

    n_module_index = models.IntegerField(
        verbose_name="Индекс модуля",
    )
    c_name_module = models.CharField(
        verbose_name="Имя модуля", max_length=ModelConstants.FIELD_MAX_LENGTH64
    )
    c_desc_module = models.CharField(
        verbose_name="Описание модуля", max_length=ModelConstants.FIELD_MAX_LENGTH255
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Модуль"
        verbose_name_plural = "Модули"

    def __str__(self):
        """Магический метод."""
        return (
            str(self.n_controller)
            + ":  "
            + self.c_name_module
            + "  -   "
            + self.c_desc_module
        )


class cnfModuleType(models.Model):
    """Справочник типов модуля."""

    n_type_value = models.IntegerField(
        verbose_name="Тип модуля - значение", unique=True
    )
    c_type_name = models.CharField(
        verbose_name="Тип модуля", max_length=ModelConstants.FIELD_MAX_LENGTH32
    )
    c_type_desc = models.CharField(
        verbose_name="Описание типа модуля",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Тип модуля"
        verbose_name_plural = "Типы модулей"


class cnfModuleDataType(models.Model):
    """Справочник типов данных для модуля."""

    n_type_value = models.IntegerField(
        verbose_name="Тип данных модуля - значение", unique=True
    )
    c_type_name = models.CharField(
        verbose_name="Имя типа данных модуля",
        max_length=ModelConstants.FIELD_MAX_LENGTH32,
    )
    c_type_desc = models.CharField(
        verbose_name="Описание типа данных модуля",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Тип данных модуля"
        verbose_name_plural = "Типы данных модулей"


class cnfModuleValue(ValueModelMixin):
    """Модель для значений модулей контроллера."""

    RELATED_NAME = "values"

    n_module = models.ForeignKey(
        cnfModule,
        on_delete=models.CASCADE,
        verbose_name="Module ID",
        related_name="attr_values",
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Значение модуля"
        verbose_name_plural = "Значения модуля"
