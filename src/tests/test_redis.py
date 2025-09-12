# tests/test_redis.py
import redis
from django.conf import settings

def test_redis_connection():
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False