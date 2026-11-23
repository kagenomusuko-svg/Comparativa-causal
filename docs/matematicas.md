# Especificación matemática v1

## Pearl · pearl-2010

SCM recursivo finito (U,V,F). Cada ecuación es una tabla total sobre sus padres.
El orden topológico garantiza una solución única por contexto. Una intervención
reemplaza ecuaciones por constantes. Una observación restringe contextos por la
solución factual. Para un contrafáctico se retienen los mismos valores exógenos
al resolver el modelo intervenido. Con masa conjunta exógena se aplica abducción,
acción y predicción mediante filtrado, sustitución y suma de masas. Sin masa,
una conclusión puntual requiere acuerdo entre todos los contextos compatibles.
Un efecto distributivo es la diferencia entre las masas de dos regímenes do.
La identificación general a partir de datos observacionales queda fuera de v1.
La enumeración crece con el producto de los dominios exógenos.
Fuente: [Pearl 2010, §§2–3 y 5](https://proceedings.mlr.press/v6/pearl10a.html).

## Halpern · hp-2001-ch-2004

Modelo recursivo, contexto efectivo completo, candidato conjuntivo endógeno
(X=x) y efecto booleano sobre eventos endógenos. AC1 verifica ambos eventos.
AC2(a) busca una partición ((Z,W)) con (X⊆Z) y valores (x',w') tales
que ([X←x',W←w']¬φ). AC2(b) restaura (X=x), mantiene todo (W=w')
y exige (φ) al restaurar a su valor factual cada subconjunto de (Z).
AC3 descarta toda conjunción que tenga un subconjunto propio causal.
Se minimiza el número (k) de variables de (W) distintas de sus valores
efectivos entre los testigos AC2. La responsabilidad es (1/(1+k)) para
causas y cero en otro caso. El testigo incluye partición, valores y costo.
La búsqueda agota combinaciones con presupuesto explícito. Un agotamiento
impide certificar el veredicto. Se adopta la versión citada por Chockler y
Halpern para conservar la definición 3.2. La actualización de 2005 exige
también subconjuntos de W. La modificación de 2015 restringe contingencias
a valores efectivos. Se excluyen ambas variantes, normalidad y blame.
Fuentes: [HP 2001, definición 3.1](https://arxiv.org/abs/1301.2275),
[CH 2004, §§3.1–3.2](https://arxiv.org/abs/cs/0312038),
[Halpern 2015, §2](https://arxiv.org/abs/1505.00162).

## Wright · wright-1985-declared

Se representa el efecto efectivo y un registro de condiciones con verdad
efectiva parcial. Cada vía causal directa es una regla positiva avalada por
una ley o mecanismo declarado y su procedencia. La regla declara antecedentes
conjuntamente suficientes y que cada antecedente es esencial para esa vía.
Es una hipótesis explícita del modelo, no una inferencia de coocurrencias.
Los bloqueos y la preempción requieren antecedentes de activación específicos
de cada vía. Para cada regla aplicable, quitar el candidato del conjunto de
antecedentes elimina el certificado de suficiencia de esa vía. Se descarta el testigo si el conjunto reducido
contiene íntegramente los requisitos de otra vía conocida. Con inventario abierto,
la esencialidad se limita al modelo declarado. Otra vía puede certificar el mismo efecto. La necesidad global se
evalúa sobre las vías declaradas si su cobertura es completa y sus estados
permiten resolverla. Se conservan los mecanismos y conjuntos testigos.
Con inventario abierto o condiciones desconocidas, la falta de testigos no
prueba ausencia de causalidad. No se infieren leyes ni se modelan cadenas
o todas las variantes jurídicas del criterio. Se coteja cada conjunto reducido con las vías alternativas activas. [Wright 1985, pp. 1788–1803](https://scholarship.kentlaw.iit.edu/fac_schol/697/).

## Bayes · fnl-2013-exact

DAG categórico con tablas condicionales exhaustivas y normalizadas. La masa
conjunta es el producto de las filas correspondientes a una asignación.
La posterior divide la masa conjunta con la evidencia por su masa marginal.
Dos alternativas son estados distintos de una variable de hipótesis. La
razón de verosimilitud divide las masas de la misma evidencia condicionadas
a dichos estados. Se informa indefinición ante condicionamientos nulos y
se distingue una razón infinita de 0/0. La sensibilidad compara la base con
escenarios de reemplazo de filas completas. Enumeración exacta racional,
exponencial en el número de variables. Las dependencias se conservan por
marginalización conjunta. Los patrones o idioms de Fenton, Neil y Lagnado
orientan la construcción documentada de redes legales. El motor recibe
esa construcción y aplica inferencia bayesiana ordinaria. Los roles de
hipótesis y evidencia se especifican en cada consulta. Las flechas expresan
factorización y solo adquieren semántica causal por un supuesto explícito.
Se consultó el resumen original para precisar el papel de los patrones de
modelización. El texto completo no estuvo accesible y los casos de
verificación bayesiana se calcularon de forma independiente sobre redes
sintéticas. [Fenton, Neil y Lagnado 2013](https://doi.org/10.1111/cogs.12004).
