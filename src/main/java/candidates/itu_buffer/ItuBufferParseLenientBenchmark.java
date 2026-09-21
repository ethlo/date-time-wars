package candidates.itu_buffer;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Setup;

import com.ethlo.time.ITU;
import com.ethlo.time.MutableDateTimeBuffer;
import common.BenchmarkDefaults;

/**
 * ITU's zero-allocation path: the same lenient grammar parsed from a {@code char[]} window into a reusable
 * {@link MutableDateTimeBuffer}. Same inputs as {@link common.ParseLenientBenchmark} so the rows line up; the
 * state mirrors {@code floor.HarnessFloorBenchmark}, so floor and score subtract like for like.
 * <p>
 * The buffer is a field of the state object, so its stores escape and cannot be elided; the consumed length goes
 * to the Blackhole.
 */
public class ItuBufferParseLenientBenchmark extends BenchmarkDefaults
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
        chars = dateString.toCharArray();
        offset = 0;
        length = chars.length;
        buffer = new MutableDateTimeBuffer();
    }

    @Benchmark
    public int parseLenient()
    {
        return ITU.parseLenient(chars, offset, length, buffer);
    }

    /**
     * Parse followed by the conversion a pipeline does next: the epoch second, which runs the civil-to-days
     * arithmetic. The throughput harness showed this pair, not the parse alone, is what a file reader pays.
     */
    @Benchmark
    public long parseLenientToEpochSecond()
    {
        ITU.parseLenient(chars, offset, length, buffer);
        return buffer.toEpochSecond();
    }
}
