# LLM Agents Benchmark

Automated benchmark runner that tests LLM models on Saotri Bench tasks via [OpenRouter](https://openrouter.ai/).

## Setup

1. Install dependencies (from project root):

```bash
pip install -r requirements.txt
```

2. Create and fill in `agents/.env` (see `.env.example`):

```bash
cp agents/.env.example agents/.env
```

## Usage

All commands run from the **project root** directory.

### List available models

```bash
python -m agents.run_benchmark --list-models
```

### Run all models on all tasks

```bash
python -m agents.run_benchmark
```

### Run specific model tier on a specific task

```bash
python -m agents.run_benchmark --tier strong --task task_00_fizzbuzz
```

Available tiers: `weak`, `medium`, `strong`

### Run all models on one task

```bash
python -m agents.run_benchmark --task task_00_fizzbuzz
```

### Pass API key via CLI (alternative to .env)

```bash
python -m agents.run_benchmark --api-key "sk-or-v1-..."
```

### Quiet mode (less output)

```bash
python -m agents.run_benchmark --quiet
```

## API Key Priority

The script resolves the OpenRouter API key in this order:

1. `--api-key` CLI argument (highest priority)
2. `OPENROUTER_API_KEY` environment variable (auto-loaded from `agents/.env`)

If neither is set, the script exits with an error message.

## Configured Models

| Tier     | Model           | OpenRouter ID                          |
|----------|-----------------|----------------------------------------|
| weak     | Gemma 2 9B      | `google/gemma-2-9b-it`                 |
| medium   | Llama 3.3 70B   | `meta-llama/llama-3.3-70b-instruct`    |
| strong   | Claude Sonnet   | `anthropic/claude-sonnet-4`            |

Models are chosen to show clear capability differences across tiers.

## Reports

Results are saved to `reports/` (gitignored):

```
reports/
  benchmark_report.json          # Full summary across all models and tasks
  task_00_fizzbuzz/
    comparison.json              # Side-by-side comparison for this task
    weak/run_20260207_235146.json
    medium/run_20260207_235213.json
    strong/run_20260207_235224.json
```

### Report structure

**`benchmark_report.json`** — aggregated results:
- Per-task breakdown with each model's performance
- Per-model summary (tasks completed, phase completion rate, tokens, duration)

**`comparison.json`** — per-task model comparison:
- Completion rate, attempts, token usage, phase-by-phase details

**`run_*.json`** — individual run details:
- Model info, task info, phase results, token usage, timestamps

## CLI Options

```
python -m agents.run_benchmark [OPTIONS]

Options:
  --tier {weak,medium,strong}  Run only this model tier (default: all)
  --task TASK                  Task directory name (default: all tasks)
  --tasks-dir PATH             Path to tasks directory (default: ./tasks)
  --reports-dir PATH           Path to reports output (default: ./reports)
  --api-key KEY                OpenRouter API key (or use agents/.env)
  --list-models                List configured models and exit
  --quiet                      Reduce output verbosity
```

## Architecture

```
agents/
  __init__.py          # Package init
  .env                 # API key (gitignored, auto-loaded)
  .env.example         # Template for .env
  config.py            # Model configurations (tiers, IDs, parameters)
  llm_client.py        # OpenRouter HTTP client
  agent.py             # LLM coding agent (prompt building, code extraction)
  bench_runner.py      # Orchestrator (agent + Saotri Bench runner loop)
  reports.py           # Report saving, loading, and summary printing
  run_benchmark.py     # CLI entry point (loads .env via python-dotenv)
```

### How it works

1. `run_benchmark.py` auto-loads `agents/.env` and reads the API key
2. Runner sets up workspace with `problem.md`, `task.json`, `phase.json`
3. Agent reads workspace files, builds a prompt, calls OpenRouter LLM
4. Agent writes generated code to `workspace/solution.py`
5. Runner evaluates the solution, writes `feedback.json`
6. Agent reads feedback, refines solution, writes again
7. Loop continues until all phases pass or attempt limits are reached
8. Results and reports are saved to `reports/`
