package candidates.itu_configurable;


import static com.ethlo.time.DateTimeTokens.digits;
import static com.ethlo.time.DateTimeTokens.fractions;
import static com.ethlo.time.DateTimeTokens.separators;
import static com.ethlo.time.DateTimeTokens.zoneOffset;
import static com.ethlo.time.Field.DAY;
import static com.ethlo.time.Field.HOUR;
import static com.ethlo.time.Field.MINUTE;
import static com.ethlo.time.Field.MONTH;
import static com.ethlo.time.Field.SECOND;
import static com.ethlo.time.Field.YEAR;

import java.text.ParsePosition;

import com.ethlo.time.DateTimeParser;
import com.ethlo.time.token.ConfigurableDateTimeParser;
import common.ParserBenchmarkTest;

public class ItuConfigurableParserBenchmarkTest extends ParserBenchmarkTest
{
    private static final DateTimeParser FRACTIONAL_SECONDS_OFFSET = ConfigurableDateTimeParser.of(
            digits(YEAR, 4),
            separators('-'),
            digits(MONTH, 2),
            separators('-'),
            digits(DAY, 2),
            separators('T'),
            digits(HOUR, 2),
            separators(':'),
            digits(MINUTE, 2),
            separators(':'),
            digits(SECOND, 2),
            separators('.'),
            fractions(),
            zoneOffset()
    );

    public ItuConfigurableParserBenchmarkTest()
    {
        super(text -> FRACTIONAL_SECONDS_OFFSET.parse(text, new ParsePosition(0)));
    }
}
