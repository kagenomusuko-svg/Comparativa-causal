# Informe de cierre

## Base histórica 0.2.0

| Motor | Definición y condiciones | Operaciones y comprobaciones |
| --- | --- | --- |
| [Pearl](../causal/engines/pearl.py) | SCM recursivo de Pearl, con dominios finitos y ecuaciones totales. Identificación en DAG con latentes explícitos y soporte observacional. | Observación, asociación, intervención, contrafáctico, efecto y [ajuste](../causal/engines/identification.py) por puerta trasera y delantera. El ejemplo de puerta delantera obtiene `3/5`, comprobado mediante factorización truncada con un confundente latente. |
| [Halpern–Pearl y Chockler–Halpern](../causal/engines/halpern.py) | AC1–AC3 originales de 2001 y responsabilidad de la definición 3.2 de 2004, con contexto efectivo completo. | Contingencias, estabilidad, minimalidad y testigo de costo mínimo. El ejemplo disyuntivo devuelve `1/2` para cada causa consultada. Se reproducen la preempción de la botella y una variante de la votación de CH. |
| [Wright](../causal/engines/ness.py) | NESS con vías directas declaradas y extensión explícita de [composición](../causal/engines/ness_composition.py) mediante leyes estables. | Conjuntos suficientes, concurrencia, preempción, cadenas y alternativas. Se reproduce el caso de Wright de cinco unidades contaminantes entre siete. El ejemplo por etapas devuelve el conjunto `{A, B}` con dos pasos. |
| [Bayes](../causal/engines/bayesian.py) | DAG finito con CPT completas e inferencia exacta. [Patrones](../causal/engines/evidence_patterns.py) contrastados con Lagnado, Fenton y Neil 2012. | Posteriores, hipótesis rivales, razón de verosimilitud, evidencia dependiente, sensibilidad y cinco patrones documentados. Se reproduce una posterior de `1/12` con razón de verosimilitud `9`. |

Consulte la [especificación matemática y sus fuentes](matematicas.md) y
el [contrato de ejecución y trazabilidad](contrato.md). El registro de
cada ejecución conserva su versión de software y los esquemas publican
una estructura para agregar resultados de otros motores. La integración
inicial de los cuatro motores quedó en `main` por avance rápido al
commit `3c4b675a611e69e91b0195204629aad30df1c3eb`.
[Historial de main](https://github.com/kagenomusuko-svg/Comparativa-causal/commits/main/).

## Verificación

Las 42 pruebas comprueban referencias académicas, cálculo independiente,
determinismo, JSON Schema, equivalencia CLI/API para todos los ejemplos
publicados, límites de recursos, contradicciones, información ausente,
arcos y dependencias. GitHub Actions instala las dependencias de prueba
y ejecuta la suite en Python 3.11, 3.12 y 3.13.

La ejecución solo usa Python y su biblioteca estándar, con licencia
Python Software Foundation. Se usa setuptools con licencia MIT para
construcción y jsonschema 4.25.1 con licencia MIT para pruebas opcionales.

## Ejecución

```bash
python -m pip install .
causal examples/pearl.json
causal examples/pearl-backdoor.json
causal examples/pearl-frontdoor.json
causal examples/halpern.json
causal examples/ness.json
causal examples/ness-chain.json
causal examples/bayesian.json
causal examples/bayesian-testimony.json
causal - < examples/pearl-frontdoor.json
python -m pip install '.[test]'
python -m unittest discover -s tests -v
```

`causal.execute` acepta la solicitud decodificada y devuelve el mismo
sobre, con estados diferenciados y certificados específicos de cada motor.

## Límites

El ajuste requiere un criterio válido y datos de observación con
soporte. La identificación general queda fuera del dominio implementado.
AC2 y la composición de certificados pueden agotar el presupuesto.
NESS requiere estabilidad y cobertura declaradas para las conclusiones
que las presuponen. Los patrones bayesianos se basan en el texto
completo del artículo metodológico de 2012. En 0.2.0 se había consultado el resumen de 2013. Su revisión completa
corresponde a la adecuación de 0.3.0 descrita más abajo. No se introducen cifras para suplir CPT
ausentes ni se infieren mecanismos o relaciones a partir de documentos.

## Adecuaciones de 0.3.0

Se conserva la entrega de 0.2.0 como base histórica. La revisión de 0.3.0
consultó el texto editorial completo de 2013, incluidos sus diagramas
y tablas, y el trabajo complementario de 2012. El perfil nuevo añade
exactitud, oportunidad necesaria, motivo agregado, dependencia entre
informes, coartada con exactitud, explicaciones competitivas,
exclusión con calibración, análisis de estructura, actualización por
etapas y sensibilidad de evidencia. Las pruebas diferencian las
reproducciones numéricas de las verificaciones de estructura
para figuras sin tablas completas. [Correspondencia académica](fnl.md)

La trazabilidad cubre hojas individuales y agrupaciones enumeradas,
aplica un modo estricto opcional general y exige cobertura de
probabilidades en el perfil bayesiano nuevo. Distingue búsquedas
observadas, dependencias matemáticas exactas entre artefactos y
dependencias de entrada conservadoras. La invalidación acepta
rutas o una solicitud revisada y conserva el ámbito de los certificados
por reconstrucción. [Trazabilidad y comandos](contrato.md)

La suite ejecuta 62 pruebas con 11 ejemplos, incluida la regresión de
0.2.0, y valida esquemas de entrada, resultado, lote, cobertura e
invalidación. El registro de GitHub Actions en `main` identifica
el estado de la matriz para cada commit.
