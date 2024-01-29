package candidates.noop;

import com.ethlo.time.DateTime;
import com.ethlo.time.TimezoneOffset;
import common.ParserBenchmarkTest;

public class NoopParserBenchmarkTest extends ParserBenchmarkTest
{
    public NoopParserBenchmarkTest()
    {
        super(chars -> DateTime.of(2222, 12, 22, 1, 1, 22, 4422233, TimezoneOffset.UTC, 3));
    }
}
