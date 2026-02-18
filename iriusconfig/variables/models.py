from django.contrib.auth import get_user_model
from django.db import models
from general.mixins import RowAddedEditedModelMixin, ValueModelMixin
from modules.models import cnfModule

from iriusconfig.constants import ModelConstants

User = get_user_model()


class cnfVariableType(models.Model):
    """Справочник типов переменной."""

    n_type_value = models.IntegerField(
        verbose_name="Тип переменной - значение", unique=True
    )
    c_type_name = models.CharField(
        verbose_name="Тип переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH32,
    )
    c_type_desc = models.CharField(
        verbose_name="Описание типа переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Тип переменной"
        verbose_name_plural = "Типы переменных"

    def __str__(self):
        return self.c_type_desc


class cnfVariableDataType(models.Model):
    """Справочник типов данных для модуля."""

    n_type_value = models.IntegerField(
        verbose_name="Тип данных переменной - значение", unique=True
    )
    c_type_name = models.CharField(
        verbose_name="Имя типа данных переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH32,
    )
    c_type_desc = models.CharField(
        verbose_name="Описание типа данных переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Тип данных переменной"
        verbose_name_plural = "Типы данных переменных"

    def __str__(self):
        return self.c_type_desc


class cnfVariable(RowAddedEditedModelMixin):
    """Модель для переменных контроллера."""

    RELATED_NAME = "variable"

    n_variable_index = models.IntegerField(
        verbose_name="Индекс",
    )
    c_name_variable = models.CharField(
        verbose_name="Имя", max_length=ModelConstants.FIELD_MAX_LENGTH64
    )
    c_desc_variable = models.CharField(
        verbose_name="Описание",
        max_length=ModelConstants.FIELD_MAX_LENGTH2000,
        null=True,
        blank=True,
    )
    c_name_section = models.CharField(
        verbose_name="Наименование секции",
        max_length=ModelConstants.FIELD_MAX_LENGTH64,
        null=True,
        blank=True,
    )
    c_name_position = models.CharField(
        verbose_name="Наименование позиции",
        max_length=ModelConstants.FIELD_MAX_LENGTH64,
        null=True,
        blank=True,
    )
    c_num_position = models.CharField(
        verbose_name="Номер позиции",
        max_length=ModelConstants.FIELD_MAX_LENGTH16,
        null=True,
        blank=True,
    )

    n_module_id = models.ForeignKey(
        cnfModule,
        on_delete=models.SET_NULL,
        verbose_name="ID модуля",
        null=True,
        blank=True,
        related_name="variable_modules",
    )

    n_module_channel = models.IntegerField(
        verbose_name="Канал модуля", null=True, blank=True
    )

    n_variable_type = models.ForeignKey(
        cnfVariableType,
        on_delete=models.SET_NULL,
        verbose_name="Тип",
        null=True,
        related_name="variable_types",
    )
    n_variable_data_type = models.ForeignKey(
        cnfVariableDataType,
        on_delete=models.SET_NULL,
        verbose_name="Тип данных",
        null=True,
        related_name="variable_data_types",
    )
    b_masked = models.BooleanField(
        verbose_name="Замаскирован",
        default=False,
        # Если True - то замаскирован
    )
    c_signal_ident = models.CharField(
        verbose_name="Идентификатор сигнала",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
        null=True,
        blank=True,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Переменная"
        verbose_name_plural = "Переменные"


class cnfVariableValue(ValueModelMixin):
    """Модель для значений атрибутов переменных."""

    RELATED_NAME = "values"

    n_variable = models.ForeignKey(
        cnfVariable,
        on_delete=models.CASCADE,
        verbose_name="ID переменной из cnfVariable",
        related_name="variable",
    )

    c_formula = models.CharField(
        verbose_name="Формула",
        null=True,
        blank=True,
        # max_length=MAX
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Значение переменной"
        verbose_name_plural = "Значения переменной"


class cnfFormulaSymbol(models.Model):
    """Справочник символов для переменной."""

    # Цифры - 1
    # Переменная - 2
    # Агрегат - 3
    # Скобки - 4
    # Операции - 5
    # Тернарная операция - 6
    # Пробел - 7: Можно не учитывать и сразу обрезать при обработке

    n_type = models.SmallIntegerField(
        verbose_name="Тип символа",
    )
    n_nn_char = models.SmallIntegerField(
        verbose_name="Идентификатор символа (не используется)",
    )
    n_chr = models.IntegerField(verbose_name="Идентификатор символа", default=0)
    c_symbol = models.CharField(
        verbose_name="Символ",
        max_length=ModelConstants.FIELD_MAX_LENGTH2,
    )
    c_desc = models.CharField(
        verbose_name="Символ",
        max_length=ModelConstants.FIELD_MAX_LENGTH256,
        blank=True,
        null=True,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Описание символа для формулы переменной"
        verbose_name_plural = "Описания символов для формулы переменной"

    def __str__(self):
        return self.c_desc
