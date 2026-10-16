#!/usr/bin/env python3
"""Verify and stage the separately supplied private US700 handoff; never activate.

The archive's digest is pinned by the public receipt. Only a NEW destination is
allowed. Configuration installation refuses conflicting files and symlinks.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stage(archive, destination):
    receipt=json.loads((ROOT/'docs/handoff/us700-receipt.json').read_bytes())
    if destination.exists() or destination.is_symlink():
        raise ValueError('staging destination must not exist')
    if sha(archive.read_bytes())!=receipt['private_archive_sha256']:
        raise ValueError('private archive hash mismatch')
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers(); names=[m.name for m in members]
        if len(names)!=len(set(names)) or any(not m.isfile() for m in members):
            raise ValueError('archive has duplicates or nonregular files')
        for m in members:
            path=PurePosixPath(m.name)
            if path.is_absolute() or '..' in path.parts or str(path)!=m.name or 'active.json' in path.parts:
                raise ValueError('unsafe archive member')
        inventory=json.load(tar.extractfile('inventory.json'))
        if set(names)!=set(inventory)|{'inventory.json'} or len(inventory)!=receipt['private_file_count']:
            raise ValueError('archive membership differs from receipt')
        for m in members:
            raw=tar.extractfile(m).read()
            if m.name!='inventory.json' and sha(raw)!=inventory[m.name]:
                raise ValueError('archive member hash mismatch')
        # All validation precedes any extraction or checkout write.
        configs=[]
        for name in inventory:
            for prefix,folder in (('main-config/',ROOT/'backend/app/us_valuation/config'),
                                  ('parser-config/',ROOT/'us_refresh_parser/backend/app/us_valuation/config')):
                if name.startswith(prefix):
                    target=folder/name[len(prefix):]
                    if target.is_symlink() or any(p.is_symlink() for p in target.parents):
                        raise ValueError('configuration symlink is not allowed')
                    if target.exists() and sha(target.read_bytes())!=inventory[name]:
                        raise ValueError('configuration conflict; use a fresh checkout')
                    configs.append((name,target))
        destination.mkdir(parents=True,mode=0o700)
        for m in members:
            target=destination/m.name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            target.write_bytes(tar.extractfile(m).read());target.chmod(0o600)
        for name,target in configs:
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((destination/name).read_bytes());target.chmod(0o600)
    print(json.dumps({'staged':str(destination),'catalog_version':receipt['catalog_version'],
        'private_files':len(inventory),'active_pointer_created':False,'SEC_job_started':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args();stage(args.archive.resolve(),args.destination.absolute())
