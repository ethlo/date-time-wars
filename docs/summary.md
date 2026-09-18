| Operation | ITU | JDK `java.time` | Speed-up |
|:---|---:|---:|---:|
| `parse` | 20–33 ns/op | 546–579 ns/op | **17–27×** |
| `parseLenient` | 14–24 ns/op | 736–796 ns/op | **32–53×** |
| `formatSeconds` | 16 ns/op | 102 ns/op | **6.4×** |
| `formatMillis` | 19 ns/op | 113 ns/op | **5.9×** |
| `formatNanos` | 34 ns/op | 118 ns/op | **3.5×** |
| `parseDuration` | 24–51 ns/op | 132–256 ns/op | **5.0–5.5×** |
| `formatDuration` | 13–27 ns/op | 10–31 ns/op | **0.7–1.1×** |

[Full report with error bars, inputs and environment »](https://ethlo.github.io/date-time-wars/)
