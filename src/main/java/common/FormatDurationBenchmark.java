package common;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Setup;

/**
 * Formatting a duration (parsed once in {@link #setup()}) as an ISO-8601 string.
 */
public abstract class FormatDurationBenchmark<T> extends BenchmarkDefaults
{
    private final DurationCodec<T> codec;

    @Param({
            "-P180DT23H27M19.193964536S",
            "PT2H30M"
    })
    public String durationString;

    private T duration;

    protected FormatDurationBenchmark(DurationCodec<T> codec)
    {
        this.codec = codec;
    }

    @Setup
    public void setup()
    {
        duration = codec.parseDuration(durationString);
    }

    @Benchmark
    public String formatDuration()
    {
        return codec.formatDuration(duration);
    }
}
