from django.http import JsonResponse
from django.db import connection
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """Комплексная проверка всех зависимостей"""
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "overall": "healthy"
    }
    
    status_code = 200 if all(v == "healthy" for v in checks.values() if v != "overall") else 503
    
    return JsonResponse(checks, status=status_code)

def check_database():
    """Проверка подключения к БД"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return "unhealthy"

def check_redis():
    """Проверка подключения к Redis"""
    try:
        # Используйте ваш конфиг Redis из settings
        from django.conf import settings
        import redis
        
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        return "healthy"
    except RedisConnectionError as e:
        logger.error(f"Redis health check failed: {e}")
        return "unhealthy"
    except Exception as e:
        logger.error(f"Redis health check error: {e}")
        return "unhealthy"