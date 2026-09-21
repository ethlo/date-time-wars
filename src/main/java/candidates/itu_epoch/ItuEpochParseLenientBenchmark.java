package candidates.itu_epoch;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Setup;

import com.ethlo.time.DateTime;
import com.ethlo.time.ITU;
import common.BenchmarkDefaults;

/**
 * The epoch alternative measured on equal terms with the string parsers: the same epoch-millis text that
 * {@code candidates.epoch} hands to {@link Long#parseLong(String)}, but parsed with
 * {@link ITU#parseEpochMilli(String)} into the same {@link DateTime} that {@code ITU.parseLenient} returns for
 * the date-time string. "Epoch is faster to parse" is only a like-for-like claim when both sides end at a
 * temporal value; this row is that comparison, and {@code candidates.epoch} is the floor beneath it.
 * <p>
 * Input handling mirrors {@code candidates.epoch}: the {@code @Param} is the date-time string so the rows line
 * up, and {@code @Setup} turns it into epoch-millis text, truncating the nanosecond input to milliseconds.
 */
public class ItuEpochParseLenientBenchmark extends BenchmarkDefaults
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
    public DateTime parseLenient()
    {
        return ITU.parseEpochMilli(epochMillis);
    }
}
