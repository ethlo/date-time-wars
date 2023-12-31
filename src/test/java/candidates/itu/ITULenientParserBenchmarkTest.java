package candidates.itu;

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

import com.ethlo.time.ITU;
import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.infra.Blackhole;

import java.util.concurrent.TimeUnit;

@OutputTimeUnit(TimeUnit.MILLISECONDS)
public class ITULenientParserBenchmarkTest {
    @Benchmark
    public void rawDate(final Blackhole blackhole) {
        blackhole.consume(ITU.parseLenient("2017-12-21"));
    }

    @Benchmark
    public void rawSecond(final Blackhole blackhole) {
        blackhole.consume(ITU.parseLenient("2017-12-21T12:20:45Z"));
    }

    @Benchmark
    public void rawMillis(final Blackhole blackhole) {
        blackhole.consume(ITU.parseLenient("2017-12-21T12:20:45.123Z"));
    }

    @Benchmark
    public void rawNanos(final Blackhole blackhole) {
        blackhole.consume(ITU.parseLenient("2017-12-21T12:20:45.123123123Z"));
    }
}
