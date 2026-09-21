| Operation | ITU | JDK `java.time` | Speed-up |
|:---|---:|---:|---:|
| `parse` | 16–25 ns/op | 494–508 ns/op | **20–30×** |
| `parseLenient` | 10–16 ns/op | 636–680 ns/op | **41–66×** |
| `isValid` | 1–11 ns/op | 473–2,082 ns/op | **45–675×** |
| `formatSeconds` | 14 ns/op | 88 ns/op | **6.2×** |
| `formatMillis` | 17 ns/op | 99 ns/op | **5.9×** |
| `formatNanos` | 29 ns/op | 100 ns/op | **3.5×** |
| `parseDuration` | 22–45 ns/op | 119–215 ns/op | **4.8–5.5×** |
| `formatDuration` | 12–24 ns/op | 9–27 ns/op | **0.7–1.2×** |

[Full report with error bars, inputs and environment »](https://ethlo.github.io/date-time-wars/)
