package candidates.itu;


import com.ethlo.time.ITU;
import common.ParserBenchmarkTest;

public class ITULenientParserBenchmarkTest extends ParserBenchmarkTest
{
    public ITULenientParserBenchmarkTest()
    {
        super(ITU::parseLenient);
    }
}
