from django.db import models


from iriusconfig.constants import ModelConstants

# User = get_user_model()


class cnfController(models.Model):
    """Модель данных по контроллерам."""

    c_name_controller = models.CharField(
        verbose_name="Controller name", max_length=ModelConstants.FIELD_MAX_LENGTH64
    )
    c_ip_controller = models.CharField(
        verbose_name="Controller IP-address",
        max_length=ModelConstants.FIELD_MAX_LENGTH32,
        help_text="Set only ip, must haven't dns name",
    )
    c_desc_controller = models.CharField(
        verbose_name="Controller description",
        null=True,
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Controller"
        verbose_name_plural = "Controllers"

    def __str__(self):
        return self.c_name_controller


class cnfAttribute(models.Model):
    """Атрибуты всех сущностей."""

    n_attribute_type = models.PositiveSmallIntegerField(
        verbose_name="Тип атрибута",
    )
    n_parameter_id = models.PositiveIntegerField(
        verbose_name="Идентификатор параметра",
    )
    n_parameter_bit = models.PositiveSmallIntegerField(
        verbose_name="Бит в параметре",
    )
    c_name_attribute = models.CharField(
        verbose_name="Имя атрибута", max_length=ModelConstants.FIELD_MAX_LENGTH255
    )
    c_display_attribute = models.CharField(
        verbose_name="Пользовательское имя",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
    )
    c_desc_attribute = models.CharField(
        verbose_name="Описание",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
        null=True,
    )
    n_attr_min_id = models.SmallIntegerField(
        verbose_name="Минимальное значение id атрибута", null=True, blank=True
    )
    n_attr_max_id = models.SmallIntegerField(
        verbose_name="Максимальное значение id атрибута", null=True, blank=True
    )
    n_attr_min_value = models.FloatField(
        verbose_name="Минимальное значение атрибута", null=True, blank=True
    )
    n_attr_max_value = models.FloatField(
        verbose_name="Максимальное значение атрибута", null=True, blank=True
    )
    c_attr_display_group = models.CharField(
        verbose_name="Отображаемая группа для атрибута",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
        null=True,
        blank=True,
    )
    n_attr_display_order = models.SmallIntegerField(
        verbose_name="Порядок отображения для атрибута", null=True, blank=True
    )
    n_attribute_sub_type = models.PositiveSmallIntegerField(
        verbose_name="Подтип атрибута", null=True, blank=True
    )
    n_parent = models.IntegerField(
        verbose_name="Идентификатор родителя",
        null=True,
        # blank=True
    )

    n_global_object_type = models.PositiveSmallIntegerField(
        verbose_name="""Тип глобального объекта:
        Модули, Переменные, Оборудование...""",
        # Модули: 1
        # Переменные: 2
        # Оборудование: 3
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Атрибут"
        verbose_name_plural = "Атрибуты"

    def __str__(self):
        return self.c_name_attribute


class cnfCommands(models.Model):
    """Перечень команд с описанием."""

    n_command_index = models.PositiveSmallIntegerField(
        verbose_name="Индекс команды",
    )
    c_name = models.CharField(
        verbose_name="Имя константы",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
    )
    c_desc = models.CharField(
        verbose_name="Описание команды/запроса/ответа",
        max_length=ModelConstants.FIELD_MAX_LENGTH512,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Команда"
        verbose_name_plural = "Команды"

    def __str__(self):
        return self.с_desc


class cnfVariableQualityCodes(models.Model):
    """Перечень кодов качества с описанием."""

    n_code = models.PositiveSmallIntegerField(
        verbose_name="Код качества",
    )
    c_name = models.CharField(
        verbose_name="Имя кода",
        max_length=ModelConstants.FIELD_MAX_LENGTH64,
    )
    c_desc = models.CharField(
        verbose_name="Описание кода",
        max_length=ModelConstants.FIELD_MAX_LENGTH255,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Код качества"
        verbose_name_plural = "Коды качества"

    def __str__(self):
        return self.с_desc


class cnfJournalMessages(models.Model):
    """Перечень сообщений жкрнала ПЛК с описанием."""

    n_index = models.PositiveSmallIntegerField(
        verbose_name="Индекс сообщения",
    )
    c_obj_index_name = models.CharField(
        verbose_name="Имя объекта для индекса",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
    )
    c_desc = models.CharField(
        verbose_name="Описание команды/запроса/ответа",
        max_length=ModelConstants.FIELD_MAX_LENGTH512,
    )
    c_mes_type = models.CharField(
        verbose_name="Тип сообщения",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"

    def __str__(self):
        return self.с_desc


class cnfVariableAttributes(models.Model):
    """Перечень атрибутов переменных для формирования карты адресов."""

    c_attr_name = models.CharField(
        verbose_name="Имя атрибута",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
    )
    c_data_type = models.CharField(
        verbose_name="Тип данных атрибута",
        max_length=ModelConstants.FIELD_MAX_LENGTH16,
    )
    c_reg_type = models.CharField(
        verbose_name="Наименование типа регистра",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
    )
    n_offset = models.PositiveSmallIntegerField(
        verbose_name="Смещение относительно базового адреса",
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Атрибут переменной"
        verbose_name_plural = "Атрибуты переменной"

    def __str__(self):
        return self.c_attr_name


class cnfEquipmentAttributes(models.Model):
    """Перечень атрибутов оборудования для формирования карты адресов."""

    c_attr_name = models.CharField(
        verbose_name="Имя атрибута",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
    )
    c_data_type = models.CharField(
        verbose_name="Тип данных атрибута",
        max_length=ModelConstants.FIELD_MAX_LENGTH16,
    )
    c_reg_type = models.CharField(
        verbose_name="Наименование типа регистра",
        max_length=ModelConstants.FIELD_MAX_LENGTH128,
    )
    n_offset = models.PositiveSmallIntegerField(
        verbose_name="Смещение относительно базового адреса",
    )

    class Meta:
        """Конструктор."""

        verbose_name = "Атрибут оборудования"
        verbose_name_plural = "Атрибуты оборудования"

    def __str__(self):
        return self.c_attr_name
