package candidates.itu;

import com.ethlo.time.Duration;
import common.FormatDurationBenchmark;

public class ItuFormatDurationBenchmark extends FormatDurationBenchmark<Duration>
{
    public ItuFormatDurationBenchmark()
    {
        super(new ItuCandidate());
    }
}
