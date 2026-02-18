from django.contrib.auth import get_user_model
from django.db import models
from general.mixins import RowAddedEditedModelMixin, ValueModelMixin
# from general.models import cnfAttribute, cnfController
from variables.models import cnfVariable

from iriusconfig.constants import ModelConstants

User = get_user_model()


class cnfEquipmentType(models.Model):
    """Справочник типов оборудования."""

    n_type_value = models.IntegerField(
        verbose_name="Тип оборудования - значение", unique=True
    )
    c_type_name = models.CharField(
        verbose_name="Тип оборудования", max_length=ModelConstants.FIELD_MAX_LENGTH32
    )
    c_type_desc = models.CharField(
        verbose_name="Описание типа оборудования",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
    )
    # n_global_object_type - соответствует n_global_object_type в general_cnfattribute
    n_global_object_type = models.PositiveSmallIntegerField(
        verbose_name="Тип глобального объекта: Модули, Переменные, Оборудование...",
        # Модули: 1
        # Переменные: 2
        # Оборудование(Задвижка-Клапан/ с ЧРП): 11, 12
        # Оборудование(Электропривод/ с ЧРП): 13, 14
        # Оборудование(Аналоговый ПИД-регулятор): 15
        # Оборудование(ПИД-регулятор - ШИМ): 16
        # Оборудование(Пороговый регулятор): 17
        # Оборудование(Последовательность): 18
        # Оборудование(АВР): 19
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Тип оборудования"
        verbose_name_plural = "Типы оборудования"

    def __str__(self):
        return self.c_type_desc


class cnfEquipment(RowAddedEditedModelMixin):
    """Модель для оборудования."""

    RELATED_NAME = "equipment"

    n_equipment_index = models.IntegerField(
        verbose_name="Индекс",
    )
    c_name_equipment = models.CharField(
        verbose_name="Имя", max_length=ModelConstants.FIELD_MAX_LENGTH64
    )
    c_desc_equipment = models.CharField(
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
        max_length=ModelConstants.FIELD_MAX_LENGTH64,
        null=True,
        blank=True,
    )

    n_type_id = models.ForeignKey(
        cnfEquipmentType,
        on_delete=models.SET_NULL,
        verbose_name="Тип оборудования",
        null=True,
        related_name=RELATED_NAME,
    )
    b_masked = models.BooleanField(
        verbose_name="Замаскирован",
        default=False,
        # Если True - то замаскирован
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Переменная"
        verbose_name_plural = "Переменные"

    def __str__(self):
        return self.c_desc_equipment


class cnfEquipmentValue(ValueModelMixin):
    """Модель для значений оборудования."""

    RELATED_NAME = "values"

    n_equipment = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="ID оборудования из cnfEquipment",
        related_name="equipment",
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Значение переменной"
        verbose_name_plural = "Значения переменной"


class cnfEquipmentVariableRole(models.Model):
    """Справочник роли переменных."""

    n_role_index = models.IntegerField(
        verbose_name="Индекс роли переменной", unique=True
    )
    c_role_name = models.CharField(
        verbose_name="Имя флага роли переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
        blank=True,
        null=True,
    )

    c_role_desc = models.CharField(
        verbose_name="Описание роли переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH512,
    )
    
    c_role_oper_desc = models.CharField(
        verbose_name="Описание роли переменной для оператора",
        max_length=ModelConstants.FIELD_MAX_LENGTH512,
        null=True,
        blank=True
    )
    
    c_group = models.CharField(
        verbose_name="Описание группы переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
        null=True,
        blank=True
    )
    
    n_priority = models.SmallIntegerField(
        verbose_name="Приоритет роли переменной",
        null=True,
        blank=True
    )
      
    class Meta:
        """Конструктор."""

        verbose_name = "Роль переменной"
        verbose_name_plural = "Роли переменных"

    def __str__(self):
        return self.c_role_desc


class cnfEquipmentLinkedVariable(models.Model):
    """Модель для ссылок на переменные и роли."""

    n_index = models.IntegerField(
        verbose_name="Индекс",
        null=True,
    )
    n_equipment = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="ID оборудования из cnfEquipment",
        related_name="linked_variable",
    )
    n_role = models.ForeignKey(
        cnfEquipmentVariableRole,
        on_delete=models.CASCADE,
        verbose_name="Роль переменной",
        null=True,
        related_name="linked_variable",
    )
    n_timer = models.FloatField(verbose_name="Таймер", default=0)

    n_variable = models.ForeignKey(
        cnfVariable,
        on_delete=models.CASCADE,
        verbose_name="Ссылка на переменную",
        null=True,
        related_name="linked_variable",
    )
    b_masked = models.BooleanField(
        verbose_name="Замаскирован",
        default=False,
        # Если True - то замаскирован
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Ссылка на переменную"
        verbose_name_plural = "Ссылки на переменные"


class cnfEquipmentRole(models.Model):
    """Справочник роли оборудования."""

    n_role_index = models.IntegerField(
        verbose_name="Индекс роли оборудования", unique=True
    )
    c_role_name = models.CharField(
        verbose_name="Имя флага роли оборудования",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
        blank=True,
        null=True,
    )
    c_role_desc = models.CharField(
        verbose_name="Описание роли оборудования",
        max_length=ModelConstants.FIELD_MAX_LENGTH512,
    )
    c_role_oper_desc = models.CharField(
        verbose_name="Описание роли оборуования для оператора",
        max_length=ModelConstants.FIELD_MAX_LENGTH512,
        null=True,
        blank=True
    )
    c_group = models.CharField(
        verbose_name="Описание группы оборудования",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
        blank=True,
        null=True,
    )
    
    n_priority = models.SmallIntegerField(
        verbose_name="Приоритет роли оборудования",
        blank=True,
        null=True,
    )
    
    class Meta:
        """Конструктор."""

        verbose_name = "Роль оборудования"
        verbose_name_plural = "Роли оборудования"

    def __str__(self):
        return self.c_role_desc


class cnfEquipmentLinkedEquipment(models.Model):
    """Модель для ссылок на оборудование и роли."""

    n_index = models.IntegerField(
        verbose_name="Индекс",
        null=True,
    )
    n_equipment = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="ID оборудования из cnfEquipment",
        related_name="linked_equipment",
    )
    n_role = models.ForeignKey(
        cnfEquipmentRole,
        on_delete=models.CASCADE,
        verbose_name="Роль оборудования",
        null=True,
        related_name="linked_equipment",
    )
    n_timer = models.FloatField(verbose_name="Таймер", default=0)

    n_equipment_link = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="Ссылка на оборудование",
        null=True,
        related_name="linked_equipment_link",
    )
    b_masked = models.BooleanField(
        verbose_name="Замаскирован",
        default=False,
        # Если True - то замаскирован
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Ссылка на оборудование"
        verbose_name_plural = "Ссылки на оборудование"


class cnfEquipmentPIDVariableRole(models.Model):
    """Справочник роли переменных ПИД-регуляторов."""

    n_role_index = models.IntegerField(
        verbose_name="Индекс роли переменной ПИД", unique=True
    )
    c_role_name = models.CharField(
        verbose_name="Имя флага роли переменной ПИД",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
        blank=True,
        null=True,
    )

    c_role_desc = models.CharField(
        verbose_name="Описание роли переменной ПИД",
        max_length=ModelConstants.FIELD_MAX_LENGTH512,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Роль переменной ПИД"
        verbose_name_plural = "Роли переменных ПИД"

    def __str__(self):
        return self.c_role_desc


class cnfEquipmentLinkedPIDVariable(models.Model):
    """Модель для ссылок на переменные ПИД и роли."""

    n_index = models.IntegerField(
        verbose_name="Индекс",
        null=True,
    )
    n_equipment = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="ID оборудования из cnfEquipment",
        related_name="linked_pid_variable",
    )
    n_role = models.ForeignKey(
        cnfEquipmentPIDVariableRole,
        on_delete=models.CASCADE,
        verbose_name="Роль переменной ПИД",
        null=True,
        related_name="linked_pid_variable",
    )
    n_timer = models.FloatField(verbose_name="Таймер", default=0)

    n_variable_link = models.ForeignKey(
        cnfVariable,
        on_delete=models.CASCADE,
        verbose_name="Ссылка на переменную",
        null=True,
        related_name="linked_pid_variable_link",
    )
    b_masked = models.BooleanField(
        verbose_name="Замаскирован",
        default=False,
        # Если True - то замаскирован
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Ссылка на переменную ПИД"
        verbose_name_plural = "Ссылки на переменные ПИД"


class cnfEquipmentLinkedWord(models.Model):
    """
    Модель для ссылок на переменные слов состояния,
    управления, и т.д. с разбивкой по битам.
    """

    n_equipment = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="ID оборудования из cnfEquipment",
        related_name="linked_word",
    )
    n_role = models.ForeignKey(
        cnfEquipmentVariableRole,
        on_delete=models.CASCADE,
        verbose_name="Роль переменной",
        null=True,
        related_name="linked_word",
    )
    n_bit = models.SmallIntegerField(
        verbose_name="Номер бита",
    )

    n_variable = models.ForeignKey(
        cnfVariable,
        on_delete=models.CASCADE,
        verbose_name="Ссылка на переменную",
        null=True,
        related_name="linked_word",
    )

    n_word_type = models.SmallIntegerField(
        verbose_name="Тип слова",
        # 1 - Слово состояния
        # 2 - Слово управления
        # 3 - Слово ошибок
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Ссылка на слово"
        verbose_name_plural = "Ссылки на слова"


class cnfSequenceRole(models.Model):
    """Справочник роли последовательностей."""

    n_role_index = models.IntegerField(
        verbose_name="Индекс роли переменной", unique=True
    )
    b_role_equipment = models.BooleanField(
        verbose_name="Роль для оборудования",
        null=True,
        # Если True - то роль для оборудования
        # иначе - для переменных
    )
    c_role_name = models.CharField(
        verbose_name="Имя флага роли переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
        blank=True,
        null=True,
    )

    c_role_desc = models.CharField(
        verbose_name="Описание роли переменной",
        max_length=ModelConstants.FIELD_MAX_LENGTH512,
    )

    # n_role_type = models.SmallIntegerField(
    #     verbose_name="Тип привязки для роли - переменная/оборудование",
    #     null=True
    #     # Если 3 - то роль для оборудования
    #     # иначе 2 - для переменных
    # )
    class Meta:
        """Конструктор."""

        verbose_name = "Роль переменной"
        verbose_name_plural = "Роли переменных"

    def __str__(self):
        return self.c_role_desc


class cnfSequenceLinkedEquipment(models.Model):
    """Модель для ссылок на оборудование и роли для последовательнотей."""

    n_equipment = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="ID оборудования из cnfEquipment",
        related_name="seq_linked_equipment",
    )
    n_role = models.ForeignKey(
        cnfSequenceRole,
        on_delete=models.CASCADE,
        verbose_name="Роль оборудования",
        related_name="seq_linked_equipment",
    )
    n_timer = models.FloatField(verbose_name="Таймер", null=True)
    n_step = models.IntegerField(
        verbose_name="Таймер",
        # null=True
    )
    n_equipment_link = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="Ссылка на оборудование",
        null=True,
        related_name="seq_linked_equipment_link",
    )
    n_seq_type = models.SmallIntegerField(
        verbose_name="Тип последовательности: 1 -запуск, 2 - б.запуск, 3 - останов, 4 - авар.останов",
        # null=True
    )
    b_masked = models.BooleanField(
        verbose_name="Замаскирован",
        default=False,
        # Если True - то замаскирован
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Ссылка на оборудование (последовательности)"
        verbose_name_plural = "Ссылки на оборудование (последовательности)"


class cnfSequenceLinkedVariable(models.Model):
    """Модель для ссылок на переменные и роли для последовательнотей."""

    n_equipment = models.ForeignKey(
        cnfEquipment,
        on_delete=models.CASCADE,
        verbose_name="ID оборудования из cnfEquipment",
        related_name="seq_linked_variable",
    )
    n_role = models.ForeignKey(
        cnfSequenceRole,
        on_delete=models.CASCADE,
        verbose_name="Роль оборудования",
        related_name="seq_linked_variable",
    )
    n_timer = models.FloatField(verbose_name="Таймер", null=True)
    n_step = models.IntegerField(
        verbose_name="Таймер",
        # null=True
    )
    n_variable_link = models.ForeignKey(
        cnfVariable,
        on_delete=models.CASCADE,
        verbose_name="Ссылка на переменную",
        null=True,
        related_name="seq_linked_variable_link",
    )
    n_seq_type = models.SmallIntegerField(
        verbose_name="Тип последовательности: 1 -запуск, 2 - б.запуск, 3 - останов, 4 - авар.останов",
        # null=True
    )
    b_masked = models.BooleanField(
        verbose_name="Замаскирован",
        default=False,
        # Если True - то замаскирован
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Ссылка на переменную (последовательности)"
        verbose_name_plural = "Ссылки на переменные (последовательности)"
