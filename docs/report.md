# date-time-wars

* **Date:** 2026-09-18T13:48:21
* **JDK:** 25.0.4 (OpenJDK 64-Bit Server VM 25.0.4+7-1-26.04-Ubuntu)
* **JVM args:** -XX:+UnlockDiagnosticVMOptions -XX:+TieredCompilation -XX:+AlwaysPreTouch
* **Iterations:** 1 fork(s), 3 × 2 s warmup, 5 × 2 s measurement

Lower is better. *rel* is the score relative to the fastest candidate in the same row.

## Date-time parsing

### parse

*strict RFC-3339 / ISO-8601 date-time*

#### `parse("2023-01-01T23:38:34.987654321+06:00")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 29.2 | 1.7 | 1.00× |
| 2 | ITU (configurable) | 69.7 | 4.7 | 2.39× |
| 3 | JDK Instant | 394 | 21.3 | 13.52× |
| 4 | JDK java.time | 498 | 16.6 | 17.07× |
| 5 | Google HTTP client | 594 | 57.3 | 20.34× |

#### `parse("3074-07-01T12:02:01Z")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 18.1 | 1.2 | 1.00× |
| 2 | JDK Instant | 354 | 26.7 | 19.61× |
| 3 | Google HTTP client | 414 | 15.9 | 22.88× |
| 4 | JDK java.time | 481 | 20.2 | 26.63× |

#### `parse("5050-01-01T12:02:01.123Z")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 22.5 | 1.5 | 1.00× |
| 2 | ITU (configurable) | 52.8 | 1.7 | 2.35× |
| 3 | JDK Instant | 370 | 9.9 | 16.44× |
| 4 | JDK java.time | 515 | 24.1 | 22.91× |
| 5 | Google HTTP client | 522 | 52.5 | 23.23× |

### parseLenient

*lenient date-time (optional fields)*

#### `parseLenient("2023-01-01T23:38:34.987654321+06:00")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 21.4 | 0.6 | 1.00× |
| 2 | JDK java.time | 678 | 41.4 | 31.61× |

#### `parseLenient("3074-07-01T12:02:01Z")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 12.1 | 0.6 | 1.00× |
| 2 | JDK java.time | 645 | 28.8 | 53.27× |

#### `parseLenient("5050-01-01T12:02:01.123Z")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 16.8 | 0.9 | 1.00× |
| 2 | JDK java.time | 681 | 31.0 | 40.54× |

## Date-time formatting

### formatSeconds

*format UTC, second resolution*

#### `formatSeconds()`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 14.1 | 1.0 | 1.00× |
| 2 | JDK java.time | 86.8 | 4.9 | 6.14× |

### formatMillis

*format UTC, millisecond resolution*

#### `formatMillis()`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 17.0 | 0.7 | 1.00× |
| 2 | JDK java.time | 98.3 | 5.9 | 5.78× |

### formatNanos

*format UTC, nanosecond resolution*

#### `formatNanos()`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 29.2 | 1.4 | 1.00× |
| 2 | JDK java.time | 101 | 3.7 | 3.45× |

## Duration

### parseDuration

*ISO-8601 duration*

#### `parseDuration("-P180DT23H27M19.193964536S")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 45.2 | 1.2 | 1.00× |
| 2 | JDK java.time | 207 | 48.5 | 4.59× |

#### `parseDuration("PT2H30M")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 21.3 | 1.1 | 1.00× |
| 2 | JDK java.time | 121 | 3.9 | 5.66× |

### formatDuration

*ISO-8601 duration*

#### `formatDuration("-P180DT23H27M19.193964536S")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **ITU** | 23.3 | 0.4 | 1.00× |
| 2 | JDK java.time | 27.8 | 0.9 | 1.19× |
| 3 | ITU (hours) | 28.0 | 1.6 | 1.20× |

#### `formatDuration("PT2H30M")`

| # | Candidate | ns/op | ± error | rel |
|---:|:---|---:|---:|---:|
| 1 | **JDK java.time** | 8.70 | 0.4 | 1.00× |
| 2 | ITU (hours) | 11.9 | 0.3 | 1.37× |
| 3 | ITU | 12.6 | 0.8 | 1.45× |
