package candidates.jdk;

import java.time.Duration;

import common.FormatDurationBenchmark;

public class JdkFormatDurationBenchmark extends FormatDurationBenchmark<Duration>
{
    public JdkFormatDurationBenchmark()
    {
        super(new JdkCandidate());
    }
}
