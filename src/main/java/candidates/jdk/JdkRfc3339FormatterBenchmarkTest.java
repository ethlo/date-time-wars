package candidates.jdk;

import common.FormatterBenchmarkTest;

public class JdkRfc3339FormatterBenchmarkTest extends FormatterBenchmarkTest
{
    public JdkRfc3339FormatterBenchmarkTest()
    {
        super(new JdkLenientParser());
    }
}
