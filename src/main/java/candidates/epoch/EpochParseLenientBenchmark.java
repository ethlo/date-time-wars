package candidates.epoch;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Setup;

import common.BenchmarkDefaults;

/**
 * The alternative to a date-time string at all: epoch milliseconds as a decimal integer, read with
 * {@link Long#parseLong(String)}. This is the cost anyone choosing epoch numbers "because they are faster to
 * parse" is comparing against, so it sits in the {@code parseLenient} rows next to the string parsers.
 * <p>
 * The {@code @Param} is the same date-time string as the other candidates, so the rows line up; {@code @Setup}
 * turns it into the epoch-millis text this candidate actually parses (13-14 digits for these inputs). The
 * nanosecond input is truncated to milliseconds, which is the precision epoch millis has.
 * <p>
 * The result is a primitive {@code long}, not a temporal object, so this row is the allocation-free floor of
 * the epoch approach - the like-for-like of {@code itu_buffer}, not of {@code itu}.
 */
public class EpochParseLenientBenchmark extends BenchmarkDefaults
{
    @Param({
            "2023-01-01T23:38:34.987654321+06:00",
            "5050-01-01T12:02:01.123Z",
            "3074-07-01T12:02:01Z"
    })
    public String dateString;

    private String epochMillis;

    @Setup
    public void setup()
    {
        epochMillis = Long.toString(OffsetDateTime.parse(dateString).toInstant().toEpochMilli());
    }

    @Benchmark
    public long parseLenient()
    {
        return Long.parseLong(epochMillis);
    }
}
