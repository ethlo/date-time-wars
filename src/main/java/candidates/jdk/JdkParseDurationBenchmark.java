package candidates.jdk;

import java.time.Duration;

import common.ParseDurationBenchmark;

public class JdkParseDurationBenchmark extends ParseDurationBenchmark<Duration>
{
    public JdkParseDurationBenchmark()
    {
        super(new JdkCandidate());
    }
}
