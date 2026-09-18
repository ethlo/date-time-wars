package common;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;

/**
 * Parsing an ISO-8601 duration string into the candidate's own duration type.
 */
public abstract class ParseDurationBenchmark<T> extends BenchmarkDefaults
{
    private final DurationCodec<T> codec;

    @Param({
            "-P180DT23H27M19.193964536S",
            "PT2H30M"
    })
    public String durationString;

    protected ParseDurationBenchmark(DurationCodec<T> codec)
    {
        this.codec = codec;
    }

    @Benchmark
    public T parseDuration()
    {
        return codec.parseDuration(durationString);
    }
}
