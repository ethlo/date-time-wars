package candidates.jdk_instant;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import common.Rfc3339Parser;

/**
 * {@link Instant#parse(CharSequence)}, the JDK's fastest built-in path for RFC-3339 input.
 */
public class JdkInstantCandidate implements Rfc3339Parser
{
    @Override
    public OffsetDateTime parseDateTime(final String text)
    {
        return Instant.parse(text).atOffset(ZoneOffset.UTC);
    }
}
