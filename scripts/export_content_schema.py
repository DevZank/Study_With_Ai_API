"""Exporta somente o contrato público; o schema de geração com gabaritos é privado."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from study_api.domain.content import PublicDocument

target = ROOT / "docs" / "api" / "content-v1.schema.json"
target.write_text(
    json.dumps(PublicDocument.model_json_schema(), ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print("Contrato público exportado sem gabaritos.")
