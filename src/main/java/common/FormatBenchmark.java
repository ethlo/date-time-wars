package common;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Setup;

/**
 * Formatting an {@link OffsetDateTime} as an RFC-3339 UTC string at different resolutions.
 */
public abstract class FormatBenchmark extends BenchmarkDefaults
{
    /**
     * The same instant at UTC and at an offset: a formatter that renders UTC reads the fields off the first and
     * has to convert the second, which is the shape of most real inputs.
     */
    @Param({
            "2017-12-21T12:20:45.987654321Z",
            "2017-12-21T18:20:45.987654321+06:00"
    })
    public String dateString;

    private OffsetDateTime INPUT;
    private final Rfc3339Formatter formatter;

    protected FormatBenchmark(Rfc3339Formatter formatter)
    {
        this.formatter = formatter;
    }

    @Setup
    public void setup()
    {
        INPUT = OffsetDateTime.parse(dateString);
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
