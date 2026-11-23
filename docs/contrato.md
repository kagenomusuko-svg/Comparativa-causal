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
los arcos y su origen metodológico. Consulte [roles y semántica](matematicas.md)
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
registro documental con el que se resuelve. La traza tiene granularidad
de entrada declarada. No infiere todas las dependencias semánticas
mínimas del resultado ni obliga a documentar parámetros omitidos.

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
