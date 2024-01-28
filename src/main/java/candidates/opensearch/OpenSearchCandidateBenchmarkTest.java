package candidates.opensearch;

import java.text.ParsePosition;
import java.time.temporal.TemporalAccessor;

import common.LenientDateTimeParser;
import common.ParserBenchmarkTest;

public class OpenSearchCandidateBenchmarkTest extends ParserBenchmarkTest
{
    public OpenSearchCandidateBenchmarkTest()
    {
        super(new LenientDateTimeParser()
        {
            final RFC3339DateTimeFormatter candidate = new RFC3339DateTimeFormatter("");

            @Override
            public TemporalAccessor parseLenient(final String dateTimeStr)
            {
                return candidate.parse(dateTimeStr, new ParsePosition(0));
            }
        });
    }
}