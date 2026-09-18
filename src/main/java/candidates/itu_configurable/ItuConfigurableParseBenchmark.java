package candidates.itu_configurable;

import java.time.OffsetDateTime;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.Param;

import common.BenchmarkDefaults;
import common.ParseBenchmark;

/**
 * Same as {@link ParseBenchmark}, but limited to the inputs the fixed token layout in
 * {@link ItuConfigurableCandidate} can handle (the layout requires a fraction).
 */
public class ItuConfigurableParseBenchmark extends BenchmarkDefaults
{
    private final ItuConfigurableCandidate parser = new ItuConfigurableCandidate();

    @Param({
            "2023-01-01T23:38:34.987654321+06:00",
            "5050-01-01T12:02:01.123Z"
    })
    public String dateString;

    @Benchmark
    public OffsetDateTime parse()
    {
        return parser.parseDateTime(dateString);
    }
}
