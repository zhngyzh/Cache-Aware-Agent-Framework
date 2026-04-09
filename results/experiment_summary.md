# Experiment Summary

## execution_enabled

| Scenario | Hit Rate | Delta vs Baseline | Cost | Delta Cost | Cache Hit Tokens | Cache Miss Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| execution_enabled / Baseline | 85.58% | +0.00% | $0.0188 | $+0.0000 | 49,984 | 8,421 |
| execution_enabled / 2. Dynamic Tool Add/Remove | 66.81% | -18.77% | $0.0288 | $+0.0100 | 38,912 | 19,330 |
| execution_enabled / 3. Unstable Tool Order | 63.00% | -22.58% | $0.0325 | $+0.0138 | 38,016 | 22,323 |
| execution_enabled / 5. Non-Deterministic Serialization | 12.36% | -73.23% | $0.0585 | $+0.0397 | 7,296 | 51,755 |

Key takeaway: **execution_enabled / 5. Non-Deterministic Serialization** shows the largest drop in this track.

## schema_only

| Scenario | Hit Rate | Delta vs Baseline | Cost | Delta Cost | Cache Hit Tokens | Cache Miss Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| schema_only / Baseline | 92.56% | +0.00% | $0.0063 | $+0.0000 | 5,248 | 422 |
| schema_only / 1. Timestamp in Static Section | 78.03% | -14.52% | $0.0059 | $-0.0005 | 3,904 | 1,099 |
| schema_only / 4. Modify Message History | 32.99% | -59.57% | $0.0044 | $-0.0019 | 960 | 1,950 |
| schema_only / 6. Model Switch Mid-Session | 85.95% | -6.61% | $0.0090 | $+0.0026 | 5,120 | 837 |

Key takeaway: **schema_only / 4. Modify Message History** shows the largest drop in this track.

