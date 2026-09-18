package common;

/**
 * Parse and format ISO-8601 durations using the candidate's own duration type.
 *
 * @param <T> The candidate's duration type
 */
public interface DurationCodec<T>
{
    T parseDuration(String text);

    String formatDuration(T duration);
}
