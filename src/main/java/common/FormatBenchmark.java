package common;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;

/**
 * Formatting an {@link OffsetDateTime} as an RFC-3339 UTC string at different resolutions.
 */
public abstract class FormatBenchmark extends BenchmarkDefaults
{
    private static final OffsetDateTime INPUT = OffsetDateTime.parse("2017-12-21T12:20:45.987654321Z");

    private final Rfc3339Formatter formatter;

    protected FormatBenchmark(Rfc3339Formatter formatter)
    {
        this.formatter = formatter;
    }

    @Benchmark
    public String formatSeconds()
    {
        return formatter.formatUtc(INPUT);
    }

    @Benchmark
    public String formatMillis()
    {
        return formatter.formatUtcMilli(INPUT);
    }

    @Benchmark
    public String formatNanos()
    {
        return formatter.formatUtcNano(INPUT);
    }
}
