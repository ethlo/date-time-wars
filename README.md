# Date-time wars

### A micro-benchmark of different date-time parsers and formatters.

**[» Latest benchmark report](https://ethlo.github.io/date-time-wars/)**

## Candidates

* ITU - Internet Time Utility - https://github.com/ethlo/itu (`ITU.parseDateTime`, `ITU.parseLenient`, `ITU.formatUtc*`, `ITU.parseDuration`)
* ITU configurable - `ConfigurableDateTimeParser` with an explicit token layout (`yyyy-MM-ddTHH:mm:ss.fff+offset`)
* ITU (hours) - ITU duration formatting clamped to hours via `normalized(DurationUnit.HOURS)`, so it
  decomposes a duration the same way `java.time.Duration.toString()` does. ITU's default `normalized()`
  renders with the largest units available and emits weeks and days, which the JDK never does, so the two
  are not directly comparable without the clamp
* Standard JDK - [java.time.OffsetDateTime](https://docs.oracle.com/javase/8/docs/api/java/time/OffsetDateTime.html),
  a `DateTimeFormatterBuilder` layout with optional parts for lenient parsing, and `java.time.Duration`
* JDK `Instant.parse` - the fastest built-in JDK path for RFC-3339 input
* Google HTTP client - [com.google.api.client.util.DateTime](https://github.com/googleapis/google-http-java-client/blob/main/google-http-client/src/main/java/com/google/api/client/util/DateTime.java)

## Benchmarks

| Method | What | Candidates |
|---|---|---|
| `parse` | strict RFC-3339 date-time → `OffsetDateTime` | ITU, ITU configurable (fractional inputs only), JDK, JDK Instant, Google |
| `parseLenient` | date-time with optional fraction/offset → candidate's own type | ITU, JDK |
| `formatSeconds` / `formatMillis` / `formatNanos` | `OffsetDateTime` → RFC-3339 UTC string | ITU, JDK |
| `parseDuration` | ISO-8601 duration string → candidate's own duration type | ITU, JDK |
| `formatDuration` | duration → ISO-8601 string | ITU, ITU (hours), JDK |

Each candidate is a single `*Candidate` class under `src/main/java/candidates/<id>/` implementing the
interfaces in `common/`; the `*Benchmark` classes next to it are one-liners wiring it into the shared,
JMH-annotated base classes (`ParseBenchmark`, `FormatBenchmark`, ...). To add a candidate, implement the
interfaces you support and add a `*Benchmark` subclass per suite.

## Running the benchmarks

`bench.sh` wraps the shaded JMH jar: it picks the benchmark set, runs it with consistent iteration settings,
records the environment, and generates a report. It builds `target/date-time-wars.jar` automatically if it is
missing.

```shell
./bench.sh                           # everything, normal mode (~10 min)
./bench.sh --quick --duration        # ~1 min smoke run of the duration suite
./bench.sh --lenient --format --gc   # lenient parsers + formatters, with allocation stats
./bench.sh --thorough --all --async  # publishable numbers + flame graphs (~1h20m)
./bench.sh --list                    # which benchmarks exist
./bench.sh --help                    # every option
```

### Suites

Which benchmarks to run. They combine freely, and default to `--all`.

| Flag | Benchmarks | Combos |
|---|---|---|
| `--parse` | strict date-time parsers | 14 |
| `--lenient` | lenient date-time parsers | 6 |
| `--format` | date-time formatters | 6 |
| `--datetime` | the three above | 26 |
| `--duration` | duration parse + format | 10 |
| `--all` | everything (default) | 36 |
| `<regex>` | a raw JMH benchmark regex, e.g. `'itu.*parse'` | |

"Combos" is benchmark methods × `@Param` values, which is what actually determines run time — each one is a
separate JMH fork.

### Modes

How long to run. Per-combo times are measured on the reference machine below.

| Mode | JMH settings | Per combo | `--all` |
|---|---|---|---|
| `--quick` | 1 fork, 2×1s warmup, 3×1s measure | ~5s | ~3 min |
| `--normal` (default) | 1 fork, 3×2s warmup, 5×2s measure | ~16s | ~10 min |
| `--thorough` | 3 forks, 5×3s warmup, 10×3s measure | ~2m20s | ~1h 20m |

Use `--quick` to sanity-check a change and `--thorough` for anything you intend to publish; `--quick` numbers
are usually within a few percent but the error bars are wide enough to hide a small regression.

### Profiling

| Flag | What |
|---|---|
| `--gc` | JMH gc profiler - allocation rate and bytes per operation |
| `--async [PATH]` | async-profiler flame graphs into `profiles/`. `PATH` is `libasyncProfiler.so`; defaults to `$ASYNC_PROFILER_LIB`, then a lookup under `~/Downloads`, `/opt` and `/usr/local` |
| `--async-event EV` | async-profiler event: `cpu` (default), `alloc`, `wall`, `lock` |

### Output

Each run writes to `results/<timestamp>-<suite>-<mode>[-<name>]/`, and `results/latest` is repointed at it as
a symlink.

| File | What |
|---|---|
| `report.html` | self-contained page with bar charts (hover for details) and tables |
| `report.md` | markdown tables, ready to paste into a README or PR |
| `report.png` | static chart (needs `matplotlib`) |
| `summary.md` | one headline ITU-vs-JDK row per method |
| `summary.png` | compact speed-up chart, transparent so it reads on light and dark |
| `jmh-result.json` | the raw JMH output, including `jdkVersion` and `vmVersion` |
| `jmh-result-grouped.json` | relabelled/sorted, for [jmh.morethan.io](https://jmh.morethan.io/) |
| `run.properties` | environment and settings: CPU, OS, JDK, git rev, suite, mode, iteration args, elapsed |
| `jmh.log` | full JMH console output |
| `profiles/` | async-profiler flame graphs, when run with `--async` |

`results/` is gitignored, so runs stay local until you publish one.

### Publishing

`--publish` copies the run's `report.html` to `docs/index.html` and stages it. GitHub Pages serves that
directory at <https://ethlo.github.io/date-time-wars/>, which is where the ITU README links.

```shell
./bench.sh --thorough --all --publish
git commit -m "Update benchmark report" && git push
```

The ITU README keeps its performance table between `BENCH:START`/`BENCH:END` markers, which `report.py`
rewrites in place, so the numbers there never drift from a published run:

```shell
python3 report.py results/latest/jmh-result.json --readme ../itu/README.md
```

Its chart is hotlinked straight from Pages (`summary.png`), so publishing a run updates it with no commit
on the ITU side.

Use `--thorough` for anything you publish. The report records the CPU, OS, JDK and git revision behind the
numbers, so a published run stays traceable.

### Comparing runs

To see whether a change helped, run against a previous result directory (or a `jmh-result.json` directly).
The report then gains a `vs baseline` column, matched per candidate and scenario.

```shell
./bench.sh --duration --baseline results/latest
```

Naming a run with `-n` makes it easier to find later, and the label shows up in the report:

```shell
./bench.sh --duration -n "itu-1.15-buffer"
```

### Other options

| Flag | What |
|---|---|
| `-o, --out DIR` | result directory, instead of the generated `results/<timestamp>-...` one |
| `-n, --name NAME` | label for the run, appended to the directory name and shown in the report |
| `--no-report` | skip report generation, keep only the raw JMH json |
| `--open` | open `report.html` in the browser when done |
| `-b, --build` | force `mvn -q -DskipTests clean package` first |
| `-l, --list` | list matching benchmarks and exit |
| `--jvm-args ARGS` | forked JVM args (default `-XX:+UnlockDiagnosticVMOptions -XX:+TieredCompilation -XX:+AlwaysPreTouch`) |
| `--jmh ARGS` | pass raw args through to JMH, e.g. `--jmh "-t 4"` |
| `--dry-run` | print the JMH command instead of running it |
| `-v, --verbose` | JMH verbose output |

A report can also be regenerated from any JMH json without re-running the benchmarks:

```shell
python3 report.py results/latest/jmh-result.json          # writes alongside the input
python3 report.py results/latest/jmh-result.json -o /tmp  # or somewhere else
python3 report.py --help                                  # --baseline, --title, --no-png, -q
```

## Performance

Your mileage may vary. I've done my best to make sure these tests are as accurate as possible, but please do
your own evaluation - and prefer `--thorough` numbers on an otherwise idle machine.

For current numbers, run the suite yourself and open `results/latest/report.html`. `report.md` in the same
directory holds the same tables in markdown.

[Historical JMH result file](results/jmh-result-grouped.json) -
[Visualize JMH](https://jmh.morethan.io/?source=https://raw.githubusercontent.com/ethlo/date-time-wars/main/results/jmh-result-grouped.json)
- note this snapshot predates the current candidate set and the duration benchmarks. Any run's own
`jmh-result-grouped.json` can be dropped into the same viewer.

### Environment

Each run records its own environment in `run.properties`, so results carry the machine they were measured on.
