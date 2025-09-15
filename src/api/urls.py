from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as token_views
from api import views

app_name = 'api'
router = DefaultRouter()

router.register(r'bots', views.BotViewSet, basename='bot')
router.register(r'scenarios', views.ScenarioViewSet, basename='scenario')


urlpatterns = [
    path('v1/', include(router.urls)),
    path('token-auth/', token_views.obtain_auth_token)
]
