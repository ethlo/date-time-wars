package candidates.jdk;

import common.ParseBenchmark;

public class JdkParseBenchmark extends ParseBenchmark
{
    public JdkParseBenchmark()
    {
        super(new JdkCandidate());
    }
}
