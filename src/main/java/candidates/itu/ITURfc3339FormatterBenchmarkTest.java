package candidates.itu;

import com.ethlo.time.internal.EthloITU;
import common.FormatterBenchmarkTest;

public class ITURfc3339FormatterBenchmarkTest extends FormatterBenchmarkTest
{
    public ITURfc3339FormatterBenchmarkTest()
    {
        super(EthloITU.getInstance());
    }
}
