"""Statische PE-Importanalyse, führt keine DLL aus."""
import json
from pathlib import Path
import sys
import pefile
from PyInstaller.archive.readers import CArchiveReader

root = Path(sys.argv[1])
rows = []
for path in sorted(root.rglob('*')):
    if not path.is_file() or path.suffix.lower() not in {'.exe', '.dll', '.pyd'}:
        continue
    with pefile.PE(str(path), fast_load=True) as pe:
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
        rows.append({
            'path': path.relative_to(root).as_posix(),
            'machine': pe.FILE_HEADER.Machine,
            'certificate_table_size': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_SECURITY']].Size,
            'imports': sorted(item.dll.decode('ascii', errors='replace') for item in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])),
            'upx_sections': [s.Name.rstrip(b'\0').decode('ascii', errors='replace') for s in pe.sections if s.Name.upper().startswith(b'UPX')],
        })
Path(sys.argv[2]).write_text(json.dumps(rows, indent=2), encoding='utf-8')
archive = CArchiveReader(str(root / 'Klangwerk.exe'))
pyz_name = next(name for name in archive.toc if name.endswith('.pyz'))
modules = sorted(archive.open_embedded_archive(pyz_name).toc)
Path(sys.argv[2]).with_name('python-modules.json').write_text(json.dumps({
    'modules': modules,
    'legacy_numpy_multiarray': 'numpy.core.multiarray' in modules,
    'contains_pip': any(m == 'pip' or m.startswith('pip.') for m in modules),
    'contains_pytest': any(m == 'pytest' or m.startswith('_pytest') for m in modules),
    'contains_filelock': any(m == 'filelock' or m.startswith('filelock.') for m in modules),
}, indent=2), encoding='utf-8')
