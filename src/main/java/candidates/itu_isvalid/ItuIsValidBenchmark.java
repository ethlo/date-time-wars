package candidates.itu_isvalid;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;

import com.ethlo.time.ITU;
import common.BenchmarkDefaults;

/**
 * {@code ITU.isValid(String)}: the yes/no of strict RFC-3339 parsing. The three valid inputs are those of
 * {@link common.ParseBenchmark}; the invalid ones are the shapes a validator meets in practice - trailing junk,
 * a field out of range, a truncated value and something that is not a date at all - because an implementation
 * that parses and catches pays for the exception on exactly those.
 */
public class ItuIsValidBenchmark extends BenchmarkDefaults
{
    @Param({
            "2023-01-01T23:38:34.987654321+06:00",
            "5050-01-01T12:02:01.123Z",
            "3074-07-01T12:02:01Z",
            "3074-07-01T12:02:01Zjunk",
            "3074-13-01T12:02:01Z",
            "3074-07-01T12:02",
            "not-a-date"
    })
    public String dateString;

    @Benchmark
    public boolean isValid()
    {
        return ITU.isValid(dateString);
    }
}
