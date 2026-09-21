package candidates.itu_configurable;

import static com.ethlo.time.DateTimeTokens.digits;
import static com.ethlo.time.DateTimeTokens.optionalFractions;
import static com.ethlo.time.DateTimeTokens.separators;
import static com.ethlo.time.DateTimeTokens.zoneOffset;
import static com.ethlo.time.Field.DAY;
import static com.ethlo.time.Field.HOUR;
import static com.ethlo.time.Field.MINUTE;
import static com.ethlo.time.Field.MONTH;
import static com.ethlo.time.Field.SECOND;
import static com.ethlo.time.Field.YEAR;

import java.text.ParsePosition;
import java.time.OffsetDateTime;

import com.ethlo.time.DateTimeParser;
import com.ethlo.time.token.ConfigurableDateTimeParser;
import common.Rfc3339Parser;

/**
 * ITU's configurable token based parser, set up for the RFC-3339 layout
 * {@code yyyy-MM-ddTHH:mm:ss[.fraction]+offset}, so it takes the same inputs as the fixed parser.
 */
public class ItuConfigurableCandidate implements Rfc3339Parser
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
            optionalFractions('.'),
            zoneOffset()
    );

    @Override
    public OffsetDateTime parseDateTime(final String text)
    {
        return FRACTIONAL_SECONDS_OFFSET.parse(text, new ParsePosition(0)).toOffsetDatetime();
    }
}
