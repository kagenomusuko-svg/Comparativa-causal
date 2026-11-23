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
La enumeración crece con el producto de los dominios exógenos.

La operación observacional `identify` recibe un DAG causal con nodos latentes
explícitos y masa conjunta de los observables. Para puerta trasera, comprueba
que el conjunto nominado no incluya descendientes de X y que separe X de Y
al eliminar las aristas salientes de X. Evalúa ∑z P(y|x,z)P(z).
Para puerta delantera con un mediador M, comprueba que M intercepte todos
los caminos dirigidos X→Y, que no haya puerta trasera X–M y que X bloquee
las puertas traseras M–Y. Evalúa ∑m P(m|x) ∑x′ P(y|m,x′)P(x′).
La d-separación se reduce a separación en el grafo ancestral moralizado.
Antes de evaluar la fórmula, se contrastan con la masa las independencias
condicionales por pares de observables que el grafo implica. Es una prueba
necesaria de compatibilidad, con alcance limitado para DAG con latentes.
La evaluación exacta exige positividad de cada condicionamiento de peso
positivo. Un criterio fallido documenta el alcance de ese criterio.
El modelo asume Markov causal, modularidad y que el DAG describe las
dependencias pertinentes. No se aplica identificación general.
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
El certificado conserva además la asignación factual de Z y cuántos
subconjuntos se verificaron. AC3 evalúa todo subconjunto propio no vacío
hasta encontrar un contraejemplo. La búsqueda agota combinaciones con presupuesto explícito. Un agotamiento
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
prueba ausencia de causalidad. La operación directa evalúa vías al efecto. Para cadenas, `reconstruct`
exige un DAG de reglas positivas con raíces enumeradas. Cada regla se
puede componer únicamente cuando su estabilidad está declarada por quien
modela y sus antecedentes y consecuente están presentes. Un certificado
es una unión de hojas y pasos, calculada en orden topológico por el
producto de las derivaciones de los antecedentes. La inducción en ese
orden demuestra suficiencia de las hojas bajo las leyes declaradas.
El candidato intermedio puede actuar como hoja efectiva. El cierre de
las leyes activas sobre el conjunto reducido comprueba que ninguna
derivación declarada conserve el efecto al retirar el candidato. Los
inventarios abiertos permiten conclusiones condicionadas a los
mecanismos declarados. La necesidad en todo el inventario exige
cobertura, ausencia de lagunas pertinentes y un candidato raíz.
Una lista de reconstrucciones se evalúa por separado. La coincidencia
entre sus veredictos tiene alcance sobre esa lista. El tamaño de los
certificados puede crecer exponencialmente. Se excluye la inferencia de
leyes y de compatibilidad física, así como la composición en presencia
de ciclos o efectos inhibidores sin condiciones de habilitación explícitas. Se coteja cada conjunto reducido con las vías alternativas activas. [Wright 1985, pp. 1788–1803](https://scholarship.kentlaw.iit.edu/fac_schol/697/).

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
marginalización conjunta. Los patrones son fragmentos de DAG que
se ensamblan identificando roles con variables declaradas. La inferencia
sobre el DAG ensamblado sigue siendo bayesiana ordinaria. Cada tabla
condicional debe cubrir los padres efectivos del nodo. El usuario
declara las dependencias adicionales, los dominios y todas las cifras.
Los patrones nunca asignan cifras ni completan datos.

| Patrón | Arcos requeridos | Referencia de 2012 |
| --- | --- | --- |
| `evidence` | Objetivo → informe | §3.1, figs. 3–4 |
| `evidence_reliability` | Objetivo y fiabilidad → informe, con independencia marginal entre ambos padres | §3.2, figs. 5–7 |
| `opportunity_motive` | Oportunidad y/o motivo → hipótesis | §3.3, fig. 8 |
| `testimony_components` | Objetivo, sensibilidad, objetividad y veracidad → informe | §3.4, fig. 9 |
| `alibi` | Oportunidad → hipótesis e informe. Hipótesis → veracidad → informe. | §3.5, fig. 10 |

Se consultó el texto completo de [Lagnado, Fenton y Neil 2012](https://doi.org/10.1080/19462166.2012.682656)
en la [copia pública de autor](https://www.researchgate.net/publication/236944352_Legal_idioms_a_framework_for_evidential_reasoning).
Las figuras 3–7 se contrastaron con cálculos exactos. De
[Fenton, Neil y Lagnado 2013](https://doi.org/10.1111/cogs.12004) se
consultó el resumen original. El texto completo de 2013 no estuvo
accesible y la cobertura de los patrones se limita a los fragmentos
verificados en 2012. Los identificadores, la expansión de arcos y los
certificados JSON son decisiones de implementación de este proyecto.
