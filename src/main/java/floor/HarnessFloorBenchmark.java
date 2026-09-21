package floor;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Setup;

import common.BenchmarkDefaults;

/**
 * The cost of the harness itself: the JMH loop, the {@code @State} field loads and handing an
 * {@code int} to the Blackhole, with no parsing at all. Subtract it from a parse score to get the
 * time the parser is actually responsible for - "single-digit nanoseconds" is only an honest claim
 * net of this number.
 * <p>
 * Deliberately outside {@code candidates.*} and not named {@code parseLenient}, so it never shows up
 * as a candidate in the report or in the {@code --lenient} suite; run it with {@code --floor}.
 * The state mirrors what the zero-allocation {@code char[]} parse benchmark holds, so the two
 * are subtracted like for like.
 */
public class HarnessFloorBenchmark extends BenchmarkDefaults
{
    @Param({
            "2023-01-01T23:38:34.987654321+06:00",
            "5050-01-01T12:02:01.123Z",
            "3074-07-01T12:02:01Z"
    })
    public String dateString;

    private char[] chars;
    private int offset;

    @Setup
    public void setup()
    {
        chars = dateString.toCharArray();
        offset = 0;
    }

    @Benchmark
    public int floor()
    {
        return chars.length - offset;
    }
}
