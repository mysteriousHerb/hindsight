# Performance Benchmarks

Performance benchmarks for measuring the throughput and latency of individual Hindsight operations.

## Retain Performance Benchmark

Measures the performance of the retain operation by:
- Loading a document from a file
- Sending it to the retain endpoint via HTTP
- Measuring time taken and token usage
- Reporting performance metrics

### Prerequisites

1. **Start the API server**:
   ```bash
   ./scripts/dev/start-api.sh
   ```

2. **Verify server is running**:
   ```bash
   curl http://localhost:8000/health
   ```

### Usage

#### Using the Shell Script (Recommended)

```bash
# Basic usage with sample document
./scripts/benchmarks/run-retain-perf.sh \
    --document hindsight-dev/benchmarks/perf/test_data/sample_document.txt

# With custom bank ID
./scripts/benchmarks/run-retain-perf.sh \
    --document ./my_document.txt \
    --bank-id my-test-bank

# Save results to JSON file
./scripts/benchmarks/run-retain-perf.sh \
    --document ./my_document.txt \
    --bank-id my-test-bank \
    --output results/retain_perf_$(date +%Y%m%d_%H%M%S).json

# With custom API URL (if server is on different port)
./scripts/benchmarks/run-retain-perf.sh \
    --document ./my_document.txt \
    --api-url http://localhost:9000
```

#### Using Python Directly

```bash
# Basic usage
uv run python hindsight-dev/benchmarks/perf/retain_perf.py \
    --document hindsight-dev/benchmarks/perf/test_data/sample_document.txt \
    --bank-id perf-test

# With all options
uv run python hindsight-dev/benchmarks/perf/retain_perf.py \
    --document ./my_document.txt \
    --bank-id my-test-bank \
    --context "Performance test run" \
    --api-url http://localhost:8000 \
    --timeout 300 \
    --output results/retain_perf.json
```

### Output

The benchmark displays results in a formatted table showing:
- Content length (characters)
- Duration (seconds)
- Throughput (chars/second)
- Token usage (input, output, total)
- Tokens per second

Example output:
```
┌─────────────────────────────────────────────────────┐
│    Retain Performance Benchmark Results             │
├──────────────────────┬──────────────────────────────┤
│ Metric               │ Value                        │
├──────────────────────┼──────────────────────────────┤
│ Bank ID              │ perf-test                    │
│ Content Length       │ 3,456 chars                  │
│                      │                              │
│ Duration             │ 2.145s                       │
│ Throughput           │ 1611 chars/sec               │
│                      │                              │
│ Input Tokens         │ 1,234                        │
│ Output Tokens        │ 456                          │
│ Total Tokens         │ 1,690                        │
│ Tokens/Second        │ 787.9                        │
└──────────────────────┴──────────────────────────────┘
```

### JSON Output Format

When using `--output`, results are saved in JSON format:

```json
{
  "bank_id": "perf-test",
  "document_path": "./my_document.txt",
  "content_length": 3456,
  "duration_seconds": 2.145,
  "chars_per_second": 1610.95,
  "usage": {
    "input_tokens": 1234,
    "output_tokens": 456,
    "total_tokens": 1690
  },
  "tokens_per_second": 787.9
}
```

### Test Data

Sample test documents are provided in `test_data/`:
- `sample_document.txt`: ~3.5KB technical document with various entity types

You can also use your own documents for testing.

### Environment Variables

The shell script supports environment variables:

```bash
export DOCUMENT=./my_document.txt
export BANK_ID=my-test-bank
export API_URL=http://localhost:8000
export OUTPUT=results/retain_perf.json

./scripts/benchmarks/run-retain-perf.sh
```

### Notes

- The benchmark uses HTTP directly (not the Python client SDK) for accurate timing
- Token usage is only available for synchronous operations
- The server must be running before executing the benchmark
- Large documents may require increasing the timeout (default: 300s)
