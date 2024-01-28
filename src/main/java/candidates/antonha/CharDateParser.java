/**
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the “Software”), to deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to the following conditions:
 * <p>
 * The above copyright notice and this permission notice shall be included in all copies or
 * substantial portions of the Software.
 * <p>
 * THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
 * WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
 * OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
 * OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
package candidates.antonha;

import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.temporal.TemporalAccessor;

import common.LenientDateTimeParser;

/**
 * Date parser which is based on charAt() to demonstrate that it is possible to parse dates faster than the Java
 * parsers.
 * <p>
 * I'm not terribly proud of this code, but it is not that bad either. And it seems to work, based on tests. I would
 * want some more eyes on it before using it in production, though.
 */
public class CharDateParser implements LenientDateTimeParser
{
    public TemporalAccessor parseLenient(String dateString)
    {

        //Year
        if (dateString.length() < 4)
        {
            return null;
        }
        char y0 = dateString.charAt(0);
        int y1 = charToInt(dateString.charAt(1));
        int y2 = charToInt(dateString.charAt(2));
        int y3 = charToInt(dateString.charAt(3));
        if (y0 < '0' || y0 > '9' || y1 < 0 || y1 > 9 || y2 < 0 || y2 > 9 || y3 < 0 || y3 > 9)
        {
            return null;
        }
        int year = charToInt(y0) * 1000 + y1 * 100 + y2 * 10 + y3;


        //Month - first check if there are months
        if (dateString.length() == 4 || dateString.charAt(4) != '-')
        {
            return LocalDate.of(year, 1, 1);
        }
        int m0 = charToInt(dateString.charAt(5));
        int m1 = charToInt(dateString.charAt(6));
        if (m0 < 0 || m0 > 1 || m1 < 0 || m1 > 9)
        {
            return LocalDate.of(year, 1, 1);
        }
        int month = m0 * 10 + m1;

        //Day: first check if there are days
        if (dateString.length() == 7 || dateString.charAt(7) != '-')
        {
            return LocalDate.of(year, month, 1);
        }
        int d0 = charToInt(dateString.charAt(8));
        int d1 = charToInt(dateString.charAt(9));
        if (d0 < 0 || d0 > 3 || d1 < 0 || d1 > 9)
        {
            return LocalDate.of(year, month, 1);
        }
        int day = d0 * 10 + d1;

        //Hour: first check if there are hours
        if (dateString.length() == 10 || dateString.charAt(10) != 'T')
        {
            return LocalDate.of(year, month, day);
        }
        int h0 = charToInt(dateString.charAt(11));
        int h1 = charToInt(dateString.charAt(12));
        if (h0 < 0 || h0 > 9 || h1 < 0 || h1 > 9)
        {
            return LocalDate.of(year, month, day);
        }
        int hour = h0 * 10 + h1;

        //Minute: first check if there are minutes
        if (dateString.length() == 13 || dateString.charAt(13) != ':')
        {
            return withZone(
                    year, month, day, hour, 0, 0, 0,
                    dateString, 13
            );
        }
        int mi0 = charToInt(dateString.charAt(14));
        int mi1 = charToInt(dateString.charAt(15));
        if (mi0 < 0 || mi0 > 5 || mi1 < 0 || mi1 > 9)
        {
            return withZone(
                    year, month, day, hour, 0, 0, 0,
                    dateString, 13
            );
        }
        int minute = mi0 * 10 + mi1;

        //Second: first check if there are seconds
        if (dateString.length() == 16 || dateString.charAt(16) != ':')
        {
            return withZone(
                    year, month, day, hour, minute, 0, 0,
                    dateString, 16
            );
        }
        int s0 = charToInt(dateString.charAt(17));
        int s1 = charToInt(dateString.charAt(18));
        if (s0 < 0 || s0 > 5 || s1 < 0 || s1 > 9)
        {
            return withZone(
                    year, month, day, hour, minute, 0, 0,
                    dateString, 16
            );
        }
        int second = s0 * 10 + s1;

        //Nanos: first check if there are second fractions
        if (dateString.length() == 19 || dateString.charAt(19) != '.')
        {
            return withZone(
                    year, month, day, hour, minute, second, 0,
                    dateString, 19
            );
        }

        //Second fractions can be of length 1-9, so we first scan through them and then increase based on number
        //of parsed digits
        int nanos = 0;
        int pos = 20;
        while (pos < dateString.length())
        {
            int num = charToInt(dateString.charAt(pos));
            if (num < 0 || num > 9)
            {
                break;
            }
            nanos = nanos * 10 + num;
            pos++;
        }
        int j = pos - 20;
        while (j < 9)
        {
            nanos *= 10;
            j++;
        }
        return withZone(
                year, month, day, hour, minute, second, nanos,
                dateString, pos
        );
    }

    //Taking in the date string here with position, rather than a substring, lets us avoid allocating a new String.
    private static TemporalAccessor withZone(
            int year, int month, int day,
            int hour, int minute, int second, int nanos,
            String dateString, int pos
    )
    {
        if (pos == dateString.length())
        {
            return LocalDateTime.of(year, month, day, hour, minute, second, nanos);
        }
        ZoneId zone = parseZone(dateString, pos);
        if (zone != null)
        {
            return ZonedDateTime.of(
                    year, month, day, hour, minute, second, nanos,
                    zone
            );
        }
        else
        {
            return LocalDateTime.of(year, month, day, hour, minute, second, nanos);
        }
    }

    private static ZoneId parseZone(String dateString, int pos)
    {
        //Fast-track for UTC, since we don't need to create a substring.
        //Would love to have slices in Java.
        if (dateString.charAt(pos) == 'Z')
        {
            return ZoneOffset.UTC;
        }
        try
        {
            return ZoneId.of(dateString.substring(pos));
        }
        catch (DateTimeException e)
        {
            return null;
        }
    }

    private static int charToInt(char c)
    {
        return c - '0';
    }
}
