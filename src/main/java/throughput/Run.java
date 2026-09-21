package throughput;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.OffsetDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

import com.ethlo.time.ITU;
import com.ethlo.time.MutableDateTimeBuffer;

/**
 * Reads a CSV written by {@link Generate} end to end, parsing the timestamp of every line with one pipeline, and
 * reports wall time per pass. One pipeline per JVM: the three share nothing, so no JIT profile or heap state
 * carries over from one to the next.
 * <ul>
 * <li>{@code jdk} - {@code BufferedReader.readLine()}, {@code indexOf} for the column, {@code substring},
 * {@code OffsetDateTime.parse}. What a program written without thought for speed does.</li>
 * <li>{@code itu-string} - the same reading and splitting, {@code ITU.parseDateTime}. Same allocation as
 * {@code jdk}, so the difference is the parser alone.</li>
 * <li>{@code itu-buffer} - bytes read in 1 MB chunks, the column found by scanning, copied to a reused
 * {@code char[]} and parsed with {@code ITU.parseLenient(char[], ...)} into a reused
 * {@link MutableDateTimeBuffer}. No {@code String} exists for any line.</li>
 * <li>{@code floor-string} and {@code floor-buffer} - the same reading, splitting and copying with no parse at
 * all (the column's length is hashed instead). A pipeline's time minus its floor is the parser's share; the
 * floor itself is what the surrounding code costs, which no parser can remove.</li>
 * </ul>
 * Every parsing pipeline folds the epoch second and nanosecond of every timestamp into one hash, printed at the
 * end: the three must agree, and the work cannot be skipped. The first pass over a file is reported but not
 * counted; it warms the JIT and, if the file was not in the page cache, reads it from disk.
 */
public final class Run
{
    private static final int CHUNK = 1 << 20;

    private Run()
    {
    }

    public static void main(final String[] args) throws IOException
    {
        if (args.length < 2)
        {
            System.err.println("usage: Run <file> <jdk|itu-string|itu-buffer|floor-string|floor-buffer> [passes]");
            System.exit(2);
        }
        final Path file = Paths.get(args[0]);
        final String pipeline = args[1];
        final int passes = args.length > 2 ? Integer.parseInt(args[2]) : 3;
        final long bytes = Files.size(file);

        long lines = 0;
        long hash = 0;
        final long[] millis = new long[passes];
        for (int pass = 0; pass <= passes; pass++)
        {
            final long gcTimeBefore = gcTimeMillis();
            final long allocBefore = allocatedBytes();
            final long start = System.nanoTime();
            final Result result = runOnce(file, pipeline);
            final long elapsed = System.nanoTime() - start;
            final long gcTime = gcTimeMillis() - gcTimeBefore;
            final long alloc = allocatedBytes() - allocBefore;
            if (pass > 0 && (result.lines != lines || result.hash != hash))
            {
                throw new IllegalStateException("Pass " + pass + " disagrees with pass " + (pass - 1));
            }
            lines = result.lines;
            hash = result.hash;
            System.out.printf(Locale.ROOT, "%-11s pass %d%s %7.0f ms  %6.1f ns/timestamp  %6.0f MB/s  gc %5d ms  %5.0f B/timestamp%n",
                    pipeline, pass, pass == 0 ? " (warm-up)" : "          ", elapsed / 1e6, (double) elapsed / lines, bytes / (elapsed / 1e3), gcTime, (double) alloc / lines);
            if (pass > 0)
            {
                millis[pass - 1] = elapsed / 1_000_000;
            }
        }
        Arrays.sort(millis);
        final long median = millis[passes / 2];
        System.out.printf(Locale.ROOT, "RESULT pipeline=%s file=%s lines=%d bytes=%d median_ms=%d min_ms=%d ns_per_timestamp=%.1f mb_per_s=%.0f hash=%d%n",
                pipeline, file.getFileName(), lines, bytes, median, millis[0], median * 1e6 / lines, bytes / 1048576.0 / (median / 1e3), hash);
    }

    private static Result runOnce(final Path file, final String pipeline) throws IOException
    {
        switch (pipeline)
        {
            case "jdk":
                return runStrings(file, Parser.JDK);
            case "itu-string":
                return runStrings(file, Parser.ITU);
            case "floor-string":
                return runStrings(file, Parser.NONE);
            case "itu-buffer":
                return runBuffer(file, true);
            case "floor-buffer":
                return runBuffer(file, false);
            default:
                throw new IllegalArgumentException("Unknown pipeline: " + pipeline);
        }
    }

    private enum Parser
    {
        JDK, ITU, NONE
    }

    private static Result runStrings(final Path file, final Parser parser) throws IOException
    {
        long lines = 0;
        long hash = 0;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(file.toFile()), StandardCharsets.UTF_8), CHUNK))
        {
            String line;
            while ((line = reader.readLine()) != null)
            {
                final int from = line.indexOf(',') + 1;
                final int to = line.indexOf(',', from);
                final String timestamp = line.substring(from, to);
                if (parser == Parser.NONE)
                {
                    hash = 31 * hash + timestamp.length();
                }
                else
                {
                    final OffsetDateTime dateTime = parser == Parser.JDK ? OffsetDateTime.parse(timestamp) : ITU.parseDateTime(timestamp);
                    hash = 31 * hash + dateTime.toEpochSecond();
                    hash = 31 * hash + dateTime.getNano();
                }
                lines++;
            }
        }
        return new Result(lines, hash);
    }

    private static Result runBuffer(final Path file, final boolean parse) throws IOException
    {
        long lines = 0;
        long hash = 0;
        final byte[] bytes = new byte[CHUNK];
        final char[] chars = new char[64];
        final MutableDateTimeBuffer buffer = new MutableDateTimeBuffer();
        try (InputStream in = new FileInputStream(file.toFile()))
        {
            int limit = 0;
            while (true)
            {
                final int read = in.read(bytes, limit, bytes.length - limit);
                if (read < 0)
                {
                    break;
                }
                limit += read;
                int lineStart = 0;
                while (true)
                {
                    final int newline = indexOf(bytes, (byte) '\n', lineStart, limit);
                    if (newline < 0)
                    {
                        break;
                    }
                    final int from = indexOf(bytes, (byte) ',', lineStart, newline) + 1;
                    final int to = indexOf(bytes, (byte) ',', from, newline);
                    final int length = to - from;
                    for (int i = 0; i < length; i++)
                    {
                        chars[i] = (char) bytes[from + i];
                    }
                    if (parse)
                    {
                        ITU.parseLenient(chars, 0, length, buffer);
                        hash = 31 * hash + buffer.toEpochSecond();
                        hash = 31 * hash + buffer.getNano();
                    }
                    else
                    {
                        hash = 31 * hash + length + chars[length - 1];
                    }
                    lines++;
                    lineStart = newline + 1;
                }
                // The partial last line moves to the front and the next read continues after it
                limit -= lineStart;
                System.arraycopy(bytes, lineStart, bytes, 0, limit);
            }
        }
        return new Result(lines, hash);
    }

    private static int indexOf(final byte[] bytes, final byte needle, final int from, final int to)
    {
        for (int i = from; i < to; i++)
        {
            if (bytes[i] == needle)
            {
                return i;
            }
        }
        return -1;
    }

    private static long gcTimeMillis()
    {
        long total = 0;
        final List<GarbageCollectorMXBean> beans = ManagementFactory.getGarbageCollectorMXBeans();
        for (final GarbageCollectorMXBean bean : beans)
        {
            total += Math.max(0, bean.getCollectionTime());
        }
        return total;
    }

    private static long allocatedBytes()
    {
        final java.lang.management.ThreadMXBean bean = ManagementFactory.getThreadMXBean();
        if (bean instanceof com.sun.management.ThreadMXBean)
        {
            return ((com.sun.management.ThreadMXBean) bean).getThreadAllocatedBytes(Thread.currentThread().getId());
        }
        return 0;
    }

    private static final class Result
    {
        final long lines;
        final long hash;

        Result(final long lines, final long hash)
        {
            this.lines = lines;
            this.hash = hash;
        }
    }
}
