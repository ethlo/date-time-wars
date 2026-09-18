# Date-time wars

### A micro-benchmark of different date-time parsers and formatters.

## Candidates

* ITU - Internet Time Utility - https://github.com/ethlo/itu (`ITU.parseDateTime`, `ITU.parseLenient`, `ITU.formatUtc*`, `ITU.parseDuration`)
* ITU token parser - `DateTimeParsers.rfc3339()`, ITU's configurable token based parser
* Standard JDK - [java.time.OffsetDateTime](https://docs.oracle.com/javase/8/docs/api/java/time/OffsetDateTime.html),
  a `DateTimeFormatterBuilder` layout with optional parts for lenient parsing, and `java.time.Duration`
* JDK `Instant.parse` - the fastest built-in JDK path for RFC-3339 input
* Google HTTP client - [com.google.api.client.util.DateTime](https://github.com/googleapis/google-http-java-client/blob/main/google-http-client/src/main/java/com/google/api/client/util/DateTime.java)

## Benchmarks

| Method | What | Candidates |
|---|---|---|
| `parse` | strict RFC-3339 date-time → `OffsetDateTime` | ITU, ITU token parser, JDK, JDK Instant, Google |
| `parseLenient` | date-time with optional fraction/offset → candidate's own type | ITU, JDK |
| `formatSeconds` / `formatMillis` / `formatNanos` | `OffsetDateTime` → RFC-3339 UTC string | ITU, JDK |
| `parseDuration` | ISO-8601 duration string → candidate's own duration type | ITU, JDK |
| `formatDuration` | duration → ISO-8601 string | ITU, JDK |

Each candidate is a single `*Candidate` class under `src/main/java/candidates/<id>/` implementing the
interfaces in `common/`; the `*Benchmark` classes next to it are one-liners wiring it into the shared,
JMH-annotated base classes (`ParseBenchmark`, `FormatBenchmark`, ...). To add a candidate, implement the
interfaces you support and add a `*Benchmark` subclass per suite.

## Performance

Your mileage may vary. I've done my best to make sure these tests are as accurate as possible, but please do your own
evaluation.

### Parsing

[JMH result file](results/jmh-result-grouped.json) - [Visualize JMH](https://jmh.morethan.io/?source=https://raw.githubusercontent.com/ethlo/date-time-wars/main/results/jmh-result-grouped.json)

### Environment

Tests performed on a Lenovo P1 G6 laptop:

* Intel(R) Core(TM) i9-13900H
* Ubuntu 23.10
* OpenJDK version 17.0.9

### Run tests yourself

```shell
./bench.sh --quick --parse          # ~1 minute sanity check of the strict date-time parsers
./bench.sh --lenient --format --gc  # lenient parsers + formatters, with allocation stats
./bench.sh --duration               # duration parse/format
./bench.sh --thorough --all         # publishable numbers, all benchmarks
./bench.sh --help                   # all suites, modes, profilers, baseline comparison...
```

Suites: `--parse`, `--lenient`, `--format` (or `--datetime` for all three), `--duration`, `--all`;
they can be combined, or replaced by a raw JMH regex.

Each run writes to `results/<timestamp>-<suite>-<mode>/` (and `results/latest`):

| File | What |
|---|---|
| `report.html` | self-contained page with bar charts (hover for details) and tables |
| `report.md` | markdown tables, ready to paste into a README or PR |
| `report.png` | static chart (needs `matplotlib`) |
| `jmh-result.json` | the raw JMH output |
| `jmh-result-grouped.json` | relabelled/sorted, for [jmh.morethan.io](https://jmh.morethan.io/) |
| `run.properties`, `jmh.log` | environment (CPU, OS, JDK, git rev) and full JMH log |
| `profiles/` | async-profiler flame graphs, when run with `--async` |

To see whether a change helped, compare against a previous run:

```shell
./bench.sh --parse --baseline results/latest
```

The report can also be regenerated from any JMH json file:

```shell
python3 report.py results/latest/jmh-result.json
```
