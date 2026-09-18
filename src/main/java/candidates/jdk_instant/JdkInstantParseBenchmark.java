package candidates.jdk_instant;

import common.ParseBenchmark;

public class JdkInstantParseBenchmark extends ParseBenchmark
{
    public JdkInstantParseBenchmark()
    {
        super(new JdkInstantCandidate());
    }
}
