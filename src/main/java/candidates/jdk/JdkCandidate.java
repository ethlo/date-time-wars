package candidates.jdk;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.time.temporal.ChronoField;
import java.time.temporal.TemporalAccessor;

import common.DurationCodec;
import common.LenientDateTimeParser;
import common.Rfc3339Formatter;
import common.Rfc3339Parser;

/**
 * Plain java.time. Strict parsing uses {@link OffsetDateTime#parse(CharSequence)}, lenient parsing a
 * {@link DateTimeFormatterBuilder} layout with optional separator, fraction and offset. Formatters are
 * built once, up front.
 */
public class JdkCandidate implements Rfc3339Parser, LenientDateTimeParser, Rfc3339Formatter, DurationCodec<Duration>
{
    private static final DateTimeFormatter LENIENT_PARSER = new DateTimeFormatterBuilder()
            .appendValue(ChronoField.YEAR, 4)
            .appendLiteral('-')
            .appendValue(ChronoField.MONTH_OF_YEAR, 2)
            .appendLiteral('-')
            .appendValue(ChronoField.DAY_OF_MONTH, 2)
            .optionalStart().appendLiteral('T').optionalEnd()
            .optionalStart().appendLiteral('t').optionalEnd()
            .optionalStart().appendLiteral(' ').optionalEnd()
            .appendValue(ChronoField.HOUR_OF_DAY, 2)
            .appendLiteral(':')
            .appendValue(ChronoField.MINUTE_OF_HOUR, 2)
            .appendLiteral(':')
            .appendValue(ChronoField.SECOND_OF_MINUTE, 2)
            .optionalStart()
            .appendLiteral('.')
            .appendFraction(ChronoField.NANO_OF_SECOND, 1, 9, false)
            .optionalEnd()
            .optionalStart().appendOffset("+HH:MM", "Z").optionalEnd()
            .optionalStart().appendOffset("+HH:MM", "z").optionalEnd()
            .toFormatter();

    private static final DateTimeFormatter[] UTC_FORMATTERS = new DateTimeFormatter[10];

    static
    {
        for (int digits = 0; digits <= 9; digits++)
        {
            UTC_FORMATTERS[digits] = utcFormatter(digits);
        }
    }

    private static DateTimeFormatter utcFormatter(final int fractionDigits)
    {
        final DateTimeFormatterBuilder builder = new DateTimeFormatterBuilder()
                .appendValue(ChronoField.YEAR, 4)
                .appendLiteral('-')
                .appendValue(ChronoField.MONTH_OF_YEAR, 2)
                .appendLiteral('-')
                .appendValue(ChronoField.DAY_OF_MONTH, 2)
                .appendLiteral('T')
                .appendValue(ChronoField.HOUR_OF_DAY, 2)
                .appendLiteral(':')
                .appendValue(ChronoField.MINUTE_OF_HOUR, 2)
                .appendLiteral(':')
                .appendValue(ChronoField.SECOND_OF_MINUTE, 2);
        if (fractionDigits > 0)
        {
            builder.appendLiteral('.').appendFraction(ChronoField.NANO_OF_SECOND, fractionDigits, fractionDigits, false);
        }
        return builder.appendOffset("+HH:MM", "Z").toFormatter().withZone(ZoneOffset.UTC);
    }

    @Override
    public OffsetDateTime parseDateTime(final String text)
    {
        return OffsetDateTime.parse(text);
    }

    @Override
    public TemporalAccessor parseLenient(final String text)
    {
        return LENIENT_PARSER.parse(text);
    }

    @Override
    public String formatUtc(final OffsetDateTime date)
    {
        return formatUtc(date, 0);
    }

    @Override
    public String formatUtcMilli(final OffsetDateTime date)
    {
        return formatUtc(date, 3);
    }

    @Override
    public String formatUtcMicro(final OffsetDateTime date)
    {
        return formatUtc(date, 6);
    }

    @Override
    public String formatUtcNano(final OffsetDateTime date)
    {
        return formatUtc(date, 9);
    }

    @Override
    public String formatUtc(final OffsetDateTime date, final int fractionDigits)
    {
        return UTC_FORMATTERS[fractionDigits].format(date);
    }

    @Override
    public Duration parseDuration(final String text)
    {
        return Duration.parse(text);
    }

    @Override
    public String formatDuration(final Duration duration)
    {
        return duration.toString();
    }
}
