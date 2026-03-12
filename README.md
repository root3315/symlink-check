# symlink-check

Quick tool to verify symbolic links and check if their targets actually exist.

## Why I wrote this

Ever had a bunch of symlinks in your project and wondered which ones are broken? Or maybe you're cleaning up an old codebase and need to know which links are still valid. This script does that.

## Usage

Check a single symlink:
```bash
python symlink_check.py /path/to/symlink
```

Scan a directory for all symlinks:
```bash
python symlink_check.py -d /path/to/dir
```

Recursive scan:
```bash
python symlink_check.py -d /path/to/dir -r
```

Verbose mode (shows target paths and types):
```bash
python symlink_check.py -d /path/to/dir -v
```

Find only broken symlinks:
```bash
python symlink_check.py --broken /path/to/dir -r
```

Quiet mode (summary only):
```bash
python symlink_check.py -d /path/to/dir --quiet
```

JSON output:
```bash
python symlink_check.py --json /path/to/symlink
python symlink_check.py --json -d /path/to/dir
```

## Output

```
[OK] /path/to/valid/link
[BROKEN] /path/to/broken/link
[SKIP] /path/to/not-a-symlink: Not a symbolic link
```

Exit code is 0 if all symlinks are valid, 1 if any are broken.

## Notes

- Works with both absolute and relative symlinks
- Resolves the full path chain for nested symlinks
- Handles directories, files, and other symlink types
