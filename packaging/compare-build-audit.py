"""Vergleich der tatsächlich installierten Dateien, keine Sicherheitsfreigabe."""
from pathlib import Path
import json
import sys

root = Path(sys.argv[1])
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
inventories = {name: {r['path']: r for r in read(root / name / 'pe-signatures.json')} for name in ('old', 'new')}
before, after = inventories['old'], inventories['new']
common = sorted(before.keys() & after.keys())
changed = [p for p in common if before[p]['sha256'] != after[p]['sha256']]
summary = {
    'installers': {name: read(root / name / 'installer-signature.json') for name in ('old', 'new')},
    'applications': {name: inventories[name].get('Klangwerk.exe') for name in ('old', 'new')},
    'pe_counts': {name: len(inventories[name]) for name in ('old', 'new')},
    'added': sorted(after.keys() - before.keys()), 'removed': sorted(before.keys() - after.keys()),
    'changed': changed,
    'changed_dll_pyd': [p for p in changed if Path(p).suffix.lower() in {'.dll', '.pyd'}],
    'signatures': {name: {status: sum(r['signature_status'] == status for r in inv.values())
                           for status in sorted({r['signature_status'] for r in inv.values()})}
                   for name, inv in inventories.items()},
    'upx_markers': {name: [r['path'] for r in read(root / name / 'pe-imports.json') if r['upx_sections']]
                    for name in ('old', 'new')},
    'python_packages': {name: {k: v for k, v in read(root / name / 'python-modules.json').items() if k != 'modules'}
                        for name in ('old', 'new')},
    'limits': ['Kein Windows-11-Smart-App-Control-Gerätetest.', 'Keine Garantie auf Schadsoftwarefreiheit.',
               'Signaturstatus und Antivirusprüfung ersetzen keine Prüfung der SAC-CodeIntegrity-Ereignisse.'],
}
(root / 'comparison-summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
