package candidates.itu;

import java.time.OffsetDateTime;

import com.ethlo.time.ITU;
import common.FormatterBenchmarkTest;
import common.Rfc3339Formatter;

public class ITURfc3339FormatterBenchmarkTest extends FormatterBenchmarkTest
{
    public ITURfc3339FormatterBenchmarkTest()
    {
        super(new Rfc3339Formatter()
        {
            @Override
            public String formatUtc(final OffsetDateTime date)
            {
                return ITU.formatUtc(date);
            }

            @Override
            public String formatUtcMilli(final OffsetDateTime date)
            {
                return ITU.formatUtcMilli(date);
            }

            @Override
            public String formatUtcMicro(final OffsetDateTime date)
            {
                return ITU.formatUtcMicro(date);
            }

            @Override
            public String formatUtcNano(final OffsetDateTime date)
            {
                return ITU.formatUtcNano(date);
            }

            @Override
            public String formatUtc(final OffsetDateTime date, final int fractionDigits)
            {
                return ITU.formatUtc(date, fractionDigits);
            }
        });
    }
}
