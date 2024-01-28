package candidates.jdk;

import common.ParserBenchmarkTest;

public class JdkRfc3339ParserBenchmarkTest extends ParserBenchmarkTest
{
    public JdkRfc3339ParserBenchmarkTest()
    {
        super(new JdkLenientParser());
    }
}
