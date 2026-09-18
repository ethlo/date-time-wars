| Operation | ITU | JDK `java.time` | Speed-up |
|:---|---:|---:|---:|
| `parse` | 20–33 ns/op | 562–578 ns/op | **18–28×** |
| `parseLenient` | 14–25 ns/op | 732–796 ns/op | **32–53×** |
| `formatSeconds` | 16 ns/op | 101 ns/op | **6.3×** |
| `formatMillis` | 19 ns/op | 114 ns/op | **6.0×** |
| `formatNanos` | 34 ns/op | 116 ns/op | **3.4×** |
| `parseDuration` | 25–52 ns/op | 133–253 ns/op | **4.9–5.4×** |
| `formatDuration` | 14–27 ns/op | 10–31 ns/op | **0.7–1.1×** |

[Full report with error bars, inputs and environment »](https://ethlo.github.io/date-time-wars/)
