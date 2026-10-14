#!/usr/bin/env python3
"""
QZero Trend Analyzer
Analiza tendencias de insights y genera resumen ejecutivo
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("qzero-trend-analyzer")


class TrendAnalyzer:
    """Analiza tendencias de insights del proyecto QZero"""

    def __init__(self, insights_dir, output_dir, log_file):
        self.insights_dir = Path(insights_dir)
        self.output_dir = Path(output_dir)
        self.log_file = Path(log_file)
        self.insights = []
        self.trends = defaultdict(list)

    def load_insights(self):
        """Carga todos los archivos de insights"""
        logger.info("Cargando insights del proyecto...")

        # Buscar todos los archivos JSON en insights/
        json_files = list(self.insights_dir.glob("**/*.json"))

        if not json_files:
            logger.warning("No se encontraron archivos de insights")
            return

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Si es una lista (común para insights)
                if isinstance(data, list):
                    self.insights.extend(data)
                # Si es un objeto (común para reportes)
                elif isinstance(data, dict):
                    self.insights.append(data)

                logger.debug(f"Cargado: {json_file.name} ({len(data) if isinstance(data, list) else 1} items)")

            except Exception as e:
                logger.error(f"Error cargando {json_file}: {e}")

        logger.info(f"Total insights cargados: {len(self.insights)}")

    def analyze_trends(self):
        """Analiza tendencias por categoría y severidad"""
        logger.info("Analizando tendencias...")

        # Agrupar por categoría y severidad
        by_category = defaultdict(lambda: defaultdict(int))
        by_severity = defaultdict(int)
        by_actionable = defaultdict(int)

        for insight in self.insights:
            # Normalizar keys
            category = insight.get('category', 'unknown')
            severity = insight.get('severity', 'unknown')
            actionable = insight.get('actionable', False)

            by_category[category][severity] += 1
            by_severity[severity] += 1
            if actionable:
                by_actionable['actionable'] += 1

        self.trends = {
            'by_category': dict(by_category),
            'by_severity': dict(by_severity),
            'by_actionable': dict(by_actionable),
            'total_insights': len(self.insights),
            'actionable_count': by_actionable['actionable']
        }

        logger.info("Análisis de tendencias completado")

    def generate_summary(self):
        """Genera resumen ejecutivo"""
        logger.info("Generando resumen ejecutivo...")

        trends = self.trends
        total = trends['total_insights']

        # Encontrar categoría más frecuente
        top_category = max(trends['by_category'].items(),
                          key=lambda x: sum(x[1].values()))[0] if trends['by_category'] else "N/A"

        # Encontrar severidad más común
        top_severity = max(trends['by_severity'].items(),
                          key=lambda x: x[1])[0] if trends['by_severity'] else "N/A"

        # Calcular tasa de actionable
        actionable_rate = (trends['actionable_count'] / total * 100) if total > 0 else 0

        summary = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_insights': total,
                'actionable_count': trends['actionable_count'],
                'actionable_rate': round(actionable_rate, 2),
                'top_category': top_category,
                'top_severity': top_severity,
                'categories_count': len(trends['by_category'])
            },
            'trends': {
                'by_category': trends['by_category'],
                'by_severity': trends['by_severity']
            },
            'recommendations': self._generate_recommendations(trends, top_category, actionable_rate)
        }

        return summary

    def _generate_recommendations(self, trends, top_category, actionable_rate):
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []

        # Recomendación 1: Alta tasa de actionable
        if actionable_rate > 30:
            recommendations.append({
                'priority': 'high',
                'message': 'Alta tasa de insights accionables. Considerar priorizar seguimiento de estos puntos.'
            })

        # Recomendación 2: Categoría específica dominante
        if top_category and top_category != 'overall_quality':
            recommendations.append({
                'priority': 'medium',
                'message': f'La categoría "{top_category}" domina el análisis. Considerar profundizar en este área.'
            })

        # Recomendación 3: Insuficiente actionable
        if actionable_rate < 10:
            recommendations.append({
                'priority': 'low',
                'message': 'Tasa baja de insights accionables. Considerar mejorar la calidad de los insights generados.'
            })

        # Recomendación 4: Equilibrio de severidades
        if trends['by_severity']:
            critical_count = trends['by_severity'].get('critical', 0)
            if critical_count > 0:
                recommendations.append({
                    'priority': 'high',
                    'message': f'Se detectaron {critical_count} alertas críticas. Revisar inmediatamente.'
                })

        return recommendations

    def save_report(self, summary):
        """Guarda el reporte"""
        timestamp = summary['timestamp'].split('T')[0]
        time_part = summary['timestamp'].split('T')[1].split('.')[0]

        output_file = self.output_dir / f"trend-summary-{timestamp}_{time_part}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Reporte guardado: {output_file}")

    def run(self):
        """Ejecuta el análisis completo"""
        try:
            self.load_insights()
            self.analyze_trends()
            summary = self.generate_summary()
            self.save_report(summary)
            return summary
        except Exception as e:
            logger.error(f"Error en el análisis: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='QZero Trend Analyzer')
    parser.add_argument('--insights-dir', required=True, help='Directorio de insights')
    parser.add_argument('--output-dir', required=True, help='Directorio de salida')
    parser.add_argument('--timestamp', help='Timestamp personalizado')
    parser.add_argument('--log-file', required=True, help='Archivo de log')

    args = parser.parse_args()

    analyzer = TrendAnalyzer(
        insights_dir=args.insights_dir,
        output_dir=args.output_dir,
        log_file=args.log_file
    )

    summary = analyzer.run()

    print("\n" + "="*70)
    print("📊 QZero Trend Analyzer - Resumen Ejecutivo")
    print("="*70)
    print(f"\n📅 Timestamp: {summary['timestamp']}")
    print(f"\n📈 Métricas Principales:")
    print(f"   • Total Insights: {summary['summary']['total_insights']}")
    print(f"   • Accionables: {summary['summary']['actionable_count']} ({summary['summary']['actionable_rate']}%)")
    print(f"   • Categoría Dominante: {summary['summary']['top_category']}")
    print(f"   • Severidad Más Común: {summary['summary']['top_severity']}")
    print(f"   • Categorías: {summary['summary']['categories_count']}")

    print(f"\n💡 Recomendaciones:")
    for i, rec in enumerate(summary['recommendations'], 1):
        print(f"   {i}. [{rec['priority'].upper()}] {rec['message']}")

    print("\n" + "="*70)


if __name__ == '__main__':
    main()