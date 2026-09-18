package candidates.google;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import com.google.api.client.util.DateTime;
import common.Rfc3339Parser;

/**
 * Google HTTP client's {@link DateTime#parseRfc3339ToSecondsAndNanos(String)}.
 */
public class GoogleCandidate implements Rfc3339Parser
{
    @Override
    public OffsetDateTime parseDateTime(final String text)
    {
        final DateTime.SecondsAndNanos secondsAndNanos = DateTime.parseRfc3339ToSecondsAndNanos(text);
        return OffsetDateTime.ofInstant(Instant.ofEpochSecond(secondsAndNanos.getSeconds(), secondsAndNanos.getNanos()), ZoneOffset.UTC);
    }
}
