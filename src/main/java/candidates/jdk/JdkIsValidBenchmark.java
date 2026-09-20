package candidates.jdk;

import java.time.DateTimeException;
import java.time.OffsetDateTime;

import common.IsValidBenchmark;

/**
 * java.time has no validity check without a parse, so this is {@link OffsetDateTime#parse(CharSequence)} and a
 * catch - what every validator on top of java.time is.
 */
public class JdkIsValidBenchmark extends IsValidBenchmark
{
    public JdkIsValidBenchmark()
    {
        super(text ->
        {
            try
            {
                OffsetDateTime.parse(text);
                return true;
            }
            catch (DateTimeException exc)
            {
                return false;
            }
        });
    }
}
