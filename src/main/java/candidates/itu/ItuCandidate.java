package candidates.itu;

import java.time.OffsetDateTime;
import java.time.temporal.TemporalAccessor;

import com.ethlo.time.Duration;
import com.ethlo.time.ITU;
import common.DurationCodec;
import common.LenientDateTimeParser;
import common.Rfc3339Formatter;
import common.Rfc3339Parser;

/**
 * Internet Time Utility - https://github.com/ethlo/itu
 */
public class ItuCandidate implements Rfc3339Parser, LenientDateTimeParser, Rfc3339Formatter, DurationCodec<Duration>
{
    @Override
    public OffsetDateTime parseDateTime(final String text)
    {
        return ITU.parseDateTime(text);
    }

    @Override
    public TemporalAccessor parseLenient(final String text)
    {
        return ITU.parseLenient(text);
    }

    @Override
    public String formatUtc(final OffsetDateTime date)
    {
        return ITU.formatUtc(date);
    }

    @Override
    public String formatUtcMilli(final OffsetDateTime date)
    {
        return ITU.formatUtcMilli(date);
    }

    @Override
    public String formatUtcMicro(final OffsetDateTime date)
    {
        return ITU.formatUtcMicro(date);
    }

    @Override
    public String formatUtcNano(final OffsetDateTime date)
    {
        return ITU.formatUtcNano(date);
    }

    @Override
    public String formatUtc(final OffsetDateTime date, final int fractionDigits)
    {
        return ITU.formatUtc(date, fractionDigits);
    }

    @Override
    public Duration parseDuration(final String text)
    {
        return ITU.parseDuration(text);
    }

    @Override
    public String formatDuration(final Duration duration)
    {
        return duration.normalized();
    }
}
