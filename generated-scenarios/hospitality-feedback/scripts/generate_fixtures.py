"""Generate reproducible synthetic feedback using only catalog-sourced person names."""

import argparse
import csv
import json
from pathlib import Path


def generate(catalog_root: Path, output_root: Path) -> None:
    """Validate catalogs, select exact identities, and write fixtures plus provenance."""
    people_path = catalog_root / "fictitious_people_names.csv"
    company_path = catalog_root / "fictitious_company_names.csv"
    with people_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    expected = [
        "FirstName", "LastName", "FullName", "FirstNameNative",
        "LastNameNative", "FullNameNative", "Gender", "Language",
    ]
    if rows[0] != expected or any(len(row) != len(expected) for row in rows[1:]):
        raise ValueError("Invalid people catalog; do not repair or invent names.")
    with company_path.open(encoding="utf-8-sig", newline="") as handle:
        companies = list(csv.reader(handle))
    if companies[0] != ["Company Name", "Domain Name*"]:
        raise ValueError("Invalid company catalog headers.")
    if companies[21] != ["Margie's Travel", "margiestravel.com"]:
        raise ValueError("Recorded company record changed; review provenance.")
    # Languages describe feedback, not the catalog person's nationality or native language.
    content = [
        ("en", "check-in", "Check-in took forty minutes. The receptionist explained the delay politely."),
        ("es", "check-in", "Esperé treinta minutos para registrarme. El personal fue amable, pero faltaba información."),
        ("fr", "check-in", "L'enregistrement a été rapide et les explications sur le petit-déjeuner étaient claires."),
        ("ja", "check-in", "チェックインに四十分かかりました。遅れの説明がなく、不安でした。"),
        ("en", "housekeeping", "The bathroom was clean, but fresh towels arrived only after a second request."),
        ("es", "housekeeping", "La habitación estaba limpia, pero no repusieron las toallas hasta la segunda llamada."),
        ("fr", "housekeeping", "La salle de bains était propre. Les serviettes demandées sont arrivées en dix minutes."),
        ("ja", "housekeeping", "部屋は清潔でしたが、タオルの追加を二回お願いする必要がありました。"),
        ("en", "breakfast", "Breakfast had fresh fruit, but the coffee queue moved slowly."),
        ("es", "staff", "El equipo de recepción me ayudó con una solicitud y explicó las opciones con paciencia."),
        ("fr", "noise", "Le bruit du couloir m'a réveillé deux fois pendant la nuit."),
        ("ja", "staff", "スタッフは朝食の時間を丁寧に説明してくれました。親切な対応でした。"),
    ]
    fixtures, mapping = [], []
    for index, (language, category, text) in enumerate(content, 1):
        row = dict(zip(expected, rows[index], strict=True))
        if not row["FullName"]:
            raise ValueError(f"Empty name in selected record {index}")
        guest_id = f"G-{index:03d}"
        fixtures.append({
            "feedbackId": f"HF-{index:04d}", "guestId": guest_id, "guestName": row["FullName"],
            "hotelId": "HOTEL-01" if index <= 8 else "HOTEL-02",
            "language": language, "category": category, "text": text,
            "observedAt": f"2026-10-{10 + index // 4:02d}T12:00:00Z",
        })
        mapping.append({
            "guestId": guest_id, "feedbackId": f"HF-{index:04d}",
            "recordNumberExcludingHeader": index, "nameColumn": "FullName", "guestName": row["FullName"],
        })
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "feedback.json").write_text(
        json.dumps(fixtures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    provenance = {
        "synthetic": True, "generationVersion": 1,
        "companyName": "Margie's Travel", "companyDomain": "margiestravel.com",
        "companySlug": "margie-s-travel", "companySource": str(company_path), "companyRecord": 21,
        "rejectedCompanyRecords": [i for i, row in enumerate(companies[1:], 1) if len(row) != 2],
        "peopleSource": str(people_path), "peopleMapping": mapping,
        "note": "All narratives are authored synthetic feedback; no real stays, identities or contact data.",
    }
    (output_root / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(fixtures)} multilingual records and exact person mappings in {output_root}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()
    generate(args.catalog_root, args.output)
