"""Download the official BUS-BRA archive and verify its published MD5."""
import hashlib
from pathlib import Path
import urllib.request
import zipfile

URL = 'https://zenodo.org/records/8231412/files/BUSBRA.zip?download=1'
MD5 = '1f8b2be6476d58fc97bfb5e5a1ea9bab'


def main():
    root = Path('data')
    root.mkdir(exist_ok=True)
    archive = root / 'BUSBRA.zip'
    partial = root / 'BUSBRA.zip.part'
    if not archive.exists():
        print('Downloading public, anonymized BUS-BRA data from the official record...')
        try:
            with urllib.request.urlopen(URL, timeout=60) as response, partial.open('wb') as f:
                while chunk := response.read(1024 * 1024):
                    f.write(chunk)
            partial.replace(archive)
        finally:
            partial.unlink(missing_ok=True)
    digest = hashlib.md5(archive.read_bytes()).hexdigest()
    if digest != MD5:
        raise ValueError('Archive checksum mismatch. Remove data/BUSBRA.zip and retry.')
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            target = (root / info.filename).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError('Unsafe archive path')
        z.extractall(root)
    print('Verified and extracted. Next: python audit_data.py --data data/BUSBRA')
    print('Cite Gómez-Flores et al. (2024), DOI 10.1002/mp.16812. Do not republish dataset images.')


if __name__ == '__main__':
    main()
