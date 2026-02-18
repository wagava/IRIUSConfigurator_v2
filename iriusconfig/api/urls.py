from django.urls import include, path
from django.views.generic import TemplateView
from .views import EquipmentDetailView #, LogoutView #, EquipmentPostView
from rest_framework import permissions

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.authentication import TokenAuthentication

schema_view = get_schema_view(
    openapi.Info(
        title="IRIUS REST API",
        default_version='v1',
        description="REST API для работы с IRIUS",
        # terms_of_service="free",   # Условия использования
        contact=openapi.Contact(email="agava@intma.ru"),  # Контактная информация
        # license=openapi.License(name="BSD License"),  # Лицензия
    ),
    public=True,
    authentication_classes=[TokenAuthentication],
    permission_classes=(permissions.AllowAny,),  # Разрешить доступ всем
)

urlpatterns = [
        
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'), # ReDoc
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'), # Swagger UI
    # JWT токены
    path('auth/token/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path("equipment/pid", EquipmentDetailView.as_view(), name="equipment-detail"),
]
