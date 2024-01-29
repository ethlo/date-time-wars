package candidates.itu;


import com.ethlo.time.ITU;
import com.ethlo.time.internal.EthloITU;
import common.LenientDateTimeParser;
import common.ParserBenchmarkTest;

import java.time.temporal.TemporalAccessor;

public class ITULenientParserBenchmarkTest extends ParserBenchmarkTest
{
    public ITULenientParserBenchmarkTest()
    {
        super(ITU::parseLenient);
    }
}
