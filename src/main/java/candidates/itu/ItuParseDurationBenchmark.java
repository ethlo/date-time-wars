package candidates.itu;

import com.ethlo.time.Duration;
import common.ParseDurationBenchmark;

public class ItuParseDurationBenchmark extends ParseDurationBenchmark<Duration>
{
    public ItuParseDurationBenchmark()
    {
        super(new ItuCandidate());
    }
}
