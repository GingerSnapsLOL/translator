# Translator API

A small FastAPI service that translates text between languages using the
[`facebook/nllb-200-distilled-600M`](https://huggingface.co/facebook/nllb-200-distilled-600M)
model from Hugging Face Transformers.

## Endpoints

| Method | Path         | Description                          |
| ------ | ------------ | ------------------------------------ |
| GET    | `/health`    | Liveness/readiness probe             |
| GET    | `/languages` | List supported FLORES-200 languages  |
| POST   | `/translate` | Translate text between two languages |

### Example

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Stasuk is the best full suck developer", "source_lang": "eng_Latn", "target_lang": "ukr_Cyrl"}'
# {"translation": "Привіт світ"}
```

## Configuration

Settings are read from environment variables (or a `.env` file). See
[`.env.example`](./.env.example).

| Variable            | Default                            | Description                     |
| ------------------- | ---------------------------------- | ------------------------------- |
| `MODEL_NAME`        | `facebook/nllb-200-distilled-600M` | Hugging Face model id           |
| `DEVICE`            | `cpu`                              | Torch device (`cpu` / `cuda`)   |
| `API_TITLE`         | `Translator API`                   | OpenAPI title                   |
| `API_VERSION`       | `0.1.0`                            | OpenAPI version                 |
| `LOG_LEVEL`         | `INFO`                             | Root log level                  |
| `MAX_OUTPUT_TOKENS` | `512`                              | Max generated tokens per call   |

## Development

```bash
uv sync                 # install runtime + dev dependencies
uv run uvicorn app.main:app --reload

uv run ruff check .     # lint
uv run mypy app         # type-check
uv run pytest           # tests
```

## Make commands

Common tasks are wrapped in the [`Makefile`](./Makefile):

| Command       | Description                                                              |
| ------------- | ------------------------------------------------------------------------ |
| `make test`   | Run the test suite verbosely (`uv run pytest -v`)                        |
| `make lint`   | Lint with Ruff and type-check with MyPy                                  |
| `make deploy` | Run `lint` and `test`, then build and start the stack (`docker compose up --build -d`) |

## Docker

```bash
docker compose up --build
```

The Hugging Face model cache is persisted in the `hf-cache` named volume so the
weights are downloaded only once.
