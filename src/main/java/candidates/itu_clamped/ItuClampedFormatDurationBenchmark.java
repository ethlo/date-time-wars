package candidates.itu_clamped;

import com.ethlo.time.Duration;
import common.FormatDurationBenchmark;

/**
 * Extends the shared {@link FormatDurationBenchmark} rather than declaring its own inputs, so the parameters
 * match the other candidates exactly and the results land in the same reported scenario.
 */
public class ItuClampedFormatDurationBenchmark extends FormatDurationBenchmark<Duration>
{
    public ItuClampedFormatDurationBenchmark()
    {
        super(new ItuClampedCandidate());
    }
}
