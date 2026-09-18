package common;

import java.time.temporal.TemporalAccessor;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;

/**
 * Lenient parsing: fractions and offset optional, result in the candidate's own temporal type.
 */
public abstract class ParseLenientBenchmark extends BenchmarkDefaults
{
    private final LenientDateTimeParser parser;

    @Param({
            "2023-01-01T23:38:34.987654321+06:00",
            "5050-01-01T12:02:01.123Z",
            "3074-07-01T12:02:01Z"
    })
    public String dateString;

    protected ParseLenientBenchmark(LenientDateTimeParser parser)
    {
        this.parser = parser;
    }

    @Benchmark
    public TemporalAccessor parseLenient()
    {
        return parser.parseLenient(dateString);
    }
}
