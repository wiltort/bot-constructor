from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from bots.models import Bot, Scenario, Step
from .serializers import (
    BotSerializer,
    BotStepSerializer,
    BotControlSerializer,
    ScenarioSerializer,
)
from bots.services import BotService
from bots.tasks import start_bot, stop_bot, restart_bot
import logging

logger = logging.getLogger(__name__)

class BotViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления Telegram ботами.
    Предоставляет CRUD операции и дополнительные actions для управления состоянием ботов.
    """
    queryset = Bot.objects.all().order_by('-created_at')
    serializer_class = BotSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        Оптимизация queryset с prefetch_related для уменьшения количества запросов к БД
        """
        return Bot.objects.get_all_bots_with_steps()

    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Запуск конкретного бота
        POST /api/bots/{id}/start/
        """
        bot = self.get_object()
        
        # Проверка, что бот активен
        if not bot.is_active:
            return Response(
                {'error': 'Бот не активен. Сначала активируйте бота.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if bot.is_running:
            return Response(
                {'error': 'Бот уже запущен.'}
            )
        try:
            # Запускаем задачу Celery
            task_id = BotService.start_bot(bot.id)
            
            if task_id:
                logger.info(f"Задача запуска бота {bot.name} создана: {task_id}")
                return Response({
                    'status': 'success', 
                    'message': f'Задача запуска бота "{bot.name}" отправлена',
                    'task_id': task_id,
                    'bot_id': bot.id
                })
            else:
                return Response(
                    {'error': 'Ошибка при создании задачи запуска'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Ошибка запуска бота {bot.id}: {e}")
            return Response(
                {'error': f'Ошибка запуска бота: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """
        Остановка конкретного бота
        POST /api/bots/{id}/stop/
        """
        bot = self.get_object()
        
        # Проверка, что бот запущен
        if not bot.is_running:
            return Response(
                {'error': 'Бот уже остановлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Запускаем задачу Celery
            task_id = BotService.stop_bot(bot.id)
            
            if task_id:
                logger.info(f"Задача остановки бота {bot.name} создана: {task_id}")
                return Response({
                    'status': 'success', 
                    'message': f'Задача остановки бота "{bot.name}" отправлена',
                    'task_id': task_id,
                    'bot_id': bot.id
                })
            else:
                return Response(
                    {'error': 'Ошибка при создании задачи остановки'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Ошибка остановки бота {bot.id}: {e}")
            return Response(
                {'error': f'Ошибка остановки бота: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """
        Перезапуск конкретного бота
        POST /api/bots/{id}/restart/
        """
        bot = self.get_object()
        
        if not bot.is_active:
            return Response(
                {'error': 'Бот не активен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Запускаем задачу Celery
            task_id = BotService.restart_bot(bot.id)
            
            if task_id:
                logger.info(f"Задача перезапуска бота {bot.name} создана: {task_id}")
                return Response({
                    'status': 'success', 
                    'message': f'Задача перезапуска бота "{bot.name}" отправлена',
                    'task_id': task_id,
                    'bot_id': bot.id
                })
            else:
                return Response(
                    {'error': 'Ошибка при создании задачи перезапуска'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Ошибка перезапуска бота {bot.id}: {e}")
            return Response(
                {'error': f'Ошибка перезапуска бота: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Получение статуса бота
        GET /api/bots/{id}/status/
        """
        bot = self.get_object()
        
        status_data = {
            'id': bot.id,
            'name': bot.name,
            'is_active': bot.is_active,
            'is_running': bot.is_running,
            'last_started': bot.last_started,
            'last_stopped': bot.last_stopped,
            'created_at': bot.created_at,
            'updated_at': bot.updated_at,
            'steps_count': bot.current_scenario.steps.filter(is_active=True).count(),
        }
        
        return Response(status_data)
    
    @action(detail=True, methods=['get'])
    def task_status(self, request, pk=None):
        """
        Получение статуса последней задачи бота
        GET /api/bots/{id}/task_status/
        """
        bot = self.get_object()
        task_id = request.query_params.get('task_id')
        
        if not task_id:
            return Response(
                {'error': 'task_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            task_status = BotService.get_task_status(task_id)
            return Response(task_status)
        except Exception as e:
            logger.error(f"Ошибка получения статуса задачи {task_id}: {e}")
            return Response(
                {'error': f'Ошибка получения статуса задачи: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def start_all(self, request):
        """
        Запуск всех активных ботов
        POST /api/bots/start_all/
        """
        try:
            result = BotService.start_all()
            
            return Response({
                'status': 'success',
                'message': 'Задача запуска всех ботов отправлена',
                'tasks': result
            })
            
        except Exception as e:
            logger.error(f"Ошибка запуска всех ботов: {e}")
            return Response(
                {'error': f'Ошибка запуска всех ботов: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def stop_all(self, request):
        """
        Остановка всех ботов
        POST /api/bots/stop_all/
        """
        try:
            result = BotService.stop_all()
            
            return Response({
                'status': 'success',
                'message': 'Задача остановки всех ботов отправлена',
                'tasks': result
            })
            
        except Exception as e:
            logger.error(f"Ошибка остановки всех ботов: {e}")
            return Response(
                {'error': f'Ошибка остановки всех ботов: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Статистика по ботам
        GET /api/bots/summary/
        """
        total_bots = Bot.objects.count()
        active_bots = Bot.objects.get_active_bots().count()
        running_bots = Bot.objects.get_running_bots().count()
        total_handlers = Step.objects.count()
        active_handlers = Step.objects.filter(is_active=True).count()
        
        summary_data = {
            'total_bots': total_bots,
            'active_bots': active_bots,
            'running_bots': running_bots,
            'stopped_bots': active_bots - running_bots,
            'inactive_bots': total_bots - active_bots,
            'total_handlers': total_handlers,
            'active_handlers': active_handlers,
            'inactive_handlers': total_handlers - active_handlers
        }
        
        return Response(summary_data)


class ScenarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления сценариями
    """
    queryset = Scenario.objects.all()
    serializer_class = ScenarioSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Scenario.objects.get_scenarios_with_bots_and_steps()
        return queryset


class BotStepViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления обработчиками ботов.
    """
    serializer_class = BotStepSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        Фильтрация обработчиков по bot_id если передан параметр
        """
        scenario_id = self.kwargs.get('scenario_id')
        scenario = get_object_or_404(Scenario, id=scenario_id)
        return Step.objects.filter(scenario=scenario).order_by('priority')

    def get_scenario(self):
        """Получение сценария из URL параметров"""
        scenario_id = self.kwargs.get('scenario_id')
        return get_object_or_404(Scenario, id=scenario_id)
    
    def perform_create(self, serializer):
        """
        Создание шага с привязкой к сценарию из URL
        """
        scenario = self.get_scenario()
        instance = serializer.save(scenario=scenario)

        is_active = serializer.validated_data.get('is_active', False)
        bots = instance.scenario.bots.all()

        if bots and is_active:
            for bot in bots:
                self._maybe_restart_bot(bot)

    def perform_update(self, serializer):
        """
        Обновление шага с проверкой принадлежности к сценарию
        """
        instance = self.get_object()
        scenario = self.get_scenario()
                
        if instance.scenario != scenario:
            return Response(
                {'error': 'Step does not belong to this scenario'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance = serializer.save()
        bots = instance.scenario.bots.all()
        # Если изменилась активность обработчика, перезапускаем бота
        
        if bots:
            for bot in bots:
                self._maybe_restart_bot(bot)
    
    def perform_destroy(self, instance):
        """
        Удаление шага с проверкой принадлежности
        """
        scenario = self.get_scenario()
        
        if instance.scenario != scenario:
            return Response(
                {'error': 'Step does not belong to this scenario'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        bots = scenario.bots.all()
        super().perform_destroy(instance)
        
        if bots:
            for bot in bots:
                self._maybe_restart_bot(bot)
    
    def _maybe_restart_bot(self, bot):
        """
        Перезапуск бота если он запущен и активен
        """
        if bot.is_active and bot.is_running:
            try:
                # Используем задержку чтобы избежать частых перезапусков
                import time
                time.sleep(1)
                BotService.restart_bot(bot_id=bot.id)
                logger.info(f"Запланирован перезапуск бота {bot.name} после изменения обработчиков")
            except Exception as e:
                logger.error(f"Ошибка планирования перезапуска бота {bot.id}: {e}")


class BotControlViewSet(viewsets.ViewSet):
    """
    ViewSet для массового управления ботами
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def bulk_start(self, request):
        """
        Массовый запуск ботов
        POST /api/control/bulk_start/
        """
        serializer = BotControlSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        bot_ids = serializer.validated_data['bot_ids']
        results = []
        
        for bot_id in bot_ids:
            try:
                bot = TelegramBot.objects.get(id=bot_id)
                
                if not bot.is_active:
                    results.append({'bot_id': bot_id, 'status': 'skipped', 'reason': 'not_active'})
                    continue
                
                if bot.is_running:
                    results.append({'bot_id': bot_id, 'status': 'skipped', 'reason': 'already_running'})
                    continue
                
                task_id = BotService.start_bot(bot_id)
                results.append({'bot_id': bot_id, 'status': 'started', 'task_id': task_id})
                
            except TelegramBot.DoesNotExist:
                results.append({'bot_id': bot_id, 'status': 'error', 'reason': 'not_found'})
            except Exception as e:
                results.append({'bot_id': bot_id, 'status': 'error', 'reason': str(e)})
        
        return Response({'results': results})
    
    @action(detail=False, methods=['post'])
    def bulk_stop(self, request):
        """
        Массовая остановка ботов
        POST /api/control/bulk_stop/
        """
        serializer = BotControlSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        bot_ids = serializer.validated_data['bot_ids']
        results = []
        
        for bot_id in bot_ids:
            try:
                bot = TelegramBot.objects.get(id=bot_id)
                
                if not bot.is_running:
                    results.append({'bot_id': bot_id, 'status': 'skipped', 'reason': 'not_running'})
                    continue
                
                task_id = BotService.stop_bot(bot_id)
                results.append({'bot_id': bot_id, 'status': 'stopped', 'task_id': task_id})
                
            except TelegramBot.DoesNotExist:
                results.append({'bot_id': bot_id, 'status': 'error', 'reason': 'not_found'})
            except Exception as e:
                results.append({'bot_id': bot_id, 'status': 'error', 'reason': str(e)})
        
        return Response({'results': results})

class HealthCheckViewSet(viewsets.ViewSet):
    """
    ViewSet для проверки здоровья системы
    """
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['get'])
    def health(self, request):
        """
        Проверка здоровья приложения
        GET /api/health/
        """
        from django.db import connection
        from django.core.cache import cache
        import redis
        
        checks = {
            'database': False,
            'cache': False,
            'celery': False,
            'overall': False
        }
        
        # Проверка базы данных
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks['database'] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Проверка кеша (Redis)
        try:
            cache.set('health_check', 'ok', 10)
            checks['cache'] = cache.get('health_check') == 'ok'
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
        
        # Проверка Celery (опционально)
        try:
            # Простая проверка подключения к Redis
            import redis
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            r.ping()
            checks['celery'] = True
        except Exception as e:
            logger.error(f"Celery health check failed: {e}")
        
        # Общий статус
        checks['overall'] = all([checks['database'], checks['cache']])
        
        status_code = status.HTTP_200_OK if checks['overall'] else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response({
            'status': 'healthy' if checks['overall'] else 'unhealthy',
            'checks': checks,
            'timestamp': timezone.now().isoformat()
        }, status=status_code)
