# Unofficial LaTeX Template for JACoW Conferences

A minimal, auto-updating LaTeX template for
[JACoW conference](https://github.com/JACoW-org/JACoW_Templates/)
submissions. Unlike the official template, this repository:

- Contains only the necessary LaTeX files (no Word templates or extra bundles)
- Uses a practical directory structure for writing
- Automatically syncs with the official template via GitHub Actions (daily checks)
- Provides a builder script to generate submission-ready files without
  modifying your working source

## Quick Start

1. Clone this repository
2. Open in the devcontainer (or use your own LaTeX installation)
3. Write your paper in the `src/` directory
4. Run `make` to compile
5. Run `make submission` to generate submission-ready files

## Template Structure

```
jacow-latex-template/
├── src/
│ ├── main.tex # Defines paper structure and sections
│ ├── content/ # Section content (one .tex file per section)
│ │ ├── introduction.tex
│ │ └── beam_tests.tex
│ └── figures/ # Images
│   ├── image.png
├── references.bib # Bibliography
├── build_submission.py # Submission builder script
├── .devcontainer/ # Dev container configuration
└── .github/ # GitHub Actions for auto-sync
```

**`src/main.tex`** defines your paper's structure using `\input{}` commands to
  pull content from `src/content/`. This lets you see the overall structure
  without scrolling through content.

**`src/content/XYZ.tex`** contains section content. At least one file per section.

**Figures** go in `src/figures/`. The graphics path is pre-configured, so use
  `\includegraphics{fig_1}` instead of `\includegraphics{src/figures/fig_1}`.

**References** are stored in `src/references.bib`.

## Compilation

### Using the Devcontainer (Recommended)

A devcontainer is provided with TinyTeX and all required packages
pre-installed. Works with [Crib](https://fgrehm.github.io/crib/),
[VSCode](https://code.visualstudio.com/), [Zed](https://zed.dev/), or any
Docker/Podman-compatible tool.

From the devcontainer terminal:
```bash
make
```
This builds `src/main.tex` with `latexmk`, producing `src/main.pdf` and
`src/main.synctex.gz`.

### Using Your Own LaTeX Installation

If you have a working LaTeX setup, compile `src/main.tex` as you normally would.


## Submission

JACoW requires submission files to follow specific naming conventions 
(e.g., `WED1234.pdf`). The `build_submission.py` script generates a 
submission-ready directory with properly named files from your working 
source, without modifying your original files.

### Using the Devcontainer (Recommended)

From the devcontainer terminal:
```bash
make submission
```
This will make a `build` directory with a subdirectory named after the
current git hash.

### With Your Own Python Installation

From the project root run:
```bash
python build_submission.py src/main.tex [<submission_id>] [--build-dir build]
```
`submission_id` is the ID of your contribution (e.g. WED1234).


## Using with Overleaf

1. Clone this repository and rename the origin remote:
   ```bash
   cd jacow-latex-template
   git remote rename origin template
   ```

2. Create a new blank project on Overleaf, then find its Git URL:
   - Go to the Integrations sidebar > Git
   - Copy the URL (looks like `https://git@git.overleaf.com/6a90ae84...`)

3. Add Overleaf as a remote and sync:
   ```bash
   git remote add origin <your-overleaf-git-url>
   git pull origin main --allow-unrelated-histories --rebase=false
   git rm main.tex  # Remove Overleaf's default main.tex
   git commit -m "Remove unused main.tex";
   git push origin main
   ```

4. In Overleaf's compiler settings for this project, set `src/main.tex`
   as the main document.
