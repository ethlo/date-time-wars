package candidates.itu_configurable;

import java.text.ParsePosition;
import java.time.OffsetDateTime;

import com.ethlo.time.DateTimeParser;
import com.ethlo.time.DateTimeParsers;
import common.Rfc3339Parser;

/**
 * ITU's configurable, token based parser using its predefined RFC-3339 layout.
 */
public class ItuTokenParserCandidate implements Rfc3339Parser
{
    private static final DateTimeParser RFC_3339 = DateTimeParsers.rfc3339();

    @Override
    public OffsetDateTime parseDateTime(final String text)
    {
        return RFC_3339.parse(text, new ParsePosition(0)).toOffsetDatetime();
    }
}
