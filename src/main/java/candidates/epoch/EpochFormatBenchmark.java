package candidates.epoch;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Setup;

import common.BenchmarkDefaults;

/**
 * The alternative to formatting a date-time string at all: the epoch count as a decimal integer via
 * {@link Long#toString(long)}. Same input instant as {@link common.FormatBenchmark}, and each resolution row
 * emits the epoch count at that resolution (seconds, milliseconds, nanoseconds), so the rows compare the cost
 * of producing the text an API or file would carry either way.
 * <p>
 * The counts are fields of the state object rather than constants, so the JIT cannot fold the conversion.
 */
public class EpochFormatBenchmark extends BenchmarkDefaults
{
    private static final OffsetDateTime INPUT = OffsetDateTime.parse("2017-12-21T12:20:45.987654321Z");

    private long epochSeconds;
    private long epochMillis;
    private long epochNanos;

    @Setup
    public void setup()
    {
        epochSeconds = INPUT.toEpochSecond();
        epochMillis = INPUT.toInstant().toEpochMilli();
        epochNanos = epochSeconds * 1_000_000_000L + INPUT.getNano();
    }

    @Benchmark
    public String formatSeconds()
    {
        return Long.toString(epochSeconds);
    }

    @Benchmark
    public String formatMillis()
    {
        return Long.toString(epochMillis);
    }

    @Benchmark
    public String formatNanos()
    {
        return Long.toString(epochNanos);
    }
}
