#!/usr/bin/env python3
"""
Módulo de Detección de Anomalías
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class AnomalyDetector:
    """
    Detector de anomalías para QZero
    """
    
    def __init__(self, threshold: float = 0.7):
        """
        Inicializar detector
        
        Args:
            threshold: Umbral de detección (0-1)
        """
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)
        
        # Histórico de datos
        self.history: List[Dict] = []
        self.anomaly_patterns: Dict = {}
    
    def detect(self) -> Dict:
        """
        Detectar anomalías
        
        Returns:
            Diccionario con resultado del análisis
        """
        try:
            if not self.history:
                return {
                    'anomaly_detected': False,
                    'anomaly_type': 'NO_DATA',
                    'severity': 'INFO',
                    'details': 'Sin datos suficientes'
                }
            
            # Calcular métricas
            metrics = self._calculate_metrics()
            
            # Detectar anomalías
            anomaly_detected = self._check_thresholds(metrics)
            anomaly_type = self._classify_anomaly(metrics)
            severity = self._determine_severity(anomaly_type, metrics)
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'anomaly_detected': anomaly_detected,
                'anomaly_type': anomaly_type,
                'severity': severity,
                'metrics': metrics,
                'threshold': self.threshold
            }
            
            # Guardar resultado
            self._save_result(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error en detección: {e}")
            return {'error': str(e)}
    
    def _calculate_metrics(self) -> Dict:
        """
        Calcular métricas a partir del historico
        
        Returns:
            Diccionario de métricas
        """
        if not self.history:
            return {'data_points': 0}
        
        # Calcular promedios
        avg_anomaly_rate = sum(h.get('anomaly_rate', 0) for h in self.history) / len(self.history)
        avg_quality = sum(h.get('data_quality', 0) for h in self.history) / len(self.history)
        trend = self._calculate_trend()
        
        return {
            'data_points': len(self.history),
            'avg_anomaly_rate': round(avg_anomaly_rate, 3),
            'avg_quality': round(avg_quality, 3),
            'trend': trend,
            'latest_anomaly_rate': self.history[-1].get('anomaly_rate', 0),
            'latest_quality': self.history[-1].get('data_quality', 0)
        }
    
    def _check_thresholds(self, metrics: Dict) -> bool:
        """
        Verificar si se superan los umbrales
        
        Args:
            metrics: Métricas calculadas
            
        Returns:
            True si hay anomalía
        """
        anomaly_rate = metrics.get('avg_anomaly_rate', 0)
        
        # Si la tasa de anomalías es alta
        if anomaly_rate > 0.3:
            return True
        
        # Si la calidad es baja
        if metrics.get('avg_quality', 1) < 0.6:
            return True
        
        return False
    
    def _classify_anomaly(self, metrics: Dict) -> str:
        """
        Clasificar tipo de anomalía
        
        Args:
            metrics: Métricas calculadas
            
        Returns:
            Tipo de anomalía
        """
        if metrics.get('avg_anomaly_rate', 0) > 0.3:
            return 'HIGH_ANOMALY_RATE'
        
        if metrics.get('avg_quality', 1) < 0.6:
            return 'LOW_DATA_QUALITY'
        
        if metrics.get('trend') == 'DEGRADING':
            return 'DEGRADING_TREND'
        
        return 'NORMAL'
    
    def _determine_severity(self, anomaly_type: str, metrics: Dict) -> str:
        """
        Determinar severidad
        
        Args:
            anomaly_type: Tipo de anomalía
            metrics: Métricas
            
        Returns:
            Severidad: LOW/MEDIUM/HIGH/CRITICAL
        """
        if anomaly_type == 'CRITICAL':
            return 'CRITICAL'
        
        if anomaly_type in ['HIGH_ANOMALY_RATE', 'DEGRADING_TREND']:
            if metrics.get('avg_anomaly_rate', 0) > 0.5:
                return 'HIGH'
            return 'MEDIUM'
        
        if anomaly_type == 'LOW_DATA_QUALITY':
            return 'MEDIUM'
        
        return 'LOW'
    
    def _calculate_trend(self) -> str:
        """
        Calcular tendencia
        
        Returns:
            TRENDING UP/DOWN/STABLE
        """
        if len(self.history) < 3:
            return 'STABLE'
        
        recent = self.history[-3:]
        first = recent[0].get('anomaly_rate', 0)
        last = recent[-1].get('anomaly_rate', 0)
        
        diff = last - first
        
        if abs(diff) < 0.05:
            return 'STABLE'
        elif diff > 0:
            return 'INCREASING'
        else:
            return 'DECREASING'
    
    def _save_result(self, result: Dict):
        """
        Guardar resultado
        
        Args:
            result: Resultado del análisis
        """
        output_dir = Path("insights/anomaly-patterns")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"detect-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        self.logger.info(f"💾 Resultado guardado en {output_file}")
    
    def add_data_point(self, data: Dict):
        """
        Agregar punto de datos
        
        Args:
            data: Punto de datos
        """
        self.history.append(data)
    
    def reset(self):
        """Reiniciar historial"""
        self.history.clear()
        self.logger.info("🔄 Historial reiniciado")


def main():
    """Ejemplo de uso"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Detector de Anomalías')
    parser.add_argument('--threshold', type=float, default=0.7, help='Umbral de detección')
    
    args = parser.parse_args()
    
    detector = AnomalyDetector(args.threshold)
    
    # Agregar datos de ejemplo
    for i in range(5):
        detector.add_data_point({
            'timestamp': f'time-{i}',
            'anomaly_rate': 0.1 + (i * 0.05),
            'data_quality': 0.8 - (i * 0.05)
        })
    
    result = detector.detect()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
