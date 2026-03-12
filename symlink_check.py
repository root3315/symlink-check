#!/usr/bin/env python3
"""
symlink-check: Verify symbolic links and their targets.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def get_symlink_info(path: Path) -> dict:
    """Gather information about a symbolic link."""
    info = {
        "path": str(path),
        "is_symlink": False,
        "target": None,
        "target_exists": False,
        "target_type": None,
        "is_broken": False,
        "is_absolute": False,
        "error": None
    }

    if not path.exists() and not path.is_symlink():
        info["error"] = "Path does not exist"
        return info

    if not path.is_symlink():
        info["error"] = "Not a symbolic link"
        return info

    info["is_symlink"] = True

    try:
        target = os.readlink(path)
        info["target"] = target
        info["is_absolute"] = os.path.isabs(target)
    except OSError as e:
        info["error"] = f"Cannot read target: {e}"
        return info

    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = path.parent / target_path

    resolved_path = path.resolve()
    info["target_exists"] = resolved_path.exists()
    info["is_broken"] = not resolved_path.exists()

    if info["target_exists"]:
        if resolved_path.is_dir():
            info["target_type"] = "directory"
        elif resolved_path.is_file():
            info["target_type"] = "file"
        elif resolved_path.is_symlink():
            info["target_type"] = "symlink"
        else:
            info["target_type"] = "other"

    return info


def check_single_symlink(path: Path, verbose: bool = False) -> int:
    """Check a single symbolic link and return status code."""
    info = get_symlink_info(path)

    if info["error"]:
        print(f"[ERROR] {path}: {info['error']}")
        return 1

    if not info["is_symlink"]:
        print(f"[SKIP] {path}: {info['error']}")
        return 0

    status = "OK" if not info["is_broken"] else "BROKEN"
    status_marker = "[OK]" if not info["is_broken"] else "[BROKEN]"

    print(f"{status_marker} {path}")

    if verbose:
        target_display = info["target"]
        if info["target_exists"]:
            resolved = path.resolve()
            if str(resolved) != info["target"]:
                target_display += f" -> {resolved}"
        print(f"       Target: {target_display}")
        print(f"       Type: {info['target_type'] or 'unknown'}")
        print(f"       Absolute: {'yes' if info['is_absolute'] else 'no'}")

    return 1 if info["is_broken"] else 0


def scan_directory(directory: Path, recursive: bool = False, verbose: bool = False, json_output: bool = False) -> Tuple[int, int, int]:
    """Scan directory for symbolic links and check them."""
    total = 0
    ok_count = 0
    broken_count = 0

    if recursive:
        symlink_list = list(directory.rglob("*"))
    else:
        symlink_list = list(directory.iterdir())

    symlinks = [p for p in symlink_list if p.is_symlink()]

    if not symlinks:
        if not json_output:
            print(f"No symbolic links found in {directory}")
        return 0, 0, 0

    for link in sorted(symlinks):
        total += 1
        info = get_symlink_info(link)

        if info["is_symlink"]:
            if info["is_broken"]:
                broken_count += 1
                status_marker = "[BROKEN]"
            else:
                ok_count += 1
                status_marker = "[OK]"

            if not json_output:
                print(f"{status_marker} {link}")

            if verbose and info["target"] and not json_output:
                target_display = info["target"]
                if info["target_exists"]:
                    resolved = link.resolve()
                    if str(resolved) != info["target"]:
                        target_display += f" -> {resolved}"
                print(f"       Target: {target_display}")
                print(f"       Type: {info['target_type'] or 'unknown'}")
        else:
            if not json_output:
                print(f"[SKIP] {link}: {info.get('error', 'unknown')}")

    return total, ok_count, broken_count


def find_broken_symlinks(directory: Path, recursive: bool = False) -> List[Path]:
    """Find all broken symbolic links in a directory."""
    broken = []

    if recursive:
        items = list(directory.rglob("*"))
    else:
        items = list(directory.iterdir())

    for item in items:
        if item.is_symlink():
            info = get_symlink_info(item)
            if info["is_symlink"] and info["is_broken"]:
                broken.append(item)

    return broken


def main():
    parser = argparse.ArgumentParser(
        description="Verify symbolic links and their targets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/link          Check a single symlink
  %(prog)s -d /path/to/dir        Scan directory for symlinks
  %(prog)s -d /path -r            Recursively scan directory
  %(prog)s --broken /path         Find broken symlinks only
        """
    )

    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Path to a symbolic link or directory"
    )
    parser.add_argument(
        "-d", "--directory",
        action="store_true",
        help="Scan directory for symbolic links"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively scan subdirectories"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed information about each link"
    )
    parser.add_argument(
        "--broken",
        action="store_true",
        help="Only report broken symbolic links"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output summary statistics"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )

    args = parser.parse_args()

    if not args.path:
        parser.print_help()
        sys.exit(0)

    target = args.path

    if not target.exists() and not target.is_symlink():
        if args.json:
            output = {"error": f"Path does not exist: {str(target)}"}
            print(json.dumps(output, indent=2))
            sys.exit(1)
        print(f"[ERROR] Path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    if args.directory or target.is_dir():
        if not target.is_dir():
            if args.json:
                output = {"error": f"Not a directory: {str(target)}"}
                print(json.dumps(output, indent=2))
                sys.exit(1)
            print(f"[ERROR] Not a directory: {target}", file=sys.stderr)
            sys.exit(1)

        if args.broken:
            broken = find_broken_symlinks(target, args.recursive)
            if args.json:
                output = {
                    "directory": str(target),
                    "recursive": args.recursive,
                    "broken_count": len(broken),
                    "broken_links": [str(link) for link in broken]
                }
                print(json.dumps(output, indent=2))
                sys.exit(0 if not broken else 1)
            
            if not args.quiet:
                for link in broken:
                    print(f"[BROKEN] {link}")
            if not args.quiet:
                print(f"\nFound {len(broken)} broken symbolic link(s)")
            sys.exit(0 if not broken else 1)

        if not args.quiet and not args.json:
            mode = "Recursive " if args.recursive else ""
            print(f"{mode}scanning directory: {target}\n")

        total, ok, broken = scan_directory(target, args.recursive, args.verbose, args.json)

        if args.json:
            output = {
                "directory": str(target),
                "recursive": args.recursive,
                "total": total,
                "ok": ok,
                "broken": broken
            }
            print(json.dumps(output, indent=2))
        elif not args.quiet:
            print(f"\nSummary: {total} total, {ok} OK, {broken} broken")

        sys.exit(0 if broken == 0 else 1)

    elif target.is_symlink() or target.is_file():
        if args.broken:
            info = get_symlink_info(target)
            if args.json:
                output = {
                    "path": str(target),
                    "is_broken": info["is_symlink"] and info["is_broken"]
                }
                print(json.dumps(output, indent=2))
                sys.exit(1 if output["is_broken"] else 0)
            
            if info["is_symlink"] and info["is_broken"]:
                print(f"[BROKEN] {target}")
                sys.exit(1)
            sys.exit(0)

        info = get_symlink_info(target)
        
        if args.json:
            output = {
                "path": str(target),
                "is_symlink": info["is_symlink"],
                "target": info["target"],
                "target_exists": info["target_exists"],
                "target_type": info["target_type"],
                "is_broken": info["is_broken"],
                "is_absolute": info["is_absolute"],
                "error": info["error"]
            }
            print(json.dumps(output, indent=2))
            sys.exit(1 if info["is_broken"] else 0)

        if info["error"]:
            print(f"[ERROR] {target}: {info['error']}")
            sys.exit(1)

        if not info["is_symlink"]:
            print(f"[SKIP] {target}: {info['error']}")
            sys.exit(0)

        status = "OK" if not info["is_broken"] else "BROKEN"
        status_marker = "[OK]" if not info["is_broken"] else "[BROKEN]"

        print(f"{status_marker} {target}")

        if verbose:
            target_display = info["target"]
            if info["target_exists"]:
                resolved = target.resolve()
                if str(resolved) != info["target"]:
                    target_display += f" -> {resolved}"
            print(f"       Target: {target_display}")
            print(f"       Type: {info['target_type'] or 'unknown'}")
            print(f"       Absolute: {'yes' if info['is_absolute'] else 'no'}")

        sys.exit(1 if info["is_broken"] else 0)

    else:
        if args.json:
            output = {"error": f"Invalid path: {str(target)}"}
            print(json.dumps(output, indent=2))
            sys.exit(1)
        print(f"[ERROR] Invalid path: {target}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
