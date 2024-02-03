package candidates.jdk_instant;

import candidates.jdk_instant.JdkInstantParser;
import common.ParserBenchmarkTest;

public class JdkInstantBenchmarkTest extends ParserBenchmarkTest
{
    public JdkInstantBenchmarkTest()
    {
        super(new JdkInstantParser());
    }
}
