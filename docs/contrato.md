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
| Pearl | `identify` | Objeto reservado | Diagnóstico de alcance |
| Halpern | `responsibility` | `context`, `candidate`, `effect` | AC1–AC3, causa efectiva, testigo y responsabilidad |
| NESS | `evaluate` | `candidate`, `effect` | Causa NESS, vías y necesidad en el inventario |
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

Un consumidor futuro puede aceptar un lote conforme a
[external-engines-v1](../schemas/external-engines-v1.schema.json) con las
salidas bajo `runs`. Cada salida conserva identificadores, procedencia y
su propio `result`. El consumidor verificará igualdad de `case_id`
entre el lote y cada salida. Las versiones y los contratos propios de
motores externos se negocian entre el consumidor y el proveedor. El
contrato de lote se publica en esta fase como formato de intercambio.
