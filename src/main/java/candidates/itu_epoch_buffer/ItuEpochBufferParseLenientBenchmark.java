package candidates.itu_epoch_buffer;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Setup;

import com.ethlo.time.ITU;
import com.ethlo.time.MutableDateTimeBuffer;
import common.BenchmarkDefaults;

/**
 * {@code candidates.itu_epoch} on the zero-allocation path: the epoch-millis text as a {@code char[]} window,
 * parsed with {@link ITU#parseEpochMilli(char[], int, int, MutableDateTimeBuffer)} into a reusable buffer. This
 * is the like-for-like of {@code candidates.itu_buffer}, and the row to set against {@code candidates.epoch}
 * (a bare {@code long}) for what turning the number into a date actually costs.
 * <p>
 * State mirrors {@code candidates.itu_buffer}: the buffer is a field so its stores escape and cannot be elided,
 * and the consumed length goes to the Blackhole.
 */
public class ItuEpochBufferParseLenientBenchmark extends BenchmarkDefaults
{
    @Param({
            "2023-01-01T23:38:34.987654321+06:00",
            "5050-01-01T12:02:01.123Z",
            "3074-07-01T12:02:01Z"
    })
    public String dateString;

    private char[] chars;
    private int offset;
    private int length;
    private MutableDateTimeBuffer buffer;

    @Setup
    public void setup()
    {
        chars = Long.toString(OffsetDateTime.parse(dateString).toInstant().toEpochMilli()).toCharArray();
        offset = 0;
        length = chars.length;
        buffer = new MutableDateTimeBuffer();
    }

    @Benchmark
    public int parseLenient()
    {
        return ITU.parseEpochMilli(chars, offset, length, buffer);
    }
}
