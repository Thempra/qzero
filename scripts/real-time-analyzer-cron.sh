#!/bin/bash
# Wrapper para el analizador en tiempo real de QZero (integro en el proyecto)

SCRIPT_PATH="/home/thempra/projects/qzero/scripts/real-time-analyzer.py"
LOG_FILE="/home/thempra/projects/qzero/logs/real-time-analyzer.log"
PID_FILE="/home/thempra/projects/qzero/insights/real-time-analyzer.pid"

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            echo "El analizador ya está en ejecución (PID: $(cat $PID_FILE))"
            exit 1
        fi

        echo "🚀 Iniciando analizador en tiempo real de QZero (MODELO CUÁNTICO)..."
        echo "⚛️  Usando QSVM y QIVAE para detección de anomalías cuánticas"
        echo "📋 Logs: $LOG_FILE"
        echo "📊 Status: $PID_FILE"

        nohup python3 "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        echo "✅ Analizador iniciado con PID: $(cat $PID_FILE)"
        ;;

    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "El analizador no está en ejecución"
            exit 1
        fi

        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "🛑 Deteniendo analizador cuántico (PID: $PID)..."
            kill $PID
            rm -f "$PID_FILE"
            echo "✅ Analizador detenido"
        else
            echo "PID no encontrado o proceso no existe"
            rm -f "$PID_FILE"
        fi
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p $PID > /dev/null 2>&1; then
                echo "✅ Analizador cuántico en ejecución (PID: $PID)"
                echo ""
                echo "Última ejecución:"
                tail -n 5 "$LOG_FILE" 2>/dev/null || echo "No hay logs disponibles"
            else
                echo "❌ Analizador no está en ejecución (PID file existe pero proceso no)"
                rm -f "$PID_FILE"
            fi
        else
            echo "❌ Analizador no está en ejecución"
        fi
        ;;

    logs)
        tail -f "$LOG_FILE"
        ;;

    *)
        echo "Uso: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "🚀 Analizador en tiempo real de QZero - MODELO CUÁNTICO"
        echo ""
        echo "Comandos:"
        echo "  start  - Iniciar el analizador con análisis CUÁNTICO"
        echo "  stop   - Detener el analizador"
        echo "  restart - Reiniciar el analizador"
        echo "  status  - Ver estado del analizador"
        echo "  logs    - Ver los logs en tiempo real"
        exit 1
        ;;
esac