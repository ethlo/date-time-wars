package throughput;

import java.io.BufferedOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Random;

/**
 * Writes a CSV of {@code seq,timestamp,value} lines until the target size is reached, deterministically from the
 * seed. Two shapes:
 * <ul>
 * <li>{@code uniform} - every timestamp is {@code YYYY-MM-DDTHH:MM:SS.mmmZ}, the common interchange form. One
 * shape, so the branch predictors settle exactly as they do in the JMH rows.</li>
 * <li>{@code mixed} - per line, the fraction has 0, 3, 6 or 9 digits and the offset is {@code Z} or a random
 * {@code ±HH:MM}, chosen independently. Every line is still strict RFC-3339, so all pipelines accept it; what
 * changes is that no two consecutive lines need have the same shape.</li>
 * </ul>
 * Instants are uniform over 1970-2100 at nanosecond resolution; the third column is a random int so the line
 * has something after the timestamp, as a real file would.
 */
public final class Generate
{
    private static final long MAX_EPOCH_SECOND = LocalDateTime.of(2100, 1, 1, 0, 0).toEpochSecond(ZoneOffset.UTC);

    private Generate()
    {
    }

    public static void main(final String[] args) throws IOException
    {
        if (args.length < 3)
        {
            System.err.println("usage: Generate <file> <mixed|uniform> <sizeMB> [seed]");
            System.exit(2);
        }
        final Path file = Paths.get(args[0]);
        final boolean mixed = "mixed".equals(args[1]);
        final long targetBytes = Long.parseLong(args[2]) * 1024 * 1024;
        final long seed = args.length > 3 ? Long.parseLong(args[3]) : 42;
        Files.createDirectories(file.toAbsolutePath().getParent());

        final Random random = new Random(seed);
        final byte[] line = new byte[96];
        long written = 0;
        long lines = 0;
        final long start = System.nanoTime();
        try (OutputStream out = new BufferedOutputStream(new FileOutputStream(file.toFile()), 1 << 20))
        {
            while (written < targetBytes)
            {
                final int length = writeLine(line, lines, random, mixed);
                out.write(line, 0, length);
                written += length;
                lines++;
            }
        }
        System.out.printf("%s: %d lines, %d bytes, %s shape, %.1f s%n", file, lines, written, mixed ? "mixed" : "uniform", (System.nanoTime() - start) / 1e9);
    }

    private static int writeLine(final byte[] line, final long seq, final Random random, final boolean mixed)
    {
        int p = writeLong(line, 0, seq);
        line[p++] = ',';

        final long epochSecond = (long) (random.nextDouble() * MAX_EPOCH_SECOND);
        final int nano = random.nextInt(1_000_000_000);
        final int fractionDigits = mixed ? 3 * random.nextInt(4) : 3;
        final int offsetSeconds;
        if (mixed && random.nextInt(2) == 0)
        {
            // Whole-minute offsets within ±14:00, the RFC-3339 range
            offsetSeconds = (random.nextInt(2 * 14 * 60 + 1) - 14 * 60) * 60;
        }
        else
        {
            offsetSeconds = 0;
        }
        final LocalDateTime local = LocalDateTime.ofEpochSecond(epochSecond + offsetSeconds, 0, ZoneOffset.UTC);
        p = write4(line, p, local.getYear());
        line[p++] = '-';
        p = write2(line, p, local.getMonthValue());
        line[p++] = '-';
        p = write2(line, p, local.getDayOfMonth());
        line[p++] = 'T';
        p = write2(line, p, local.getHour());
        line[p++] = ':';
        p = write2(line, p, local.getMinute());
        line[p++] = ':';
        p = write2(line, p, local.getSecond());
        if (fractionDigits > 0)
        {
            line[p++] = '.';
            int fraction = nano;
            for (int i = fractionDigits; i < 9; i++)
            {
                fraction /= 10;
            }
            p = writeDigits(line, p, fraction, fractionDigits);
        }
        if (offsetSeconds == 0)
        {
            line[p++] = 'Z';
        }
        else
        {
            final int abs = Math.abs(offsetSeconds);
            line[p++] = (byte) (offsetSeconds < 0 ? '-' : '+');
            p = write2(line, p, abs / 3600);
            line[p++] = ':';
            p = write2(line, p, abs / 60 % 60);
        }
        line[p++] = ',';
        p = writeLong(line, p, random.nextInt(1_000_000));
        line[p++] = '\n';
        return p;
    }

    private static int write2(final byte[] b, final int p, final int v)
    {
        return writeDigits(b, p, v, 2);
    }

    private static int write4(final byte[] b, final int p, final int v)
    {
        return writeDigits(b, p, v, 4);
    }

    private static int writeDigits(final byte[] b, final int p, int v, final int digits)
    {
        for (int i = digits - 1; i >= 0; i--)
        {
            b[p + i] = (byte) ('0' + v % 10);
            v /= 10;
        }
        return p + digits;
    }

    private static int writeLong(final byte[] b, final int p, final long v)
    {
        final String s = Long.toString(v);
        for (int i = 0; i < s.length(); i++)
        {
            b[p + i] = (byte) s.charAt(i);
        }
        return p + s.length();
    }
}
