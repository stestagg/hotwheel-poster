## Hot Wheels Poster Group Extractor

This repo includes `extract_poster_groups.py`, a script that:

1. Loads a source poster PDF.
2. Disables background/crop optional-content layers (when present, e.g. `BACKGROUND`).
3. Locates each group using the text anchor `MINI COLLECTION`.
4. Computes 3×4 crop bounds from anchor positions.
5. Exports 12 cropped PDFs into an output folder.

### Requirements

- `uv` installed: https://docs.astral.sh/uv/

### Run (uv)

```bash
uv run extract_poster_groups.py posters/HW_Poster_WAVE_1_2024_HiRes-1.pdf \
  --output-dir output/group_pdfs
```

`uv` reads dependencies directly from `extract_poster_groups.py` and creates an isolated environment automatically.

### Optional (pip)

```bash
python -m pip install -r requirements.txt
python extract_poster_groups.py posters/HW_Poster_WAVE_1_2024_HiRes-1.pdf \
  --output-dir output/group_pdfs
```

### Output

For this poster, the script writes 12 files like:

- `group_01_r1c1.pdf`
- ...
- `group_12_r4c3.pdf`

into `output/group_pdfs/`.
