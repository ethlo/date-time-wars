# Date-time wars

### A micro-benchmark of different date-time parsers and formatters.

## Candidates

* ITU - Internet Time Utility - https://github.com/ethlo/itu
* Google HTTP
  client - [com.google.api.client.util.DateTime](https://github.com/googleapis/google-http-java-client/blob/main/google-http-client/src/main/java/com/google/api/client/util/DateTime.java)
* Standard JDK - [java.time.OffsetDateTime](https://docs.oracle.com/javase/8/docs/api/java/time/OffsetDateTime.html)

## Performance

Your mileage may vary. I've done my best to make sure these tests are as accurate as possible, but please do your own
evaluation.

### Parsing

[JMH result file](results/jmh-result-grouped.json) - [Visualize JMH](https://jmh.morethan.io/?source=https://raw.githubusercontent.com/ethlo/date-time-wars/main/results/jmh-result-grouped.json)

### Environment

Tests performed on a Lenovo P1 G6 laptop:

* Intel(R) Core(TM) i9-13900H
* Ubuntu 23.10
* OpenJDK version 17.0.9

### Run tests yourself

```shell
mvn jmh:benchmark
```

To group the results and create the result file, you can run `plot.py`, for example:

```
python3 plot.py
```
