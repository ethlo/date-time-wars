package candidates.itu_buffer;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Setup;

import com.ethlo.time.Duration;
import com.ethlo.time.ITU;
import common.BenchmarkDefaults;

/**
 * ITU's zero-allocation formatting: the same output as {@link common.FormatBenchmark} and
 * {@link common.FormatDurationBenchmark}, written into a reused {@code byte[]}. The buffer is a field, so the
 * stores escape; the length goes to the Blackhole. Same inputs as the String rows so they line up.
 */
public class ItuBufferFormatBenchmark extends BenchmarkDefaults
{
    @Param({
            "2017-12-21T12:20:45.987654321Z",
            "2017-12-21T18:20:45.987654321+06:00"
    })
    public String dateString;

    private OffsetDateTime INPUT;
    private byte[] bytes;
    private Duration shortDuration;
    private Duration longDuration;

    @Setup
    public void setup()
    {
        INPUT = OffsetDateTime.parse(dateString);
        bytes = new byte[64];
        shortDuration = ITU.parseDuration("PT2H30M");
        longDuration = ITU.parseDuration("-P180DT23H27M19.193964536S");
    }

    @Benchmark
    public int formatSeconds()
    {
        return ITU.formatUtc(INPUT, 0, bytes, 0);
    }

    @Benchmark
    public int formatMillis()
    {
        return ITU.formatUtc(INPUT, 3, bytes, 0);
    }

    @Benchmark
    public int formatNanos()
    {
        return ITU.formatUtc(INPUT, 9, bytes, 0);
    }

    @Benchmark
    public int formatDurationShort()
    {
        return shortDuration.normalized(bytes, 0);
    }

    @Benchmark
    public int formatDurationLong()
    {
        return longDuration.normalized(bytes, 0);
    }
}
