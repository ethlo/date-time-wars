| Operation | ITU | JDK `java.time` | Speed-up |
|:---|---:|---:|---:|
| `parse` | 18–28 ns/op | 542–577 ns/op | **21–30×** |
| `parseLenient` | 11–17 ns/op | 755–788 ns/op | **46–67×** |
| `isValid` | 2–13 ns/op | 536–2,397 ns/op | **43–669×** |
| `formatSeconds` | 16 ns/op | 100 ns/op | **6.3×** |
| `formatMillis` | 19 ns/op | 115 ns/op | **6.1×** |
| `formatNanos` | 33 ns/op | 115 ns/op | **3.5×** |
| `parseDuration` | 25–52 ns/op | 134–247 ns/op | **4.8–5.4×** |
| `formatDuration` | 14–27 ns/op | 10–31 ns/op | **0.7–1.2×** |

[Full report with error bars, inputs and environment »](https://ethlo.github.io/date-time-wars/)
