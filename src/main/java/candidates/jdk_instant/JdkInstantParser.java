package candidates.jdk_instant;

import java.time.Instant;
import java.time.temporal.TemporalAccessor;

import common.LenientDateTimeParser;

/**
 * Java 8 JDK classes. The safe and normally "efficient enough" choice.
 *
 * @author ethlo - Morten Haraldsen
 */
public class JdkInstantParser implements LenientDateTimeParser
{
    @Override
    public TemporalAccessor parseLenient(final String s)
    {
        return Instant.parse(s);
    }
}
