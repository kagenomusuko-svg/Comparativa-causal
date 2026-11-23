# Comparativa causal

Cuatro motores matemáticos locales para reconstrucciones estructuradas. Los ejemplos son sintéticos. Requieren Python
3.11 o posterior y usan únicamente la biblioteca estándar en ejecución.

```bash
python -m causal examples/pearl.json
python -m causal examples/pearl-backdoor.json
python -m causal examples/pearl-frontdoor.json
python -m causal examples/halpern.json
python -m causal examples/ness.json
python -m causal examples/ness-chain.json
python -m causal examples/bayesian.json
python -m causal examples/bayesian-testimony.json
python -m pip install '.[test]'
python -m unittest discover -s tests -v
```

La CLI admite `-` para leer desde la entrada estándar. La instalación opcional
con `python -m pip install .` habilita el comando `causal`. El sistema de
construcción usa setuptools.

```python
import json
from pathlib import Path

from causal import execute

request = json.loads(Path("examples/halpern.json").read_text(encoding="utf-8"))
response = execute(request)
assert response["status"] == "success"
assert response["result"]["responsibility"] == "1/2"
```

- [Especificaciones y fuentes](docs/matematicas.md)
- [Contrato JSON, adaptadores e integración externa](docs/contrato.md)
- [Informe de cierre](docs/cierre.md)
