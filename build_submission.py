#!/usr/bin/env python3
r"""
Build a flattened LaTeX conference submission.

Usage:
    python build_submission.py <main.tex> [<submission_id>] [--build-dir build]

Output:
    build/<git_hash>/<submission_id>.tex
    build/<git_hash>/figures/<submission_id>_<n>.<ext>
    build/<git_hash>/<submission_id>_<n>.bib
    build/<git_hash>/<required_files>
    build/<git_hash>/Makefile
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# List of files that should be copied into every build directory.
# Paths are relative to the project root (the directory containing main.tex).
REQUIRED_FILES = [
    "jacow.cls",
    "jacow.bbx",
    "jacow.cbx",
    "jacow.dbx",
]

# Common image extensions to try when \includegraphics omits the extension.
IMAGE_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"]
# ---------------------------------------------------------------------------


def get_git_hash(repo_dir: Path) -> str:
    """Return the current git HEAD hash, or 'unknown' if not available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def read_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def resolve_tex_path(base_dir: Path, rel_path: str) -> Path:
    r"""Resolve a path from \input or \include, adding .tex if needed."""
    p = (base_dir / rel_path).resolve()
    if p.suffix == "":
        p = p.with_suffix(".tex")
    return p


def extract_graphicspath(content: str) -> list:
    r"""
    Extract all paths from \graphicspath{{dir1/}{dir2/}...} commands.
    Handles one level of nested braces.
    """
    paths = []
    # Match \graphicspath{ ... } where the contents may contain nested { ... }
    pattern = re.compile(r"\\graphicspath\{((?:[^{}]|\{[^}]*\})*)\}")
    for match in pattern.finditer(content):
        inner = match.group(1)
        paths.extend(p.strip() for p in re.findall(r"\{([^}]*)\}", inner))
    return paths


def find_file_with_extension(path: Path) -> Optional[Path]:
    """
    If the given path does not exist and has no extension, try common image
    extensions. Return the first match, or None if nothing is found.
    """
    if path.exists():
        return path

    if path.suffix:
        return None

    for ext in IMAGE_EXTENSIONS:
        candidate = path.with_suffix(ext)
        if candidate.exists():
            return candidate

    return None


def resolve_figure_path(original_path: str, base_dir: Path, state: dict) -> Optional[Path]:
    r"""
    Resolve a figure path using, in order:
      1. The directory of the file containing the \includegraphics
      2. The directories listed in \graphicspath
      3. The project root directory
      4. As an absolute path
    """
    candidates = [base_dir]
    candidates.extend(state.get("graphicspath_dirs", []))
    candidates.append(state["root_dir"])

    for search_dir in candidates:
        candidate = (search_dir / original_path).resolve()
        found = find_file_with_extension(candidate)
        if found is not None:
            return found

    # Final fallback: absolute path
    candidate = Path(original_path).resolve()
    return find_file_with_extension(candidate)


def process_figures(content: str, base_dir: Path, build_dir: Path,
                    submission_id: str, state: dict, verbose: bool) -> str:
    r"""
    Copy figures to build/<hash>/figures/, rename them, and update
    \includegraphics paths (including the \includegraphics* variant)
    to use the new names via \graphicspath.
    """
    fig_dir = build_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Match \includegraphics or \includegraphics*, optional [...], and {...}
    img_pattern = re.compile(r"\\includegraphics(\*?)(\[[^\]]*\])?\{([^}]+)\}")

    def repl(match):
        asterisk = match.group(1) or ""
        options = match.group(2) or ""
        original_path = match.group(3).strip()

        src_path = resolve_figure_path(original_path, base_dir, state)
        if src_path is None:
            print(f"Warning: figure not found: {original_path} "
                  f"(tried base_dir={base_dir}, graphicspath={state.get('graphicspath_dirs', [])}, "
                  f"root_dir={state['root_dir']})",
                  file=sys.stderr)
            return match.group(0)

        ext = src_path.suffix
        idx = state["fig_index"]
        state["fig_index"] = idx + 1

        new_name = f"{submission_id}_{idx}{ext}"
        dst_path = fig_dir / new_name
        shutil.copy2(src_path, dst_path)

        if verbose:
            print(f"  Copied figure: {src_path} -> {dst_path}")

        # Path is relative to the build root; \graphicspath will resolve it
        return f"\\includegraphics{asterisk}{options}{{{new_name}}}"

    return img_pattern.sub(repl, content)


def flatten_tex(content: str, base_dir: Path, build_dir: Path,
                submission_id: str, state: dict, verbose: bool) -> str:
    r"""
    Recursively replace \input{...} and \include{...} with file contents.

    Figures are processed for each file using that file's directory and the
    project's \graphicspath as search paths. Cycles are detected and reported.
    """
    # Process figures in this file's content first
    content = process_figures(content, base_dir, build_dir, submission_id, state, verbose)

    input_pattern = re.compile(r"\\(input|include)\{([^}]+)\}")

    def repl(match):
        cmd = match.group(1)
        file_arg = match.group(2).strip()
        file_path = resolve_tex_path(base_dir, file_arg)

        if not file_path.exists():
            print(f"Warning: {cmd} file not found: {file_path}", file=sys.stderr)
            return match.group(0)

        # Cycle detection
        canonical = file_path.resolve()
        if canonical in state["seen_tex"]:
            print(f"Warning: cyclic {cmd} detected, skipping: {canonical}",
                  file=sys.stderr)
            return f"% skipped cyclic {cmd}: {file_arg}\n"
        state["seen_tex"].add(canonical)

        if verbose:
            print(f"  Flattening {cmd}: {file_path}")

        new_content = read_file(file_path)
        flattened = flatten_tex(
            new_content, file_path.parent, build_dir, submission_id, state, verbose
        )

        state["seen_tex"].discard(canonical)
        return flattened

    return input_pattern.sub(repl, content)


def ensure_graphicspath(content: str) -> str:
    r"""
    Ensure the document contains \graphicspath{{figures/}}.
    If one already exists, replace it; otherwise insert it after \documentclass.
    """
    pattern = re.compile(r"\\graphicspath\{\{[^}]+\}\}")

    if pattern.search(content):
        return pattern.sub(r"\\graphicspath{{figures/}}", content)

    # Insert after \documentclass{...}
    docclass_pattern = re.compile(r"(\\documentclass(?:\[[^\]]*\])?\{[^}]+\})")
    match = docclass_pattern.search(content)
    if match:
        insert_pos = match.end()
        return (
            content[:insert_pos]
            + "\n\\graphicspath{{figures/}}\n"
            + content[insert_pos:]
        )

    # Fallback: prepend to the start of the file
    return "\\graphicspath{{figures/}}\n" + content


def process_bibfiles(content: str, build_dir: Path, submission_id: str,
                     state: dict, verbose: bool) -> str:
    r"""
    Copy .bib files referenced by \addbibresource into the build directory,
    rename them, and update the LaTeX source to use the new names.
    """
    bib_pattern = re.compile(r"\\addbibresource(\[[^\]]*\])?\{([^}]+)\}")

    def repl(match):
        options = match.group(1) or ""
        bib_arg = match.group(2).strip()

        # \addbibresource can take a comma-separated list
        bib_files = [b.strip() for b in bib_arg.split(",")]
        new_names = []

        for bf in bib_files:
            if not bf.endswith(".bib"):
                bf += ".bib"

            src_path = (Path(state["root_dir"]) / bf).resolve()
            if not src_path.exists():
                print(f"Warning: bib file not found: {bf}", file=sys.stderr)
                new_names.append(bf)
                continue

            idx = state["bib_index"]
            state["bib_index"] = idx + 1

            new_name = f"{submission_id}_{idx}.bib"
            dst_path = build_dir / new_name
            shutil.copy2(src_path, dst_path)
            new_names.append(new_name)

            if verbose:
                print(f"  Copied bib: {src_path} -> {dst_path}")

        return f"\\addbibresource{options}{{{','.join(new_names)}}}"

    return bib_pattern.sub(repl, content)


def copy_required_files(build_dir: Path, root_dir: Path, verbose: bool) -> None:
    """Copy required files into the build directory."""
    for rel_path in REQUIRED_FILES:
        src_path = (root_dir / rel_path).resolve()
        if not src_path.exists():
            print(f"Warning: required file not found: {src_path}", file=sys.stderr)
            continue

        dst_path = build_dir / src_path.name
        shutil.copy2(src_path, dst_path)

        if verbose:
            print(f"  Copied required file: {src_path} -> {dst_path}")


def generate_makefile(build_dir: Path, submission_id: str) -> None:
    """Generate a Makefile in the build directory to compile the submission."""
    makefile_content = f"""\
.PHONY: default clean

default:
\tmkdir -p temp
\tpdflatex -synctex=1 -interaction=nonstopmode -output-directory=temp -aux-directory=temp {submission_id}
\tbiber temp/{submission_id}
\tpdflatex -synctex=1 -interaction=nonstopmode -output-directory=temp -aux-directory=temp {submission_id}
\tpdflatex -synctex=1 -interaction=nonstopmode -output-directory=temp -aux-directory=temp {submission_id}
\tcp temp/{submission_id}.pdf .

clean:
\trm -rf temp
\trm -f {submission_id}.pdf
"""
    write_file(build_dir / "Makefile", makefile_content)


def ask_yes_no(question: str) -> bool:
    """Prompt the user with a yes/no question and return True only if they answer yes."""
    while True:
        answer = input(f"{question} (yes/no): ").strip().lower()
        if answer in {"yes", "y"}:
            return True
        if answer in {"no", "n"}:
            return False
        print("Please answer 'yes' or 'no'.")


def run_pre_build_checks() -> bool:
    """Run the required manual checks before building the submission."""
    print("\n=== Pre-build manual checks ===\n")

    checks = [
        "Have you manually checked for any special indicators, like # and ? symbols, which need to be replaced?",
        "Have you manually removed all unnecessary comments from the source .tex files?",
    ]

    for question in checks:
        if not ask_yes_no(question):
            print("\nBuild cancelled: not all manual checks were confirmed.")
            return False

    print("\nAll manual checks confirmed. Proceeding with build...\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Flatten a LaTeX project into a conference submission."
    )
    parser.add_argument("main_tex", help="Path to the main .tex file")
    parser.add_argument(
        "submission_id",
        nargs="?",
        help="Conference submission ID, e.g. WED112 (prompted if omitted)",
    )
    parser.add_argument(
        "--build-dir", default="build", help="Top-level build directory (default: build)"
    )
    parser.add_argument(
        "--no-git", action="store_true", help="Do not include git hash in the build path"
    )
    parser.add_argument(
        "--skip-checks", action="store_true", help="Skip the manual pre-build checks"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print detailed processing information"
    )
    args = parser.parse_args()

    # Prompt for submission ID if not provided
    if args.submission_id is None:
        args.submission_id = input("Enter submission ID (e.g. WED112): ").strip()
        if not args.submission_id:
            print("Error: submission ID is required.", file=sys.stderr)
            sys.exit(1)

    # Run pre-build checks unless explicitly skipped
    if not args.skip_checks:
        if not run_pre_build_checks():
            sys.exit(1)

    main_tex = Path(args.main_tex).resolve()
    if not main_tex.exists():
        print(f"Error: main tex file not found: {main_tex}", file=sys.stderr)
        sys.exit(1)

    root_dir = main_tex.parent
    git_hash = "nogit" if args.no_git else get_git_hash(root_dir)
    build_dir = Path(args.build_dir) / git_hash
    build_dir.mkdir(parents=True, exist_ok=True)

    # Read main.tex and extract \graphicspath before flattening
    main_content = read_file(main_tex)
    graphicspath_dirs = []
    for gp in extract_graphicspath(main_content):
        gp_path = (root_dir / gp).resolve()
        if gp_path.is_dir():
            graphicspath_dirs.append(gp_path)

    state = {
        "root_dir": root_dir,
        "graphicspath_dirs": graphicspath_dirs,
        "seen_tex": {main_tex.resolve()},
        "fig_index": 0,
        "bib_index": 0,
    }

    if args.verbose:
        print(f"Project root: {root_dir}")
        print(f"Build directory: {build_dir}")
        print(f"Graphicspath directories: {graphicspath_dirs}")
        print("Flattening and processing figures...")

    # 1. Flatten \input and \include recursively, processing figures as we go
    content = flatten_tex(main_content, root_dir, build_dir, args.submission_id, state, args.verbose)

    # 2. Ensure \graphicspath is set to figures/
    content = ensure_graphicspath(content)

    # 3. Copy/rename bib files and update \addbibresource
    if args.verbose:
        print("Processing bibliography files...")
    content = process_bibfiles(content, build_dir, args.submission_id, state, args.verbose)

    # 4. Copy required files into the build directory
    if args.verbose:
        print("Copying required files...")
    copy_required_files(build_dir, root_dir, args.verbose)

    # 5. Write the final submission file
    output_tex = build_dir / f"{args.submission_id}.tex"
    write_file(output_tex, content)

    # 6. Generate Makefile
    generate_makefile(build_dir, args.submission_id)

    print(f"\nSubmission built successfully:")
    print(f"  {output_tex}")
    print(f"  Figures: {build_dir / 'figures'}")
    print(f"  Bib files: {build_dir}")
    print(f"  Required files: {build_dir}")
    print(f"  Makefile: {build_dir / 'Makefile'}")


if __name__ == "__main__":
    main()
