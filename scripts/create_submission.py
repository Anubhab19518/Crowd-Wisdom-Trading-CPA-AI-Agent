"""Create submission ZIP containing source, README, samples, reports, and other key files."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'submission_package.zip'
INCLUDE = [
    'src',
    'samples',
    'reports',
    'README.md',
    'requirements.txt',
    'Dockerfile',
    '.env.example',
    'scripts',
    '.github',
    'tests',
    'run_demo.py',
    'hermes_task.py',
]

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in INCLUDE:
        path = ROOT / p
        if not path.exists():
            continue
        if path.is_file():
            z.write(path, arcname=path.name)
        else:
            for file in path.rglob('*'):
                if file.is_file():
                    # skip common unwanted directories
                    if any(part.startswith('.venv') for part in file.parts):
                        continue
                    z.write(file, arcname=str(file.relative_to(ROOT)))
print('Created', OUT)
