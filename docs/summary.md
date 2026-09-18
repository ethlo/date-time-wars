| Operation | ITU | JDK `java.time` | Speed-up |
|:---|---:|---:|---:|
| `parse` | 18–29 ns/op | 481–515 ns/op | **17–27×** |
| `parseLenient` | 12–21 ns/op | 645–681 ns/op | **32–53×** |
| `formatSeconds` | 14 ns/op | 87 ns/op | **6.1×** |
| `formatMillis` | 17 ns/op | 98 ns/op | **5.8×** |
| `formatNanos` | 29 ns/op | 101 ns/op | **3.4×** |
| `parseDuration` | 21–45 ns/op | 121–207 ns/op | **4.6–5.7×** |
| `formatDuration` | 13–23 ns/op | 9–28 ns/op | **0.7–1.2×** |

[Full report with error bars, inputs and environment »](https://ethlo.github.io/date-time-wars/)
