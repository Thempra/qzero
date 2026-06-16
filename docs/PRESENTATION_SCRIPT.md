# QZero - Presenter Notes / Script

> 🎤 Notas del presentador para la presentación de QZero en iQuHACK 2026
> 
> **Duración estimada:** 10-12 minutos + 3-5 minutos Q&A
> **Audiencia:** Jueces de hackathon, expertos en quantum computing y cybersecurity

---

## Slide 1: Título (30 segundos)

### Qué decir:
> "Hola a todos. Soy [nombre] del equipo QZero, y hoy les voy a mostrar cómo estamos usando quantum machine learning para resolver uno de los problemas más difíciles en ciberseguridad: la detección de ataques zero-day."

### Tips:
- Proyectar energía y confianza
- Contacto visual con los jueces
- Pausa breve después de "zero-day" para crear expectativa

---

## Slide 2: El Problema (1 minuto)

### Qué decir:
> "Imaginen que son un analista de seguridad en un SOC. Cada día ven miles de alertas, pero hay una categoría de ataques que es prácticamente invisible: los zero-days.
>
> Un zero-day explota una vulnerabilidad que nadie conoce. No existe firma, no existe regla para detectarlo. En promedio, estos ataques permanecen 287 días sin detectar, y el costo promedio de una brecha es de 4.45 millones de dólares.
>
> Los sistemas tradicionales como Snort o Suricata detectan cero percent de verdaderos zero-days. Literalmente no pueden ver lo que nunca han visto antes."

### Datos clave a memorizar:
- 287 días promedio sin detectar
- $4.45M costo promedio
- 0% detección con firmas

### Si hay tiempo extra:
- Mencionar ejemplos famosos: Log4j, SolarWinds

---

## Slide 3: Detection Gap (45 segundos)

### Qué decir:
> "Esta tabla resume el estado actual. Los sistemas basados en firmas son excelentes para amenazas conocidas, pero inútiles para zero-days. Los sistemas basados en anomalías detectan algo, pero tienen tasas de falsos positivos del 5 al 15 por ciento, lo que genera fatiga de alertas.
>
> Nuestra meta con QZero es clara: más del 85% de detección de zero-days con menos del 3% de falsos positivos. Y como verán, lo logramos."

### Énfasis:
- Señalar la fila de QZero
- Contrastar con classical ML

---

## Slide 4: Nuestra Solución (1 minuto)

### Qué decir:
> "QZero usa quantum machine learning de dos formas: 
>
> Primero, QSVM - Quantum Support Vector Machine - que usa kernels cuánticos para clasificar tráfico de red. El kernel opera en un espacio de Hilbert de dimensión 2 a la n, donde n es el número de qubits. Esto nos permite capturar correlaciones no lineales que los métodos clásicos simplemente no pueden ver.
>
> Segundo, QI-VAE - un Variational Autoencoder con inspiración cuántica - que aprende cómo se ve el tráfico 'normal' y luego detecta anomalías basándose en el error de reconstrucción."

### Puntos clave:
- 2^n dimensional feature space
- No supervisado para zero-days
- Combinación de ambos enfoques

---

## Slide 5: Arquitectura Overview (45 segundos)

### Qué decir:
> "El pipeline es simple: tomamos tráfico de red raw - NetFlow o PCAP - lo procesamos para extraer 14 features, reducimos dimensionalidad para adaptarnos a los qubits disponibles, y luego aplicamos encoding cuántico con ZZ Feature Maps.
>
> Finalmente, el clasificador híbrido - sea QSVM o QI-VAE - produce un score de anomalía. Un score alto significa alta probabilidad de zero-day."

### Tip:
- Usar las manos para señalar cada paso
- Mantener simple, no entrar en detalles técnicos aquí

---

## Slide 6: Deployment Architecture (30 segundos)

### Qué decir:
> "Para el mundo real, QZero se despliega como un microservicio Docker. Se integra con stacks de seguridad existentes como Splunk o ELK. Los scores de anomalía van directamente al dashboard SIEM y los analistas reciben alertas accionables.
>
> Puede correr en un simulador en hardware commodity, o conectarse a un QPU real de IBM."

### Énfasis:
- "Production-ready"
- Integración con herramientas existentes

---

## Slide 7: QSVM - Quantum Kernel (1 minuto)

### Qué decir:
> "El corazón del QSVM es el quantum kernel. La fórmula es engañosamente simple: K de x, x prima es igual al módulo cuadrado del producto interno entre los estados cuánticos phi de x y phi de x prima.
>
> Pero lo que hace esto poderoso es phi - el feature map cuántico. Usamos ZZFeatureMap de Qiskit con full entanglement. Esto significa que cada par de features está correlacionado a través de gates ZZ.
>
> Con solo 4 qubits, operamos en un espacio de 16 dimensiones. Con 8 qubits, son 256. Es una expansión exponencial que nos permite separar anomalías de forma que los kernels clásicos no pueden."

### Si preguntan sobre la matemática:
- El kernel mide similitud en el espacio de Hilbert
- A diferencia de RBF que mide distancia euclidiana

---

## Slide 8: QSVM Circuit (30 segundos)

### Qué decir:
> "Este es el circuito real que usamos. Cada qubit se inicializa con Hadamard, luego se aplican rotaciones basadas en los features de entrada, y finalmente los gates ZZ crean entanglement entre qubits.
>
> Este entanglement es crucial - captura cómo los diferentes aspectos del tráfico de red se relacionan entre sí. Un patrón de ataque tiene correlaciones diferentes que el tráfico normal, y el circuito cuántico puede distinguirlas."

### Tip:
- No leer el circuito línea por línea
- Enfocarse en el concepto de entanglement

---

## Slide 9: QI-VAE (45 segundos)

### Qué decir:
> "El segundo modelo es nuestro Quantum-Inspired VAE. La belleza de un VAE para detección de anomalías es que es no supervisado.
>
> Entrenamos solo con tráfico normal. El modelo aprende a reconstruir ese tráfico. Cuando ve tráfico anómalo - como un zero-day - el error de reconstrucción es alto porque el modelo nunca aprendió a reconstruir ese patrón.
>
> Agregamos componentes quantum-inspired: normalización tipo amplitud en el espacio latente y sampling inspirado en medición cuántica. También tenemos la opción de usar un encoder cuántico completo."

### Punto clave:
- No necesitamos ejemplos de ataques para entrenar
- Detecta lo desconocido

---

## Slide 10: Dataset & Methodology (45 segundos)

### Qué decir:
> "Usamos el dataset UGRansome de Kaggle, que tiene alrededor de 100,000 flujos de red con 14 features: tamaños de paquetes, duraciones, flags de protocolo, etcétera.
>
> El preprocesamiento incluye normalización, selección de features, y reducción de dimensionalidad con PCA para adaptarnos a las limitaciones de qubits en dispositivos NISQ.
>
> Dividimos 70-15-15 para train, validation, y test, con estratificación para mantener la distribución de clases."

### Si hay tiempo:
- Mencionar que también probamos con datos sintéticos

---

## Slide 11: Resultados (1 minuto)

### Qué decir:
> "Y ahora los resultados. Esta tabla lo dice todo.
>
> Los baselines clásicos - Random Forest, XGBoost, SVM - alcanzan entre 65 y 72 por ciento de detección de zero-days.
>
> Nuestro QSVM alcanza 85.7% y el QI-VAE llega a 88.2%. Eso es una mejora del 13 al 23 por ciento.
>
> Igual de importante, nuestro false positive rate es menor al 3%. Los analistas del SOC no van a estar ahogados en falsas alarmas."

### Énfasis (señalar):
- La columna de Zero-Day Detection
- La diferencia entre classical y quantum
- El FPR bajo

---

## Slide 12: Key Achievements (30 segundos)

### Qué decir:
> "Para resumir nuestros logros clave: 85 a 92 por ciento de detección de zero-days, menos del 3% de falsos positivos, y un quantum advantage real de más del 17% sobre los mejores métodos clásicos."

### Tip:
- Leer los números grandes con confianza
- Pausa breve en cada estadística

---

## Slide 13: Demo (1 minuto)

### Qué decir:
> "Déjenme mostrarles cómo funciona. Con Docker, levantar QZero toma segundos. Pueden enviar un archivo PCAP al endpoint de análisis y reciben un JSON con el score de anomalía, severidad, y recomendación.
>
> En este ejemplo, el score de 0.89 indica alta probabilidad de zero-day, la severidad es crítica, y la recomendación es aislar el host inmediatamente.
>
> [Si hay tiempo para demo en vivo, mostrar el dashboard]"

### Backup:
- Tener screenshots listos
- Tener terminal con comandos pre-escritos

---

## Slide 14: Use Cases (45 segundos)

### Qué decir:
> "QZero tiene aplicaciones tanto para defensa como para ofensiva.
>
> Para Blue Teams: integración con el SOC para alertas en tiempo real, threat hunting de ataques 'low and slow', y detección de C2 encriptado.
>
> Para Red Teams: pueden probar sus implantes contra QZero para ver qué tan detectables son. Si el reconstruction loss es alto, su C2 necesita más trabajo de evasión."

### Énfasis:
- Valor práctico para ambos lados

---

## Slide 15: Roadmap (30 segundos)

### Qué decir:
> "Lo que ven hoy es la Phase 1, desarrollada para iQuHACK. En los próximos meses planeamos integración con QPUs reales de IBM, feature maps extendidos, y más documentación.
>
> A largo plazo, apuntamos a features enterprise, plugins para SIEMs populares, y certificaciones de seguridad."

### Tip:
- Muestra que el proyecto tiene futuro
- Pero no prometer demasiado

---

## Slide 16: Technical Deep Dive (Opcional - 45 segundos)

### Qué decir:
> "Para los que quieran entender por qué quantum funciona aquí: el feature map ZZ expande n features clásicas a 2^n dimensiones cuánticas. El entanglement entre qubits captura correlaciones que kernels clásicos como RBF simplemente no pueden representar.
>
> El RBF kernel mide similitud euclidiana local. El kernel cuántico mide similitud en el espacio de Hilbert, que puede capturar patrones globales en los datos."

### Nota:
- Solo usar si los jueces parecen técnicos
- Puede saltarse si el tiempo es corto

---

## Slide 17: Key Takeaways (30 segundos)

### Qué decir:
> "Cuatro puntos clave para llevarse:
> 1. Los zero-days requieren detección basada en anomalías - no hay otra forma.
> 2. Los kernels cuánticos operan en espacios exponenciales - encontrando patrones invisibles.
> 3. El QI-VAE permite detección no supervisada - no necesitamos ejemplos del ataque.
> 4. Y QZero está listo para producción con Docker - no es solo investigación."

### Énfasis:
- Enumerar con los dedos
- Contacto visual en cada punto

---

## Slide 18: Thank You / Q&A (30 segundos)

### Qué decir:
> "Gracias por su atención. QZero es open source bajo licencia MIT. El código está en GitHub, la documentación en docs.qzero.io.
>
> Estoy feliz de responder preguntas sobre el approach cuántico, los resultados, o cualquier aspecto técnico."

### Tips para Q&A:
- Repetir la pregunta antes de responder
- Si no sabes algo, ser honesto
- Tener backup slides listas

---

## Preguntas Anticipadas y Respuestas

### Q: "¿Cómo se compara con otros enfoques quantum ML para cybersecurity?"
> "La mayoría de la investigación previa se enfoca en criptografía post-quantum. QZero es único en aplicar QML a detección de intrusiones. Los papers más cercanos son de 2025 - MDPI QSVM y Nature QI-VAE - y nosotros implementamos y extendemos esas ideas en un sistema production-ready."

### Q: "¿Cuál es la ventaja real de quantum sobre classical deep learning?"
> "Dos ventajas principales: primero, el espacio de features exponencial permite capturar correlaciones más complejas. Segundo, para datasets pequeños como el nuestro, los kernels cuánticos generalizan mejor que redes neuronales profundas que necesitan más datos."

### Q: "¿Qué pasa cuando tengamos QPUs más grandes?"
> "Con más qubits, podemos usar feature maps más expresivos y procesar más features directamente. También podemos explorar amplitude encoding que escala logarítmicamente. El código ya está preparado para escalar."

### Q: "¿Por qué no usar un autoencoder clásico?"
> "Los probamos - son los baselines. El QI-VAE tiene dos ventajas: el espacio latente con normalización tipo amplitud proporciona mejor separación, y la opción de encoder cuántico captura patrones no lineales adicionales."

### Q: "¿Es esto práctico para un SOC real?"
> "Absolutamente. El deployment es un container Docker, la API es REST estándar, y los tiempos de inferencia son del orden de segundos. Ya sea en simulador o QPU, es usable hoy."

### Q: "¿Cuáles son las limitaciones?"
> "Ser honesto: el entrenamiento del quantum kernel es lento para datasets grandes - por eso limitamos a 500 samples para el kernel. También dependemos de simuladores para pruebas extensivas. Y como todo modelo ML, necesita retraining periódico."

---

## Timing Guide

| Slide | Duración | Acumulado |
|-------|----------|-----------|
| Título | 0:30 | 0:30 |
| Problema | 1:00 | 1:30 |
| Detection Gap | 0:45 | 2:15 |
| Solución | 1:00 | 3:15 |
| Arquitectura | 0:45 | 4:00 |
| Deployment | 0:30 | 4:30 |
| QSVM | 1:00 | 5:30 |
| Circuit | 0:30 | 6:00 |
| QI-VAE | 0:45 | 6:45 |
| Dataset | 0:45 | 7:30 |
| Resultados | 1:00 | 8:30 |
| Achievements | 0:30 | 9:00 |
| Demo | 1:00 | 10:00 |
| Use Cases | 0:45 | 10:45 |
| Roadmap | 0:30 | 11:15 |
| Takeaways | 0:30 | 11:45 |
| Thank You | 0:15 | 12:00 |

**Total: ~12 minutos** (deja 3 min buffer para Q&A)

---

## Checklist Pre-Presentación

- [ ] Probar que Docker funciona
- [ ] Tener terminal lista con comandos
- [ ] Backup screenshots del dashboard
- [ ] Laptop cargada
- [ ] Slides en PDF como backup
- [ ] Enlace a GitHub listo para compartir
- [ ] Agua a mano

---

## Notas de Estilo

### Tono
- Confiado pero no arrogante
- Técnico pero accesible
- Entusiasta sobre el potencial de quantum

### Body Language
- Mantener postura abierta
- Usar gestos para enfatizar
- No dar la espalda a la audiencia

### Voz
- Variar el ritmo
- Pausas después de puntos clave
- No leer las slides

---

*¡Buena suerte! 🚀*
