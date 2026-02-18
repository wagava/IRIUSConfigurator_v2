from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from equipments.models import cnfEquipment,cnfEquipmentValue
from general.models import cnfAttribute
from .serializers import EquipmentPIDSerializer, EquipmentPostSerializer #, EquipmentPostSerializer
from collections import defaultdict
from .utils import save_equipment_attributes_to_db, save_equipment_to_plc
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import permission_classes
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@permission_classes([IsAuthenticated])
class EquipmentDetailView(APIView):
    """Представление для получения данных об оборудовании."""

    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
    operation_description="Получение данных по коэффициентам регуляторов",
    manual_parameters=[
        openapi.Parameter(
            'index',
            openapi.IN_QUERY,
            description="Номер или имя оборудования. Обязательный параметр, если 'all' не установлено в 'true'.",
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'plc',
            openapi.IN_QUERY,
            description="Номер PLC. Обязательный параметр.",
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'all',
            openapi.IN_QUERY,
            description="Флаг для получения данных по всему оборудованию. Принимает значения 'true' или 'false'. По умолчанию 'false'.",
            type=openapi.TYPE_BOOLEAN,
            default=False
        ),
    ],
    responses={
        200: "Success",
        400: "Bad request",
        404: "Not Found"
    }
)
    def get(self, request, *args, **kwargs):
        index = request.query_params.get("index")  # Номер или имя оборудования
        plc_num = request.query_params.get("plc")
        all_equipment = request.query_params.get("all", "false").lower() == "true"
        if not plc_num:
            return Response({"error": "Необходимо указать 'plc'."}, status=status.HTTP_400_BAD_REQUEST)
        if not index:
            return Response({"error": "Необходимо указать 'index'."}, status=status.HTTP_400_BAD_REQUEST)
        if not index and not all_equipment:
            return Response(
                {"error": "Необходимо указать 'index' или установить 'all=True'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Поиск оборудования по номеру или имени
        try:
            if all_equipment:
                data = cnfEquipmentValue.objects.select_related(
                'n_equipment', 'n_attribute'
            ).filter(
                    Q(n_equipment__n_controller=plc_num) &
                    Q(n_attribute__c_name_attribute__in=["PID.Kp", "PID.Ti", "PID.Td"])
            ).values(
                'n_equipment__id',
                'n_equipment__n_equipment_index',
                'n_equipment__c_name_equipment',
                'n_attribute__c_name_attribute',
                'f_value'
            )
            else:
                data = cnfEquipmentValue.objects.select_related(
                'n_equipment', 'n_attribute'
                ).filter(
                    Q(n_equipment__n_controller=plc_num) &
                    Q(n_equipment__n_equipment_index=index) &
                    Q(n_attribute__c_name_attribute__in=["PID.Kp", "PID.Ti", "PID.Td"])                
                ).values(
                    'n_equipment__id',
                    'n_equipment__n_equipment_index',
                    'n_equipment__c_name_equipment',
                    'n_attribute__c_name_attribute',
                    'f_value'
                )
        except cnfEquipment.DoesNotExist:
            return Response({"error": "Оборудование не найдено."}, status=status.HTTP_404_NOT_FOUND)

        
        grouped_data = defaultdict(lambda: {
                                "id": None,
                                "index": None,
                                "name": None,
                                "attributes": []
        })
        for item in data:
            equipment_id = item["n_equipment__id"]
            grouped_data[equipment_id]["id"] = item["n_equipment__id"]
            grouped_data[equipment_id]["index"] = item["n_equipment__n_equipment_index"]
            grouped_data[equipment_id]["name"] = item["n_equipment__c_name_equipment"]
            grouped_data[equipment_id]["attributes"].append({
                "attribute_name": item["n_attribute__c_name_attribute"],
                "value": item["f_value"]
            })

        result = grouped_data.values()
        serializer = EquipmentPIDSerializer(result, many=True)

        
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Сохранение данных оборудования в базу данных.",
        request_body=EquipmentPostSerializer,
        responses={
            201: "Данные успешно сохранены.",
            400: "Ошибка валидации входных данных.",
            500: "Внутренняя ошибка сервера."
        }
    )
    def patch(self, request, *args, **kwargs):
        # Валидация входных данных
        serializer = EquipmentPostSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Получение данных
        equipment_data = serializer.validated_data["equipment_data"]

        try:
            # Сохранение данных в базу
            save_equipment_attributes_to_db(equipment_data)
            save_equipment_to_plc(equipment_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Данные успешно сохранены."}, status=status.HTTP_201_CREATED)
    

# class LogoutView(APIView):
#     """
#     Представление для выхода из системы.
#     Добавляет refresh-токен в черный список.
#     """
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         try:
#             # Получаем refresh-токен из тела запроса
#             refresh_token = request.data.get("refresh_token")

#             if not refresh_token:
#                 return Response(
#                     {"error": "Refresh token is required."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#             # Создаем объект RefreshToken и добавляем его в черный список
#             token = RefreshToken(refresh_token)
#             token.blacklist()

#             return Response(
#                 {"message": "Successfully logged out."},
#                 status=status.HTTP_205_RESET_CONTENT
#             )
#         except Exception as e:
#             return Response(
#                 {"error": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )