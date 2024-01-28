package common;

import java.time.temporal.TemporalAccessor;

public interface LenientDateTimeParser
{
    TemporalAccessor parseLenient(String chars);
}