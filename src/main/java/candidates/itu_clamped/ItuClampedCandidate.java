package candidates.itu_clamped;

import com.ethlo.time.Duration;
import com.ethlo.time.DurationUnit;
import com.ethlo.time.ITU;
import common.DurationCodec;

/**
 * ITU duration formatting clamped to hours, for a like-for-like comparison against
 * {@code java.time.Duration.toString()}.
 * <p>
 * ITU's default {@code normalized()} renders with the largest units available, so it emits weeks and days
 * where the JDK only ever accumulates into hours - {@code -P25W5DT23H27M19.193964536S} against
 * {@code PT-4343H-27M-19.193964536S}. Capping at {@link DurationUnit#HOURS} makes both decompose the
 * duration the same way, so the measurement is formatting cost rather than how many components each one
 * chose to emit.
 * <p>
 * NOTE: The two are still not character-identical. ITU carries a single leading sign as ISO 8601 specifies
 * ({@code -PT4343H27M19.193964536S}), while the JDK signs every component. See
 * {@code candidates.itu.ItuCandidate} for the default rendering, which is what {@code toString()} gives you.
 */
public class ItuClampedCandidate implements DurationCodec<Duration>
{
    @Override
    public Duration parseDuration(final String text)
    {
        return ITU.parseDuration(text);
    }

    @Override
    public String formatDuration(final Duration duration)
    {
        return duration.normalized(DurationUnit.HOURS);
    }
}
