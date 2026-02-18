from rest_framework import serializers
from equipments.models import cnfEquipment, cnfEquipmentValue
from general.models import cnfAttribute

# class AttributeValueSerializer(serializers.ModelSerializer):
#     """Сериализатор для значений атрибутов."""
#     attribute_name = serializers.CharField(source="attribute.name", read_only=True)

#     class Meta:
#         model = cnfAttribute
#         fields = ["c_name_attribute"]


# class EquipmentDetailSerializer(serializers.ModelSerializer):
#     """Сериализатор для детальной информации об оборудовании."""
#     # attributes = AttributeValueSerializer(many=True, source="attributes.all", read_only=True)

#     class Meta:
#         model = cnfEquipment
#         fields = ["id", "n_equipment_index", "c_name_equipment"]

# class EquipmentPIDSerializer(serializers.Serializer):
#     """Сериализатор для данных, полученных через values()."""
#     n_equipment__id = serializers.IntegerField()
#     n_equipment__n_equipment_index = serializers.CharField()
#     n_equipment__c_name_equipment = serializers.CharField()
#     n_attribute__c_name_attribute = serializers.CharField()
#     f_value = serializers.FloatField()


class AttributeSerializer(serializers.Serializer):
    attribute_name = serializers.CharField()
    value = serializers.FloatField()

class EquipmentPIDSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    index = serializers.CharField()
    name = serializers.CharField()
    attributes = AttributeSerializer(many=True)




class AttributeValueSerializer(serializers.Serializer):
    """Сериализатор для значений атрибутов."""
    PID_Kp = serializers.FloatField(required=True)
    PID_Ti = serializers.FloatField(required=True)
    PID_Td = serializers.FloatField(required=True)

class EquipmentDataSerializer(serializers.Serializer):
    """Сериализатор для данных оборудования."""
    plc = serializers.IntegerField(required=True)
    equipment_index = serializers.IntegerField(required=True)
    attributes = AttributeValueSerializer()

class EquipmentPostSerializer(serializers.Serializer):
    """Сериализатор для всего запроса."""
    equipment_data = serializers.ListField(child=EquipmentDataSerializer(), required=True)




# class EquipmentPIDSerializer(serializers.ModelSerializer):
#     """Сериализатор для детальной информации о ПИД-регуляторе."""
#     attributes = AttributeValueSerializer(many=True, read_only=True) #source="attributes.all", read_only=True)
#     equipments = EquipmentDetailSerializer(many=True, read_only=True) #source="attributes.all", read_only=True)

#     class Meta:
#         model = cnfEquipmentValue
#         fields = ["id", "f_value", "attributes", "equipments"]


# class EquipmentPostSerializer(serializers.Serializer):
#     """Сериализатор для записи данных через POST."""
#     equipment = serializers.CharField()  # Номер или имя оборудования
#     attributes = serializers.DictField(child=serializers.CharField())  # Словарь: {"атрибут": "значение"}

#     def validate_equipment(self, value):
#         """Проверка существования оборудования."""
#         if not Equipment.objects.filter(models.Q(number=value) | models.Q(name=value)).exists():
#             raise serializers.ValidationError("Оборудование не найдено.")
#         return value

#     def validate_attributes(self, value):
#         """Проверка существования атрибутов."""
#         attribute_names = list(value.keys())
#         existing_attributes = Attribute.objects.filter(name__in=attribute_names).values_list("name", flat=True)
#         missing_attributes = set(attribute_names) - set(existing_attributes)
#         if missing_attributes:
#             raise serializers.ValidationError(f"Атрибуты не найдены: {', '.join(missing_attributes)}")
#         return value





# from djoser.serializers import UserSerializer
# # from rest_framework import serializers
# from django.contrib.auth import get_user_model

# User = get_user_model()

# class CustomUserSerializer(UserSerializer):
#     """Сериализатор для аутентификации пользователя."""

#     class Meta:
#         model = User
#         fields = (
#             'id',
#             'email',
#             'username',
#             'first_name',
#             'last_name',
#             'password',
#         )
#         # extra_kwargs = USER_EXTRA_KWARGS

#     def create(self, validated_data):
#         password = validated_data.pop('password', None)
#         instance = self.Meta.model(**validated_data)
#         instance.set_password(password)
#         instance.save()
#         return instance