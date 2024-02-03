package candidates.itu_configurable;


import static com.ethlo.time.Field.DAY;
import static com.ethlo.time.Field.HOUR;
import static com.ethlo.time.Field.MINUTE;
import static com.ethlo.time.Field.MONTH;
import static com.ethlo.time.Field.SECOND;
import static com.ethlo.time.Field.YEAR;
import static com.ethlo.time.token.DateTimeTokens.digits;
import static com.ethlo.time.token.DateTimeTokens.fractions;
import static com.ethlo.time.token.DateTimeTokens.separators;
import static com.ethlo.time.token.DateTimeTokens.timeZoneOffset;

import java.text.ParsePosition;

import com.ethlo.time.token.ConfigurableDateTimeParser;
import common.ParserBenchmarkTest;

public class ItuConfigurableParserBenchmarkTest extends ParserBenchmarkTest
{
    private static final ConfigurableDateTimeParser DATE = new ConfigurableDateTimeParser(
            digits(YEAR, 4),
            separators('-'),
            digits(MONTH, 2),
            separators('-'),
            digits(DAY, 2)
    );

    private static final ConfigurableDateTimeParser MINUTES = DATE.combine(
            separators('T'),
            digits(HOUR, 2),
            separators(':'),
            digits(MINUTE, 2)
    );

    private static final ConfigurableDateTimeParser LOCAL_TIME = MINUTES.combine(
            separators(':'),
            digits(SECOND, 2)
    );

    private static final ConfigurableDateTimeParser FRACTIONAL_SECONDS_LOCAL = LOCAL_TIME.combine(
            separators('.'),
            fractions()
    );

    private static final ConfigurableDateTimeParser FRACTIONAL_SECONDS_OFFSET = FRACTIONAL_SECONDS_LOCAL.combine(
            timeZoneOffset()
    );

    public ItuConfigurableParserBenchmarkTest()
    {
        super(text -> FRACTIONAL_SECONDS_OFFSET.parse(text, new ParsePosition(0)));
    }
}
