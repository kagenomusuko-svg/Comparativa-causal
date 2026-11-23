# Contrato v1

`causal.execute(request)` recibe estructuras JSON decodificadas y devuelve
un objeto serializable. La CLI emite el mismo objeto y usa código 0 en
`success` y 1 cuando el cálculo solicitado falla. La CLI rechaza claves
duplicadas y constantes numéricas no finitas. Los esquemas Draft 2020-12
describen la estructura. El validador local controla además referencias,
filas exhaustivas, dominios, orden topológico y normalización.

## Solicitud

`schema_version` es `"1"`. Se requiere `case`, `engine`,
`mathematical_version`, `operation`, `model` y `parameters`.
`options.max_steps` tiene valor efectivo inicial 100 000. Cada motor
contabiliza sus operaciones elementales, incluidas comprobaciones de tablas.
El presupuesto mide pasos y no memoria ni segundos. Los valores discretos
son etiquetas de texto no vacías. Se recomiendan fracciones o decimales
en cadenas para preservar el valor textual exacto de los parámetros.
La CLI rechaza números de punto flotante cuya lectura redondea el valor
decimal original. En Python, cada float se interpreta mediante su
representación decimal corta. Las probabilidades de salida son siempre cadenas racionales.

El caso contiene `id`, `reference_event` y `entries` con identificadores
únicos. Cada registro tiene `id`, `kind`, `text`, y opcionalmente
`state` y `refs`. Use referencias entre proposiciones y fuentes y
registros de apoyo u oposición. Para secuencias use `kind: "sequence"`
y referencias en orden temporal. Los estados documentales son
`accredited`, `refuted`, `disputed`, `unknown` y `pending`.
Las listas `modeling_hypotheses` y `assumptions` se declaran por ejecución.
`provenance` vincula rutas o etiquetas del modelo con identificadores del
caso. El adaptador valida estos vínculos y entrega a cada motor el modelo
y los parámetros declarados. El significado factual lo proporcionan
asignaciones explícitas del modelo.

## Operaciones y resultados

| Motor | Operación | Parámetros | Resultado |
| --- | --- | --- | --- |
| Pearl | `observe` | `query`, opcionales `context`, `observed` | Verdad factual o distribución condicional |
| Pearl | `associate` | `query`, `observed`, opcional `context` | Probabilidad observacional |
| Pearl | `intervene` | `query`, `do`, opcional `context` | Solución o distribución intervenida |
| Pearl | `counterfactual` | `query`, `do`, opcionales `context`, `observed` | Solución o distribución de los mismos contextos compatibles |
| Pearl | `effect` | `query`, `do`, `baseline` | Probabilidades de ambos regímenes y diferencia |
| Pearl | `identify` | `treatment`, `outcome`, `criterion`, `adjustment` o `mediator` | Verificación gráfica, fórmula, estratos y probabilidad si procede |
| Halpern | `responsibility` | `context`, `candidate`, `effect` | AC1–AC3, causa efectiva, testigo y responsabilidad |
| NESS | `evaluate` | `candidate`, `effect` | Causa NESS, vías y necesidad en el inventario |
| NESS | `reconstruct` | `candidate`, `effect` | Veredictos por reconstrucción, pasos de cada certificado y lagunas |
| Bayes | `infer` | `hypothesis`, `evidence`, opcional `alternatives` | Priori, posterior, masa de evidencia y verosimilitudes comparables |
| Bayes | `sensitivity` | Lo anterior y `scenarios` | Base y resultados por escenario con diferencias posteriores |
| Bayes | `structure` | `hypothesis`, `reports` | Grafo, fragmentos, tipos de trayectorias y nodos sin CPT |
| Bayes | `evidence_sequence` | `hypothesis`, `evidence`, `sequence` | Actualización exacta por acumulación |
| Bayes | `evidence_sensitivity` | `hypothesis`, `evidence`, `reports` | Posteriores y extremos al variar cada informe |

Los predicados SCM en `query` y `observed` son asignaciones conjuntivas.
`do` y `baseline` asignan variables endógenas. Una fila estructural contiene
`when` con la asignación completa de padres y `then` con el valor resultante.
El prior SCM reutiliza esta estructura con todos los exógenos en cada fila.
En HP, el efecto es una fórmula con un único operador por nodo. Use
`{"eq":{"Y":"1"}}` para un átomo, `not` para negación y listas con
`all` o `any` para conjunción o disyunción. Las condiciones AC que quedan
sin examinar devuelven `null`. Las fórmulas admiten hasta 128 niveles.

En NESS los valores efectivos son booleanos o `null`. Cada mecanismo lleva
`id`, `effect`, `requires`, `law` y `provenance`. El inventario
`complete` declara cobertura para el efecto consultado. Un bloqueo puede
representarse mediante una condición explícita de paso habilitado.
`necessary_across_declared_paths` mide necesidad frente a las vías activas
del inventario. Su valor es `null` si falta cobertura para resolverla.
En Bayes, `then` contiene toda la distribución de la variable dada una
fila de padres. `alternatives` ordena numerador y denominador. Cada entrada
de `scenarios` contiene reemplazos `{node, when, then}`. La red base
permanece fija entre escenarios.

## Identificación, composición y patrones

Para Pearl, `model.observed` contiene dominios de nodos observados,
`latent` enumera los latentes y `parents` declara los padres de cada
nodo. `observational_distribution` usa filas `{when, then}` exhaustivas,
incluidas las masas cero, sobre todos los observables. `treatment` y
`outcome` asignan exactamente un estado de variables distintas. Use
`criterion: "backdoor"` y un arreglo `adjustment`, o
`criterion: "frontdoor"` y un identificador `mediator`. Una fórmula
identificada puede carecer de los datos requeridos para evaluarla.
[Ejemplo de puerta delantera](../examples/pearl-frontdoor.json).

NESS recibe `model.reconstructions`, lista de objetos `{id, model}` que
reutilizan `conditions`, `mechanisms` y `complete`. Cada reconstrucción
declara `roots`. Cada mecanismo agrega un booleano `composable`, que
expresa la estabilidad estipulada para el ámbito de la reconstrucción.
El resultado puede informar `cause`, `not_causal`, `undetermined` o
`underspecified_mechanism`. Un `necessary_across_declared_paths`
nulo señala que no se resolvió esa necesidad. Las lagunas conservan el
identificador de condición o mecanismo.
[Ejemplo de cadena](../examples/ness-chain.json).

Bayes admite `model.idioms` como lista de `{id, kind, roles, provenance}`.
Los roles se asignan a variables declaradas y `provenance` referencia
registros del caso. Los nodos pueden declarar padres adicionales. Para
un destino cubierto por un patrón, el campo `parents` se puede omitir.
Cada CPT se valida contra los padres efectivos. El resultado registra
los arcos y su origen metodológico. Consulte [roles y semántica](fnl.md)
y el [ejemplo de fiabilidad](../examples/bayesian-testimony.json).

## Trazabilidad

Cada registro puede declarar `links` con `{relation, target}`.
`asserted_by` exige un destino fuente. `supports`, `contradicts`,
`about` y `participates_in` referencian registros compatibles.
`reconstruction_id` permite distinguir ejecuciones sobre un mismo
acontecimiento. `lineage` permite asociar elementos y parámetros con
identificadores. Sus claves son punteros JSON RFC 6901 bajo `/model`
o `/parameters`. Cada valor declara `basis`, lista de pares
`{kind, ref}` de tipo `document`, `assertion`, `hypothesis` o
`assumption`, y opcionalmente `depends_on` con otros punteros ya
declarados. Se validan los punteros y tipos de registros y se rechazan
ciclos. El sobre conserva el grafo de dependencias declarado y el
registro documental con el que se resuelve. Desde 0.3.0 se adjuntan la cobertura y la traza de la ejecución.

### Cobertura e invalidación en 0.3.0

`audit_coverage(request)` y `causal --coverage solicitud.json` enumeran las hojas
JSON de `model` y `parameters`, incluidos los contenedores vacíos. Una
entrada cuenta como `individual` si tiene un registro `lineage` en su
puntero exacto. Una entrada agrupada debe aparecer explícitamente en
`lineage_groups[].members`, asociada a un `record` existente.
Se permiten grupos que comparten un supuesto o referencia común. Un
elemento no puede pertenecer a varios grupos, y su registro individual
tiene precedencia. Los vínculos generales en `/model` y `provenance`
no cubren automáticamente elementos descendientes. Cada ficha informa
los tipos de base directos y transitivos. `derived` enlaza a otro
puntero registrado y requiere `derivation` con la operación declarada.
Se comprueban referencias y aciclicidad. Los registros documentales
pueden precisar su ubicación mediante `locator`.

`options.provenance_mode` admite `compatible` (por defecto) y `strict`.
El modo compatible conserva el cálculo histórico y expone las brechas.
El estricto devuelve `insufficient_data` cuando queda una hoja sin
procedencia. El perfil bayesiano nuevo verifica la cobertura de cada
coeficiente de tablas, escenarios y evidencia blanda incluso en el
modo compatible. La cobertura verifica declaraciones y enlaces.
`declared_unverified` indica que el sistema no autentica documentos
ni comprueba la veracidad de una afirmación o de una derivación aportada.

`trace.execution.outputs` conserva etapas y punteros a fuentes,
hipótesis, supuestos, parámetros y artefactos matemáticos. Las aristas
`exact` entre salidas identifican los artefactos usados en una fórmula,
como masa conjunta y masa observada para la posterior. `observed_reads`
registra las búsquedas tabulares instrumentadas, con rutas exactas
para SCM y Bayes. Las dependencias de entrada por salida son
`conservative` y abarcan los requisitos de cálculo y validación que
podrían influir en un resultado revisado. La traza marca `unknown`
si no hay un resultado de cálculo o en la consulta de invalidación
de una ejecución histórica sin traza de resultados.

`affected(result, pointers)` y `affected_by_request(result, revised)`
devuelven punteros de salidas que requieren recálculo. La segunda
función compara la entrada efectiva con la nueva solicitud. Las
inserciones y eliminaciones en listas se registran en el contenedor.
En el primer modo, el llamador debe indicar la lista al modificar sus
posiciones. Se examinan referencias transitivas y cambios estructurales.
NESS identifica también los certificados por reconstrucción. Las
revisiones pueden devolver un conjunto conservador. Se debe ejecutar
la solicitud revisada para conocer la nueva conclusión.

```bash
causal --coverage examples/bayesian-strict.json
causal examples/bayesian-strict.json > /tmp/causal-result.json
causal --changes examples/audit/cpt-change.json /tmp/causal-result.json
causal --revised examples/bayesian-strict.json /tmp/causal-result.json
```

Cada operación de auditoría tiene su propio esquema
[schema de cobertura](../schemas/coverage-v1.schema.json) y
[schema de invalidación](../schemas/affected-v1.schema.json).
El esquema de lote sigue aceptando resultados históricos v1.

## Sobre de resultados

Identifica caso, operación, motor, versión matemática y versión del software.
Incluye `effective_input` con el registro, hipótesis, supuestos y procedencia,
`effective_options` con el presupuesto, `steps`, `domain_of_validity`,
`diagnostics` y `result` con las magnitudes y certificados específicos.
Los estados son `success`, `insufficient_data`, `invalid_model`,
`not_identifiable`, `undefined_operation`, `limit_exceeded` y
`execution_error`. Una razón de verosimilitud puede quedar indefinida o
ser infinita aunque la posterior exista. Para una evidencia conjunta de masa
cero se conserva ese diagnóstico con posterior nula. Un resultado puede
contener la solicitud, por lo que su archivo debe tratarse como los datos
de entrada.

## Interfaz externa reservada

`causal.external.bundle(case_id, runs)` construye y comprueba un lote conforme a
[external-engines-v1](../schemas/external-engines-v1.schema.json) con las
salidas bajo `runs`. Cada salida conserva identificadores, procedencia y
su propio `result`. La API verifica la igualdad de `case_id` entre el lote y cada salida. Las versiones y los contratos propios de
motores externos se negocian entre el consumidor y el proveedor. El
contrato de lote se publica en esta fase como formato de intercambio.
