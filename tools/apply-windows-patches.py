#!/usr/bin/env python3
"""Check or apply the ordered Cromite series to a native Windows Chromium checkout."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def git(directory, *args, **kwargs):
    return subprocess.run(["git", "-C", str(directory), *args], check=True, **kwargs)


def source_version(source):
    fields = dict(line.split("=") for line in (source / "chrome/VERSION").read_text().splitlines())
    return ".".join(fields[key] for key in ("MAJOR", "MINOR", "BUILD", "PATCH"))


def copy_inputs(source, scratch, patches):
    # Get both sides of renames. --numstat -z preserves spaces and non-ASCII names.
    series = b"".join(patch.read_bytes() + b"\n" for patch in patches)
    paths = set()
    for direction in ([], ["--reverse"]):
        stats = git(scratch, "apply", "--numstat", "-z", *direction, "-",
                    input=series, stdout=subprocess.PIPE).stdout
        for record in stats.split(b"\0"):
            if record:
                relative = Path(record.split(b"\t", 2)[2].decode("utf-8"))
                if relative.anchor or ".." in relative.parts:
                    raise ValueError(f"Invalid patch path: {relative}")
                paths.add(relative)
    for relative in paths:
        original = source / relative
        if original.is_file() or original.is_symlink():
            destination = scratch / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, destination, follow_symlinks=False)


def apply_one(directory, patch, reverse=False):
    options = ["--reverse"] if reverse else []
    git(directory, "apply", "--binary", "--whitespace=nowarn", *options, str(patch))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "apply"))
    parser.add_argument("source", type=Path, help="path to chromium/src")
    args = parser.parse_args()
    source = args.source.resolve()
    build = Path(__file__).resolve().parents[1] / "build"
    expected = (build / "RELEASE").read_text().strip()
    actual = source_version(source)
    if not (source / ".git").exists():
        parser.error(f"Expected a Git checkout at {source}")
    if expected != actual:
        parser.error(f"Chromium checkout is {actual}, expected {expected}")

    entries = (build / "cromite_patches_list.txt").read_text(encoding="utf-8").splitlines()
    patches = [build / "patches" / name for line in entries
               if (name := line.strip()) and not name.startswith("#")]

    with tempfile.TemporaryDirectory(prefix="cromite-patches-") as temporary:
        scratch = Path(temporary)
        git(scratch, "init", "--quiet")
        copy_inputs(source, scratch, patches)
        for index, patch in enumerate(patches, 1):
            print(f"Checking {index}/{len(patches)}  {patch.name}", flush=True)
            apply_one(scratch, patch)

    if args.mode == "apply":
        applied = []
        try:
            for patch in patches:
                apply_one(source, patch)
                applied.append(patch)
        except subprocess.CalledProcessError:
            for patch in reversed(applied):
                apply_one(source, patch, reverse=True)
            raise
    print(f"{len(patches)} patches {'applied' if args.mode == 'apply' else 'checked'}.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
