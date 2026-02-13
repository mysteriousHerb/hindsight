# Retain Performance Benchmark - Key Findings

## Test Setup
- **Dataset**: 10 documents from iota-docs (15,759 characters total)
- **Average doc size**: 1,576 characters
- **LLM**: groq/openai/gpt-oss-20b

## Results Comparison

| Metric | HTTP Mode | In-Memory Mode | Difference |
|--------|-----------|----------------|------------|
| **Duration** | 46.215s | 8.079s | **5.7x faster** |
| **Throughput** | 341 chars/sec | 1,951 chars/sec | 5.7x |
| **Docs/Second** | 0.22 | 1.24 | 5.6x |
| | | | |
| **Input Tokens** | 42,217 | 33,120 | 21.5% fewer |
| **Output Tokens** | 72,626 | 22,456 | **69.1% fewer!** |
| **Total Tokens** | 114,843 | 55,576 | 51.6% fewer |
| **Tokens/Second** | 2,485 | 6,879 | 2.8x faster |

## Critical Finding

**The HTTP path uses 3.2x more output tokens (72k vs 22k)** and takes 5.7x longer.

This is NOT just HTTP overhead - there's a fundamental difference in how the requests are being processed.

### From HTTP Server Logs (when available):
```
RETAIN_BATCH START: iota-perf-test
Batch size: 10 content items, 15,759 chars
============================================================
[1] Extract facts: 54 facts, 11 chunks from 10 contents in 43.361s
```

The LLM call details showed:
- scope=retain_extract_facts
- input_tokens=3,700
- output_tokens=39,076 (10.56x ratio!)
- time=43.326s

## Hypothesis

The massive difference in output tokens (72k HTTP vs 22k in-memory) suggests:

1. **Potential Double Processing**: HTTP path might be processing documents individually AND as batch
2. **Extension/Hook Overhead**: HTTP server might have validation or extension hooks doing extra LLM calls
3. **Configuration Difference**: The HTTP server (running from different workspace) may have different retain settings
4. **Serialization Issues**: Metadata or context being added in HTTP path causing redundant processing

## Recommendations

1. **Check for extensions**: Look for pre_retain/post_retain hooks that might trigger extra LLM calls
2. **Verify batch processing**: Ensure HTTP path uses true batching, not sequential processing
3. **Compare configurations**: Check if HTTP server has different retain_mode or chunking settings
4. **Add detailed logging**: Track each LLM call to identify where extra tokens are coming from
5. **Profile the HTTP path**: Add timing breakpoints to identify bottleneck

## Benchmark Usage

```bash
# HTTP mode (default)
./scripts/benchmarks/run-retain-perf.sh \
    --document ~/Documents/iota-docs/ \
    --bank-id test

# In-memory mode (bypass HTTP)
./scripts/benchmarks/run-retain-perf.sh \
    --document ~/Documents/iota-docs/ \
    --bank-id test \
    --in-memory
```

## Next Steps

- [ ] Investigate why HTTP path generates 3.2x more output tokens
- [ ] Check if HTTP server has different configuration than in-memory
- [ ] Add LLM call tracing to both paths for direct comparison
- [ ] Verify batch processing implementation in HTTP endpoint
