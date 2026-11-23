# Metodología bayesiana y correspondencia con las fuentes

El perfil `bn-exact-fnl-2012-2013` combina la construcción por fragmentos
descrita por los autores y la inferencia bayesiana exacta ordinaria.
La red representa la dirección causal postulada en la reconstrucción.
El cálculo puede actualizar hipótesis a partir de sus efectos observados.
La asignación de roles y los parámetros pertenecen a la reconstrucción
y deben quedar declarados. El motor admite estados categóricos para
una hipótesis consultada, una extensión de la exposición principalmente
booleana de 2013. Los estados comparados son distintos dentro de la misma
variable. Declárese una categoría adicional si las dos hipótesis no
agotan el espacio. Las alternativas con trayectorias propias pueden
usar el selector descrito más abajo. La orientación de los arcos y el
orden de presentación de la evidencia cumplen funciones diferentes.

Fuentes consultadas en texto completo, con sus figuras:

- Fenton, Neil y Lagnado 2013. [Publicación](https://doi.org/10.1111/cogs.12004) · [manuscrito de los autores](https://www.eecs.qmul.ac.uk/~norman/papers/legal_arguments_final_submitted.pdf) · [copia pública del PDF editorial](https://studylib.net/doc/13237904/).
- Lagnado, Fenton y Neil 2012. [Publicación](https://doi.org/10.1080/19462166.2012.682656) · [copia de autor](https://www.researchgate.net/publication/236944352_Legal_idioms_a_framework_for_evidential_reasoning).
- Fenton, Neil y Lagnado, informe sobre ponderación en trayectorias excluyentes citado por el artículo, versión de 2012. [Informe técnico](https://www.eecs.qmul.ac.uk/~norman/papers/soft_evidencence_mutual_exclusivity.pdf).

## Correspondencia y verificación

| Capacidad | Fuente | Contrato y verificación |
| --- | --- | --- |
| Evidencia simple, corroboración y conflicto | 2012 §3.1, figs. 3–4. 2013 §§2 y 3.2, figs. 1–4 | `evidence` monta objetivo → informe. Varias instancias componen informes. La marginalización conjunta admite evidencia favorable y contraria. Las pruebas reproducen `1/12` y LR `9` (2012) y `1000000/1000099` y LR `1000000` (2013). |
| Exactitud y cadena de medición | 2012 §3.2, figs. 5–7. 2013 §3.3, figs. 5–7 | `evidence_reliability` conserva la variante simple de 2012 con independencia marginal. `evidence_accuracy` expresa objetivo y exactitud → informe y permite las dependencias declaradas. La figura 5 de 2013 da `9500000/59000891` con un informe positivo y `1/100` con inexactitud conocida. Las cadenas se componen con varias instancias. |
| Componentes del testimonio | 2012 §3.4, fig. 9. 2013 §3.3, fig. 8 | `testimony_components` conserva los componentes como padres del informe de 2012. `accuracy_components` agrega un nodo de exactitud determinista como en 2013. Se verifican arcos y roles; la figura 8 no parametriza la red. |
| Oportunidad y motivo | 2012 §3.3, fig. 8. 2013 §3.4, figs. 9–13 | `opportunity_motive` conserva el fragmento básico; `necessary_opportunity` verifica el cero lógico indicado por el modelo; `aggregate_motive` une dos o más motivos en un nodo común y rechaza los arcos directos de esos motivos individuales a la hipótesis. Las pruebas estructurales reconstruyen la disposición de las figuras. |
| Informes dependientes | 2013 §3.5, figs. 14–15 | `dependent_evidence` permite primer informe → segundo y el nodo que gobierna la dependencia. Con las CPT publicadas, dos lecturas positivas dan `8/17` si son redundantes y `64/73` si son independientes dado el objetivo. |
| Coartada | 2012 §3.5, fig. 10. 2013 §3.6, figs. 16–17 | `alibi` lleva hipótesis → veracidad. `alibi_accuracy` lleva hipótesis → exactitud. Se comprueba el fragmento de la figura 16 y se puede acoplar el segundo informe con `evidence_accuracy`. |
| Explicaciones conjuntas y excluyentes | 2013 §3.7, figs. 18–20 | `explaining_away` monta el colisionador. `exclusive_explanations` añade un selector que valida la exclusión y conserva las trayectorias. La CPT de coincidencia de la figura 18 con el reparto simétrico da `100/101`. Se prueban también ponderaciones asimétricas y tres trayectorias según el informe complementario. |
| Evidencia directa, indirecta y ensamblaje | 2013 §3.8 y §4, figs. 21–22 | `structure` valida arcos y devuelve un certificado, incluso al faltar las CPT. Clasifica enlaces directos y trayectorias sin colisionadores de dos o más pasos. `unclassified` deja abierta cualquier relación que quede fuera de esa clasificación estructural. Se verifican los subgrafos combinados y la separación de hipótesis e informes. |
| Actualización por etapas y sensibilidad de informes | 2013 §4, tabla 1 y fig. 23 | `evidence_sequence` conserva observaciones por acumulación y posterior por etapa. `evidence_sensitivity` varía un informe a la vez y devuelve los extremos sobre sus estados con soporte. La prueba numérica usa las figuras 14–15. La figura 22 y la tabla 1 no publican todas las CPT del caso compuesto, por lo que su secuencia de cifras no se usa como fixture numérica. |

La tabla de entrada completa conserva los factores de la misma red en cada
actualización y el resultado conserva las masas conjuntas por estado y
la masa marginal observada. Todos los cocientes se calculan como fracciones.
El perfil omite asignaciones automáticas de cifras, decisiones procesales
y clasificación del valor probatorio por umbrales. Las extensiones
generales de redes, el formato JSON y la enumeración racional son decisiones
del repositorio.

## Selector y evidencia blanda

En `exclusive_explanations`, `roles.causes` lista los nodos causales y
`roles.selector` identifica una hoja con esos padres. `settings.active_states`
declara el estado activo de cada causa, `settings.pathways` el estado
correspondiente del selector y `settings.impossible` el estado que
representa cero o varias causas activas. El usuario entrega su CPT
determinista. La validación exige probabilidad uno para el estado
correspondiente a cada combinación. Se admite un selector por consulta.

Para calibrar automáticamente, se toman las marginales de activación
(x_i) después de la evidencia disponible sobre ancestros. Las trayectorias
deben estar d-separadas entre sí dada esa evidencia. Se fijan las masas
objetivo de cada vía a (x_i / \sum_j x_j) y la masa imposible a cero.
La ponderación equivalente en cada estado del selector es la masa
objetivo dividida por la marginal de calibración del selector. El uso
de fracciones permite comprobar la normalización y detectar ausencia
de soporte. La recalibración ante evidencia nueva de ancestros sigue
el procedimiento del informe técnico complementario. Las observaciones
restantes se acumulan al condicionar la red ponderada.

`parameters.soft_evidence` permite, como opción del repositorio, declarar
directamente una distribución objetivo para un solo nodo. En un selector
esa distribución debe dar masa cero al estado imposible.
El certificado distingue la calibración automática de una distribución
objetivo explícita. La opción explícita conserva las proporciones
pedidas para el selector al calibrar y puede cambiar las marginales
causales originales. La estructura sin CPT no calcula probabilidades.

## Migración

Los perfiles y contratos de 0.2.0 siguen disponibles. `fnl-2013-exact`
conserva `infer`, `sensitivity` y los cinco fragmentos de 2012.
Para usar patrones u operaciones nuevos, cambie `mathematical_version`
a `bn-exact-fnl-2012-2013` y añada procedencia individual o agrupada
para cada probabilidad usada o declarada, incluidas las sustituciones
de sensibilidad. La migración de una misma red con parámetros
documentados conserva sus probabilidades previas y posteriores.
[Ejemplo migrado y estricto](../examples/bayesian-strict.json).
