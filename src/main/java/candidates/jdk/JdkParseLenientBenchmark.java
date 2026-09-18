package candidates.jdk;

import common.ParseLenientBenchmark;

public class JdkParseLenientBenchmark extends ParseLenientBenchmark
{
    public JdkParseLenientBenchmark()
    {
        super(new JdkCandidate());
    }
}
