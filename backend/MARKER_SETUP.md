# Local Marker PDF processing

PDF uploads now use Marker 1.10.2. The backend renders each PDF once into structured page JSON and Markdown, then indexes page-aware sections, tables, equations, and captions with the existing sentence-transformer and Chroma collection. TXT uploads still use the original text path. Original PDFs, a structured `.marker.json` file, readable `.marker.md`, and extracted image files are stored under `app/data/documents/` and deleted together with the document.

## Provision local models once

Install `backend/requirements.txt` in the backend Python environment. Before disconnecting the desktop from the internet, cache the Marker/Surya model weights once. This is a model download, not an API for parsing documents. Runtime PDF uploads never call a cloud parser or enable Marker's optional `--use_llm` mode.

PowerShell example from the project root:

```powershell
$env:MODEL_CACHE_DIR = (Join-Path (Resolve-Path backend).Path '.models\marker')
$env:USE_TF = '0'
$env:USE_FLAX = '0'
python -c "from marker.models import create_model_dict; create_model_dict(); print('Marker models cached')"
Invoke-WebRequest -Uri 'https://models.datalab.to/artifacts/GoNotoCurrent-Regular.ttf' `
  -OutFile (Join-Path $env:MODEL_CACHE_DIR 'GoNotoCurrent-Regular.ttf')
```

By default the backend reads weights and the font from `backend/.models/marker`; set `MODEL_CACHE_DIR` only if you cache them elsewhere. It checks the cached model manifests and font before initializing Marker. Missing or incomplete assets return HTTP 503 with the missing paths; the upload is removed and no network download is attempted.

The embedding model `sentence-transformers/all-MiniLM-L6-v2` must also be cached locally. The embedding service loads it with `local_files_only=True`. Ollama and its selected chat model must be installed locally as before. Switching embedding models requires rebuilding the existing Chroma index so stored document and query vectors remain compatible.

## Usage and checks

Start the existing FastAPI and React processes as usual, with a local Ollama server. Upload a PDF through the current UI; no frontend configuration change is required. Marker may take longer than pypdf, particularly for scanned books or many pages. One conversion runs at a time to avoid duplicating model memory, and embeddings are still stored in batches of 128 chunks. The 100 MB upload cap remains.

The cached Marker weights and font use about 3.5 GB on this machine. A 100 MB PDF can expand substantially in memory during OCR and image extraction; test representative textbooks on the target desktop before treating the upload cap as a processing capacity guarantee.

```powershell
cd backend
python -m unittest discover -s tests -v
python -m scripts.smoke_marker path\to\sample.pdf
python -m scripts.smoke_pipeline --quiz
```

For a real offline acceptance test, disconnect networking after caching the models. Upload a digital PDF and a scanned PDF, inspect their page numbers and tables in search/chat sources, generate a grounded quiz, then delete each document and verify its PDF, Marker sidecars, images, and Chroma chunks are gone. Marker extracts images for storage; figures without captions or OCR text are not semantically searchable by the current text embedding model.

Validation on this workspace: a one-page digital PDF converted to five text blocks; a generated scanned PDF recovered its two body sentences with OCR. The isolated `smoke_pipeline --quiz` run indexed that scanned page in an ephemeral Chroma collection, returned a page-1 source, received a grounded answer from local Ollama, and generated one sourced quiz question. The backend suite passed 78 tests and the React production build passed. Existing Chroma PDFs retain their earlier pypdf chunks until re-uploaded; the new parser applies to subsequent PDF uploads.
