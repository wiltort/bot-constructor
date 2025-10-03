from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as token_views
from api import views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


app_name = 'api'

schema_view = get_schema_view(
    openapi.Info(
        title="Bot Constructor API",
        default_version='v1',
        description="API description",
        terms_of_service="https://www.google.com/policies/terms/",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    url='http://89.104.71.118',
)

router = DefaultRouter()

router.register(r'bots', views.BotViewSet, basename='bot')
router.register(r'scenarios', views.ScenarioViewSet, basename='scenario')


urlpatterns = [
    path('v1/', include(router.urls)),
    path('token-auth/', token_views.obtain_auth_token),
    path('v1/scenarios/<int:scenario_id>/steps/', views.BotStepViewSet.as_view({
        'post': 'create',
        'get': 'list'
    }), name='step-list'),
    path('v1/scenarios/<int:scenario_id>/steps/<int:pk>/', views.BotStepViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='step-detail'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

