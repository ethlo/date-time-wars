package common;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;

/**
 * Strict RFC-3339 parsing: a fully specified date-time with offset in, an {@link OffsetDateTime} out.
 */
public abstract class ParseBenchmark extends BenchmarkDefaults
{
    private final Rfc3339Parser parser;

    @Param({
            "2023-01-01T23:38:34.987654321+06:00",
            "5050-01-01T12:02:01.123Z",
            "3074-07-01T12:02:01Z"
    })
    public String dateString;

    protected ParseBenchmark(Rfc3339Parser parser)
    {
        this.parser = parser;
    }

    @Benchmark
    public OffsetDateTime parse()
    {
        return parser.parseDateTime(dateString);
    }
}
