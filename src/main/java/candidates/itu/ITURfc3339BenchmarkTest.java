package candidates.itu;

import com.ethlo.time.ITU;
import common.ParserBenchmarkTest;

public class ITURfc3339BenchmarkTest extends ParserBenchmarkTest
{
    public ITURfc3339BenchmarkTest()
    {
        super(ITU::parseDateTime);
    }
}
