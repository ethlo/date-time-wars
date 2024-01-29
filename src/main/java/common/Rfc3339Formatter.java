package common;

/*-
 * #%L
 * Internet Time Utility
 * %%
 * Copyright (C) 2017 Morten Haraldsen (ethlo)
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */

import java.time.OffsetDateTime;
import java.util.Date;

public interface Rfc3339Formatter
{
    /**
     * Format the {@link Date} as a UTC formatted date-time string
     *
     * @param date The date to format
     * @return the formatted string
     */
    String formatUtc(OffsetDateTime date);

    /**
     * Format the date as a date-time String  with millisecond resolution, for example 1999-12-31T16:48:36.123Z
     *
     * @param date The date to format
     * @return the formatted string
     */
    String formatUtcMilli(OffsetDateTime date);

    /**
     * Format the date as a date-time String  with microsecond resolution, aka 1999-12-31T16:48:36.123456Z
     *
     * @param date The date to format
     * @return the formatted string
     */
    String formatUtcMicro(OffsetDateTime date);

    /**
     * Format the date as a date-time String  with nanosecond resolution, aka 1999-12-31T16:48:36.123456789Z
     *
     * @param date The date to format
     * @return the formatted string
     */
    String formatUtcNano(OffsetDateTime date);

    /**
     * Format the date as a date-time String with specified resolution, aka 1999-12-31T16:48:36[.123456789]Z
     *
     * @param date           The date to format
     * @param fractionDigits The number of fractional digits in the second
     * @return the formatted string
     */
    String formatUtc(OffsetDateTime date, int fractionDigits);
}
