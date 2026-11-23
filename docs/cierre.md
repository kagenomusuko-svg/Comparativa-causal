# Informe de cierre v0.1.0

| Motor | Estado y versión matemática | Operaciones verificadas |
| --- | --- | --- |
| Pearl | Operativo para SCM discretos recursivos con tablas explícitas. `pearl-2010` | Observación, asociación, intervención, contrafácticos puntuales y distribuciones, diferencia de probabilidades de intervención |
| Halpern–Pearl y Chockler–Halpern | Operativo para AC1–AC3 originales y responsabilidad de la definición 3.2. `hp-2001-ch-2004` | Candidatos conjuntivos, efecto booleano, contingencias, minimalidad y testigos de costo mínimo |
| Wright | Operativo para vías causales directas con conjuntos y leyes declarados. `wright-1985-declared` | Testigos NESS, concurrencia, vías alternativas, bloqueos explícitos y cobertura incompleta |
| Fenton, Neil y Lagnado | Inferencia ordinaria exacta sobre redes legalmente modeladas y parametrizadas. `fnl-2013-exact` | Posteriores, comparación por estados, razones de verosimilitud, evidencia dependiente y sensibilidad |

Las [especificaciones](matematicas.md) detallan definiciones, fuentes y límites.
La [referencia de ejecución](contrato.md) describe los parámetros, diagnósticos
y el significado de cada salida JSON. Los ejemplos comparten un registro
sintético y conservan resultados propios por motor.

Fuera de alcance quedan identificación general a partir de distribuciones
observacionales, SCM cíclicos y continuos, variantes HP de 2005 y 2015,
blame, inferencia de leyes NESS, inferencia automática de cadenas causales,
construcción automática de redes y aprendizaje de parámetros. La
exhaustividad presupuestada puede impedir certificar un resultado. Las
conclusiones NESS dependen de la suficiencia causal y la cobertura
declaradas para el efecto. El contrato de integración externa se publica
sin requerir un servicio o repositorio asociado.

## Verificación

`python -m unittest discover -s tests -v` ejecutó 19 pruebas con Python
3.12. Incluyen los incendiarios conjuntivo y disyuntivo, la preempción
de la botella de HP, una variante de la votación de CH, la confusión
de Pearl, vías alternativas y preemptivas de NESS, las cinco unidades contaminantes entre siete de Wright,
y evidencia duplicada
por dependencia determinista. Cubren cálculo independiente, errores de
validación, normalización, información incompleta, evidencia imposible,
determinismo y equivalencia CLI/API. Los esquemas y los cuatro ejemplos se
verificaron también con Draft 2020-12 mediante jsonschema, herramienta de
verificación opcional con licencia MIT.

Se construyó una rueda Python sin descargar dependencias y se ejecutaron
los cuatro ejemplos con la CLI instalada en un entorno virtual limpio. La CI de GitHub
Actions está configurada para Python 3.11, 3.12 y 3.13. En ejecución solo se
usa CPython y su biblioteca estándar, bajo la licencia de Python Software
Foundation. Para construir la rueda se usa setuptools, bajo licencia MIT.
Las acciones de checkout y setup-python se publican bajo licencia MIT.

## Instalación y ejecución

```bash
python -m pip install .
causal examples/pearl.json
causal examples/halpern.json
causal examples/ness.json
causal examples/bayesian.json
```

Desde el repositorio también se puede sustituir `causal` por `python -m causal`.
La API `from causal import execute` acepta la solicitud decodificada y
devuelve el mismo sobre. En la rama de entrega, `git rev-parse HEAD`
identifica el commit exacto y cada salida indica `software_version`.
