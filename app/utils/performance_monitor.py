import time
import logging
from functools import wraps
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from contextlib import contextmanager
import threading
from collections import defaultdict, deque

from app.core.config import settings

class PerformanceMonitor:
    """
    Monitor de rendimiento para el agente optimizado
    """
    
    def __init__(self):
        self.logger = logging.getLogger("performance")
        self.metrics = defaultdict(lambda: {
            'total_calls': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'recent_times': deque(maxlen=100),  # Últimas 100 ejecuciones
            'errors': 0
        })
        self.lock = threading.Lock()
        
        # Configurar logging si está habilitado
        if settings.ENABLE_PERFORMANCE_LOGGING:
            self.logger.setLevel(logging.INFO)
            
            # Crear handler si no existe
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
    
    def log_execution_time(self, func_name: str = None) -> Callable:
        """Decorator para medir tiempo de ejecución"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not settings.LOG_TOOL_EXECUTION_TIME:
                    return func(*args, **kwargs)
                
                function_name = func_name or func.__name__
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Actualizar métricas
                    self._update_metrics(function_name, execution_time, success=True)
                    
                    # Log si está habilitado
                    if settings.ENABLE_PERFORMANCE_LOGGING:
                        self.logger.info(f"{function_name}: {execution_time:.3f}s")
                    
                    # Añadir metadata al resultado si es posible
                    if hasattr(result, '__dict__'):
                        result.execution_time = execution_time
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    # Actualizar métricas con error
                    self._update_metrics(function_name, execution_time, success=False)
                    
                    if settings.ENABLE_PERFORMANCE_LOGGING:
                        self.logger.error(f"{function_name} ERROR: {execution_time:.3f}s - {e}")
                    
                    raise
                    
            return wrapper
        return decorator
    
    def _update_metrics(self, function_name: str, execution_time: float, success: bool = True):
        """Actualizar métricas internas"""
        with self.lock:
            metrics = self.metrics[function_name]
            
            metrics['total_calls'] += 1
            metrics['total_time'] += execution_time
            metrics['avg_time'] = metrics['total_time'] / metrics['total_calls']
            metrics['min_time'] = min(metrics['min_time'], execution_time)
            metrics['max_time'] = max(metrics['max_time'], execution_time)
            metrics['recent_times'].append(execution_time)
            
            if not success:
                metrics['errors'] += 1
    
    @contextmanager
    def measure_block(self, block_name: str):
        """Context manager para medir bloques de código"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self._update_metrics(block_name, execution_time)
            
            if settings.ENABLE_PERFORMANCE_LOGGING:
                self.logger.info(f"Block '{block_name}': {execution_time:.3f}s")
    
    def get_metrics(self, function_name: str = None) -> Dict[str, Any]:
        """Obtener métricas de rendimiento"""
        with self.lock:
            if function_name:
                if function_name in self.metrics:
                    return dict(self.metrics[function_name])
                else:
                    return {}
            
            # Retornar todas las métricas
            return {
                name: dict(metrics) for name, metrics in self.metrics.items()
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtener resumen de rendimiento"""
        with self.lock:
            if not self.metrics:
                return {
                    "total_functions": 0,
                    "total_calls": 0,
                    "total_time": 0.0,
                    "functions": []
                }
            
            total_calls = sum(m['total_calls'] for m in self.metrics.values())
            total_time = sum(m['total_time'] for m in self.metrics.values())
            total_errors = sum(m['errors'] for m in self.metrics.values())
            
            # Resumen por función
            functions_summary = []
            for name, metrics in self.metrics.items():
                recent_avg = sum(metrics['recent_times']) / len(metrics['recent_times']) if metrics['recent_times'] else 0
                
                functions_summary.append({
                    "name": name,
                    "total_calls": metrics['total_calls'],
                    "avg_time": metrics['avg_time'],
                    "recent_avg_time": recent_avg,
                    "min_time": metrics['min_time'] if metrics['min_time'] != float('inf') else 0,
                    "max_time": metrics['max_time'],
                    "errors": metrics['errors'],
                    "error_rate": metrics['errors'] / metrics['total_calls'] if metrics['total_calls'] > 0 else 0
                })
            
            # Ordenar por tiempo promedio
            functions_summary.sort(key=lambda x: x['avg_time'], reverse=True)
            
            return {
                "total_functions": len(self.metrics),
                "total_calls": total_calls,
                "total_time": total_time,
                "total_errors": total_errors,
                "overall_error_rate": total_errors / total_calls if total_calls > 0 else 0,
                "functions": functions_summary,
                "timestamp": datetime.now().isoformat()
            }
    
    def reset_metrics(self, function_name: str = None):
        """Resetear métricas"""
        with self.lock:
            if function_name:
                if function_name in self.metrics:
                    del self.metrics[function_name]
            else:
                self.metrics.clear()
    
    def log_agent_performance(self, agent_type: str, query_time: float, tool_count: int, success: bool = True):
        """Log específico para rendimiento del agente"""
        metric_name = f"agent_{agent_type}"
        
        with self.lock:
            metrics = self.metrics[metric_name]
            metrics['total_calls'] += 1
            metrics['total_time'] += query_time
            metrics['avg_time'] = metrics['total_time'] / metrics['total_calls']
            metrics['min_time'] = min(metrics['min_time'], query_time)
            metrics['max_time'] = max(metrics['max_time'], query_time)
            metrics['recent_times'].append(query_time)
            
            if not success:
                metrics['errors'] += 1
            
            # Métricas adicionales para agentes
            if 'tool_usage' not in metrics:
                metrics['tool_usage'] = []
            metrics['tool_usage'].append(tool_count)
        
        if settings.ENABLE_PERFORMANCE_LOGGING:
            self.logger.info(f"Agent {agent_type}: {query_time:.3f}s, {tool_count} tools, {'success' if success else 'failed'}")

# Instancia global del monitor
monitor = PerformanceMonitor()

# Decorador de conveniencia
def measure_performance(func_name: str = None):
    """Decorador de conveniencia para medir rendimiento"""
    return monitor.log_execution_time(func_name)

# Context manager de conveniencia
def measure_block(block_name: str):
    """Context manager de conveniencia para medir bloques"""
    return monitor.measure_block(block_name) 