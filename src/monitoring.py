import time
import logging
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger("botitibot.monitoring")

@dataclass
class ResourceMetrics:
    """System resource usage metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    timestamp: datetime

@dataclass
class PerformanceMetrics:
    """Application performance metrics"""
    task_count: int
    error_count: int
    avg_task_duration: float
    task_success_rate: float
    timestamp: datetime

class MonitoringSystem:
    def __init__(self, alert_thresholds: Optional[Dict[str, float]] = None):
        """Initialize the monitoring system
        
        Args:
            alert_thresholds: Dictionary of metric names to their alert thresholds
        """
        self.alert_thresholds = alert_thresholds or {
            'cpu_percent': 80.0,
            'memory_percent': 80.0,
            'disk_usage_percent': 80.0,
            'error_rate': 0.1,  # 10% error rate
            'task_duration': 300.0  # 5 minutes
        }
        
        # Initialize metrics storage
        self.resource_metrics: List[ResourceMetrics] = []
        self.performance_metrics: List[PerformanceMetrics] = []
        self.error_counts = defaultdict(int)
        self.task_durations: Dict[str, List[float]] = defaultdict(list)
        
        # Track alert states to prevent alert spam
        self.active_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=30)
        
    def collect_resource_metrics(self) -> ResourceMetrics:
        """Collect current system resource metrics"""
        try:
            metrics = ResourceMetrics(
                cpu_percent=psutil.cpu_percent(),
                memory_percent=psutil.virtual_memory().percent,
                disk_usage_percent=psutil.disk_usage('/').percent,
                timestamp=datetime.now()
            )
            
            self.resource_metrics.append(metrics)
            self._check_resource_alerts(metrics)
            
            # Keep only last 24 hours of metrics
            cutoff = datetime.now() - timedelta(hours=24)
            self.resource_metrics = [
                m for m in self.resource_metrics if m.timestamp > cutoff
            ]
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect resource metrics", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'monitoring.resources'
                }
            })
            return None
            
    def collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect current application performance metrics"""
        try:
            # Calculate metrics
            total_tasks = sum(len(durations) for durations in self.task_durations.values())
            total_errors = sum(self.error_counts.values())
            
            avg_duration = 0.0
            if total_tasks > 0:
                all_durations = [
                    d for durations in self.task_durations.values()
                    for d in durations
                ]
                avg_duration = sum(all_durations) / len(all_durations)
                
            success_rate = 1.0
            if total_tasks > 0:
                success_rate = 1.0 - (total_errors / total_tasks)
                
            metrics = PerformanceMetrics(
                task_count=total_tasks,
                error_count=total_errors,
                avg_task_duration=avg_duration,
                task_success_rate=success_rate,
                timestamp=datetime.now()
            )
            
            self.performance_metrics.append(metrics)
            self._check_performance_alerts(metrics)
            
            # Keep only last 24 hours of metrics
            cutoff = datetime.now() - timedelta(hours=24)
            self.performance_metrics = [
                m for m in self.performance_metrics if m.timestamp > cutoff
            ]
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect performance metrics", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'monitoring.performance'
                }
            })
            return None
            
    def record_task_completion(self, task_type: str, duration: float, success: bool) -> None:
        """Record task completion metrics
        
        Args:
            task_type: Type of task completed
            duration: Time taken to complete task (seconds)
            success: Whether the task completed successfully
        """
        try:
            # Record duration
            self.task_durations[task_type].append(duration)
            
            # Keep only last 1000 durations per task type
            if len(self.task_durations[task_type]) > 1000:
                self.task_durations[task_type] = self.task_durations[task_type][-1000:]
                
            # Record error if task failed
            if not success:
                self.error_counts[task_type] += 1
                
            logger.info("Recorded task completion", extra={
                'context': {
                    'task_type': task_type,
                    'duration': duration,
                    'success': success,
                    'component': 'monitoring.tasks'
                }
            })
            
        except Exception as e:
            logger.error("Failed to record task completion", exc_info=True, extra={
                'context': {
                    'task_type': task_type,
                    'error': str(e),
                    'component': 'monitoring.tasks'
                }
            })
            
    def _check_resource_alerts(self, metrics: ResourceMetrics) -> None:
        """Check resource metrics against thresholds and generate alerts"""
        now = datetime.now()
        
        # Check CPU usage
        if metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            self._generate_alert(
                'high_cpu_usage',
                f"High CPU usage: {metrics.cpu_percent}%",
                now
            )
            
        # Check memory usage
        if metrics.memory_percent > self.alert_thresholds['memory_percent']:
            self._generate_alert(
                'high_memory_usage',
                f"High memory usage: {metrics.memory_percent}%",
                now
            )
            
        # Check disk usage
        if metrics.disk_usage_percent > self.alert_thresholds['disk_usage_percent']:
            self._generate_alert(
                'high_disk_usage',
                f"High disk usage: {metrics.disk_usage_percent}%",
                now
            )
            
    def _check_performance_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check performance metrics against thresholds and generate alerts"""
        now = datetime.now()
        
        # Check error rate
        if (1.0 - metrics.task_success_rate) > self.alert_thresholds['error_rate']:
            self._generate_alert(
                'high_error_rate',
                f"High error rate: {(1.0 - metrics.task_success_rate) * 100}%",
                now
            )
            
        # Check average task duration
        if metrics.avg_task_duration > self.alert_thresholds['task_duration']:
            self._generate_alert(
                'high_task_duration',
                f"High average task duration: {metrics.avg_task_duration:.2f}s",
                now
            )
            
    def _generate_alert(self, alert_type: str, message: str, timestamp: datetime) -> None:
        """Generate an alert if cooldown period has passed"""
        # Check if alert is in cooldown
        if alert_type in self.active_alerts:
            if timestamp - self.active_alerts[alert_type] < self.alert_cooldown:
                return
                
        # Update alert timestamp
        self.active_alerts[alert_type] = timestamp
        
        # Log alert
        logger.warning(f"ALERT: {message}", extra={
            'context': {
                'alert_type': alert_type,
                'message': message,
                'component': 'monitoring.alerts'
            }
        })
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics"""
        if not self.resource_metrics or not self.performance_metrics:
            return {}
            
        latest_resource = self.resource_metrics[-1]
        latest_performance = self.performance_metrics[-1]
        
        return {
            'resources': {
                'cpu_percent': latest_resource.cpu_percent,
                'memory_percent': latest_resource.memory_percent,
                'disk_usage_percent': latest_resource.disk_usage_percent
            },
            'performance': {
                'task_count': latest_performance.task_count,
                'error_count': latest_performance.error_count,
                'avg_task_duration': latest_performance.avg_task_duration,
                'task_success_rate': latest_performance.task_success_rate
            },
            'timestamp': datetime.now().isoformat()
        }
